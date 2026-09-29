"""
即時測試：開鏡頭同時顯示 paper_seg（紙張）+ shape.pt（紙上圖形）。

自帶前處理函式，不依賴 prepare.py。模型讀 fix_draw 根目錄：
  paper_seg.pt(YOLO) 取紙張最大 bbox -> (按 s) SAM2(sam2_b.pt) 精修紙張輪廓
  shape.pt(YOLO) 在紙張範圍內圈手繪圖形（框中心落在紙內才留）

為了即時 FPS：paper bbox 與 shape 偵測每幀都跑（YOLO 很快），
SAM2 較重，預設關閉，按 s 才開啟每幀精修 mask。

操作：
  r  框選 ROI（滑鼠左鍵拖曳；框好後放開）— 之後只在框內辨識
  c  清除 ROI（恢復整張畫面辨識）
  s  切換 SAM2 精修（開啟時每幀跑，會變慢）
  空白鍵  存當前 frame / vis 到 scripts/live_out/
  q 或 ESC  離開

用法（在 fix_draw 下）：
  python scripts/live_detect.py --cam 1 --device 0
  python scripts/live_detect.py --paper-conf 0.4 --shape-conf 0.25
"""

import argparse
import time
from pathlib import Path

import cv2
import numpy as np

# 模型在 fix_draw 根目錄（scripts/ 的上一層）
ROOT = Path(__file__).resolve().parent.parent
PAPER_WEIGHTS = ROOT / "paper_seg.pt"
SAM_WEIGHTS = ROOT / "sam2_b.pt"
SHAPE_WEIGHTS = ROOT / "shape.pt"

SHAPE_COLORS = {
    "circle": (0, 255, 0),
    "cross": (0, 165, 255),
    "diamond": (255, 0, 255),
    "rectangle": (255, 255, 0),
    "triangle": (0, 0, 255),
}


def pick_device(arg=None):
    if arg:
        return arg
    try:
        import torch
        return "0" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def get_paper_bbox(frame, yolo, device, conf):
    """paper 模型取「面積最大」的框 (x1,y1,x2,y2)，找不到回 None。"""
    res = yolo.predict(source=frame, conf=conf, device=device, verbose=False)[0]
    if res.boxes is None or len(res.boxes) == 0:
        return None
    boxes = res.boxes.xyxy.cpu().numpy()
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return boxes[int(np.argmax(areas))]


def sam_mask_from_bbox(frame, sam, bbox, device):
    """以 bbox 提示 SAM2，回傳精修後紙張 mask (uint8 0/255) 或 None。"""
    sam_res = sam.predict(source=frame, bboxes=np.array([bbox]),
                          device=device, verbose=False)[0]
    if sam_res.masks is None or len(sam_res.masks) == 0:
        return None
    m = sam_res.masks.data.cpu().numpy()[0]
    mask = (m > 0.5).astype(np.uint8)
    if mask.shape[:2] != frame.shape[:2]:
        mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    mask = mask * 255
    # SAM 有時把紙上深色筆跡當非紙、在紙內挖洞，導致 shape 框中心落在洞上被誤濾。
    # 取最大外輪廓填實，紙張區域維持實心（外邊界不變）。
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        filled = np.zeros_like(mask)
        cv2.drawContours(filled, [max(cnts, key=cv2.contourArea)], -1, 255, cv2.FILLED)
        mask = filled
    return mask


def find_shape_bbox_yolo(frame, shape_yolo, paper_mask, device, conf=0.25):
    """紙張範圍內用 shape 模型找圖形，取框中心落在紙內、信心最高者。
    回傳 (bbox, label, conf) 或 None。"""
    res = shape_yolo.predict(source=frame, conf=conf, device=device, verbose=False)[0]
    if res.boxes is None or len(res.boxes) == 0:
        return None
    H, W = paper_mask.shape[:2]
    # 對 SAM mask 不完美（邊緣偏緊、殘留小洞）留容忍度：膨脹一小圈再判斷。
    paper_area = int((paper_mask > 0).sum())
    k = max(5, int(0.02 * np.sqrt(paper_area)) | 1) if paper_area else 5
    mask_tol = cv2.dilate(paper_mask,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    boxes = res.boxes.xyxy.cpu().numpy()
    confs = res.boxes.conf.cpu().numpy()
    clss = res.boxes.cls.cpu().numpy().astype(int)
    names = shape_yolo.names
    cand = []
    for (x1, y1, x2, y2), cf, ci in zip(boxes, confs, clss):
        cx = int(round((x1 + x2) / 2))
        cy = int(round((y1 + y2) / 2))
        if not (0 <= cx < W and 0 <= cy < H):
            continue
        center_ok = mask_tol[cy, cx] > 0
        bx1, by1 = max(0, int(x1)), max(0, int(y1))
        bx2, by2 = min(W, int(x2)), min(H, int(y2))
        sub = paper_mask[by1:by2, bx1:bx2]
        overlap = (sub > 0).mean() if sub.size else 0.0
        if not (center_ok or overlap >= 0.3):
            continue
        cand.append((float(cf), (int(x1), int(y1), int(x2), int(y2)), names[ci]))
    if not cand:
        return None
    cf, bbox, label = max(cand, key=lambda t: t[0])
    return bbox, label, cf


# ---- ROI 框選（滑鼠拖曳）狀態 ----
class RoiState:
    def __init__(self):
        self.roi = None        # (x1,y1,x2,y2) 已確定的框
        self.selecting = False
        self.p0 = None
        self.p1 = None

    def rect(self):
        """回傳正規化 (x1,y1,x2,y2)，尚未框選回 None。"""
        if self.selecting and self.p0 and self.p1:
            x1, y1 = self.p0
            x2, y2 = self.p1
            return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        return self.roi


def make_mouse_cb(state, win_mode):
    """win_mode() 回傳目前是否處於框選模式（按 r 開啟）。"""
    def cb(event, x, y, flags, _param):
        if not win_mode():
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            state.selecting = True
            state.p0 = (x, y)
            state.p1 = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and state.selecting:
            state.p1 = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and state.selecting:
            state.p1 = (x, y)
            state.selecting = False
            x1, y1 = state.p0
            x2, y2 = state.p1
            r = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            if (r[2] - r[0]) > 5 and (r[3] - r[1]) > 5:
                state.roi = r
    return cb


def draw_shape(vis, bbox, label, conf):
    x1, y1, x2, y2 = bbox
    color = SHAPE_COLORS.get(label, (0, 255, 0))
    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
    txt = f"{label} {conf:.2f}"
    (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(vis, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
    cv2.putText(vis, txt, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0, help="攝影機索引")
    ap.add_argument("--paper-conf", type=float, default=0.4)
    ap.add_argument("--shape-conf", type=float, default=0.25)
    ap.add_argument("--device", default=None, help="0 / cpu；預設自動")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    from ultralytics import YOLO, SAM

    device = pick_device(args.device)
    print(f"[live] device={device}")
    print(f"[live] paper={PAPER_WEIGHTS}")
    print(f"[live] shape={SHAPE_WEIGHTS}")
    paper = YOLO(str(PAPER_WEIGHTS))
    shape = YOLO(str(SHAPE_WEIGHTS))
    print(f"[live] shape classes={shape.names}")
    sam = None  # 第一次按 s 才載

    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        print(f"[live] 無法開啟攝影機 {args.cam}")
        return

    out_dir = Path(__file__).resolve().parent / "live_out"
    out_dir.mkdir(exist_ok=True)

    WIN = "live: paper_seg + shape"
    cv2.namedWindow(WIN)
    roi_state = RoiState()
    roi_mode = {"on": False}   # 按 r 進入框選模式
    cv2.setMouseCallback(WIN, make_mouse_cb(roi_state, lambda: roi_mode["on"]))

    use_sam = False
    prev = time.time()
    fps = 0.0
    print("[live] r=框選ROI  c=清除ROI  s=SAM2精修  space=存檔  q/ESC=離開")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[live] 讀取失敗")
            break

        vis = frame.copy()
        H, W = frame.shape[:2]

        # ROI：偵測只在框內做，座標處理完再位移回原圖
        roi = roi_state.roi
        if roi is not None:
            rx1 = max(0, min(roi[0], W - 1))
            ry1 = max(0, min(roi[1], H - 1))
            rx2 = max(rx1 + 1, min(roi[2], W))
            ry2 = max(ry1 + 1, min(roi[3], H))
            det_frame = frame[ry1:ry2, rx1:rx2]
            ox, oy = rx1, ry1
        else:
            det_frame = frame
            ox, oy = 0, 0
        dH, dW = det_frame.shape[:2]

        # 框選中 / 已框：畫出 ROI
        rect = roi_state.rect()
        if rect is not None:
            cv2.rectangle(vis, (rect[0], rect[1]), (rect[2], rect[3]),
                          (0, 255, 255), 2)
            cv2.putText(vis, "ROI", (rect[0], max(20, rect[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        bbox = None
        if not roi_state.selecting:  # 拖曳當下先不跑推論
            bbox = get_paper_bbox(det_frame, paper, device, args.paper_conf)
        paper_mask = None            # 相對 det_frame 座標
        if bbox is not None:
            bx = bbox.astype(int)
            if use_sam:
                if sam is None:
                    print("[live] 載入 SAM2 ...")
                    sam = SAM(str(SAM_WEIGHTS))
                paper_mask = sam_mask_from_bbox(det_frame, sam, bbox, device)
            if paper_mask is not None:
                cnts, _ = cv2.findContours(paper_mask, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
                for c in cnts:
                    c[:, 0, 0] += ox
                    c[:, 0, 1] += oy
                cv2.drawContours(vis, cnts, -1, (255, 128, 0), 2)
            else:
                cv2.rectangle(vis, (bx[0] + ox, bx[1] + oy),
                              (bx[2] + ox, bx[3] + oy), (255, 128, 0), 2)
            cv2.putText(vis, "paper", (bx[0] + ox, max(20, bx[1] + oy - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 128, 0), 2)

        # 沒 SAM mask 時，用 bbox 當紙張範圍過濾圖形（測試用）
        if paper_mask is None and bbox is not None:
            paper_mask = np.zeros((dH, dW), np.uint8)
            bx = bbox.astype(int)
            paper_mask[max(0, bx[1]):bx[3], max(0, bx[0]):bx[2]] = 255

        if paper_mask is not None:
            hit = find_shape_bbox_yolo(det_frame, shape, paper_mask,
                                       device, args.shape_conf)
            if hit is not None:
                sbbox, label, conf = hit
                sbbox = (sbbox[0] + ox, sbbox[1] + oy,
                         sbbox[2] + ox, sbbox[3] + oy)
                draw_shape(vis, sbbox, label, conf)

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-6, now - prev))
        prev = now
        if roi_state.selecting:
            mode = "SELECT-ROI"
        elif roi:
            mode = "ROI"
        else:
            mode = "FULL"
        hud = f"FPS {fps:4.1f} | {mode} | SAM2 {'ON' if use_sam else 'off'} " \
              f"| paper {'yes' if bbox is not None else 'no'}"
        cv2.putText(vis, hud, (10, 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2)

        cv2.imshow(WIN, vis)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            roi_mode["on"] = True
            roi_state.roi = None
            print("[live] 框選模式：滑鼠左鍵拖曳畫框")
        if key == ord("c"):
            roi_mode["on"] = False
            roi_state.roi = None
            roi_state.selecting = False
            print("[live] 已清除 ROI，恢復整張辨識")
        if key == ord("s"):
            use_sam = not use_sam
            print(f"[live] SAM2 精修 -> {'ON' if use_sam else 'off'}")
        if key == ord(" "):
            ts = time.strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(str(out_dir / f"{ts}_frame.jpg"), frame)
            cv2.imwrite(str(out_dir / f"{ts}_vis.jpg"), vis)
            print(f"[live] 已存檔 {ts}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
