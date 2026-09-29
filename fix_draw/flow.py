"""
ch2 手繪圖辨識完整流程（獨立單檔，可直接接相機測試）：

  step1  paper 模型定位白紙 -> 畫出 mask（之後只在這個範圍內分析）
         paper 模型若失敗/範圍太小，退回 CV「最大亮色區塊」保底
  step2  在紙張 mask 範圍內，用 CV 找出手繪圖形 bbox
  step3  切正方形 -> 黑底白線 binary(224) -> cls 模型判斷形狀
         (circle / cross / other / square)

用法：
  python flow.py                      # 開相機，SPACE/s=辨識  q/ESC=離開
  python flow.py --image one.jpg      # 只跑單張
  python flow.py --dir some_folder    # 逐張跑資料夾
  python flow.py --cam 1              # 指定相機編號
可調權重：--paper 、--cls
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
MODELS = ROOT.parent / "PDMS2_web" / "models"
DEFAULT_PAPER = MODELS / "paper_seg.pt"
DEFAULT_SAM = MODELS / "sam2_b.pt"
DEFAULT_CLS = MODELS / "shape_cls.pt"


def pick_device(arg=None):
    if arg:
        return arg
    try:
        import torch
        return "0" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


# ---------------- step1: 找白紙 ----------------
def paper_mask_model(frame, paper_yolo, device, conf):
    """用 paper 分割模型取信心最高的紙張 mask (uint8 0/255)，找不到回 None。"""
    res = paper_yolo.predict(source=frame, conf=conf, device=device, verbose=False)[0]
    if res.masks is None or len(res.masks) == 0:
        return None
    best = int(np.argmax(res.boxes.conf.cpu().numpy()))
    m = res.masks.data.cpu().numpy()[best]
    mask = (m > 0.5).astype(np.uint8)
    if mask.shape[:2] != frame.shape[:2]:
        mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    return mask * 255


def paper_mask_sam(frame, paper_yolo, sam, device, conf):
    """paper 模型取信心最高 bbox -> SAM2 精修出紙張 mask (uint8 0/255)，失敗回 None。"""
    res = paper_yolo.predict(source=frame, conf=conf, device=device, verbose=False)[0]
    if res.boxes is None or len(res.boxes) == 0:
        return None
    best = int(np.argmax(res.boxes.conf.cpu().numpy()))
    bbox = res.boxes.xyxy.cpu().numpy()[best]
    sam_res = sam.predict(source=frame, bboxes=np.array([bbox]),
                          device=device, verbose=False)[0]
    if sam_res.masks is None or len(sam_res.masks) == 0:
        return None
    m = sam_res.masks.data.cpu().numpy()[0]
    mask = (m > 0.5).astype(np.uint8)
    if mask.shape[:2] != frame.shape[:2]:
        mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    return mask * 255


# ---------------- step2: 紙內用 CV 找圖形 ----------------
def find_shape_bbox(frame, paper_mask, min_area_ratio=0.0005):
    """在紙張 mask 範圍內找手繪圖形外接框(adaptiveThreshold)。回傳 (x1,y1,x2,y2) 或 None。"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    paper_area = int((paper_mask > 0).sum())
    if paper_area == 0:
        return None
    k = max(5, int(0.035 * np.sqrt(paper_area)))
    inner = cv2.erode(paper_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    if int((inner > 0).sum()) == 0:
        return None
    blk = max(15, int(0.06 * np.sqrt(paper_area)) | 1)
    adap = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, blk, 12)
    ink = ((adap > 0) & (inner > 0)).astype(np.uint8) * 255
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = min_area_ratio * paper_area
    cand = []
    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        cand.append(((x, y, w, h), (x + w / 2, y + h / 2)))
    if not cand:
        return None
    xs = np.where(inner.any(axis=0))[0]
    ys = np.where(inner.any(axis=1))[0]
    px1, px2, py1, py2 = xs.min(), xs.max(), ys.min(), ys.max()
    mx, my = 0.22 * (px2 - px1), 0.22 * (py2 - py1)
    cl, cr, ct, cb = px1 + mx, px2 - mx, py1 + my, py2 - my
    central = [b for b, (cx, cy) in cand if cl <= cx <= cr and ct <= cy <= cb]
    if not central:
        pcx, pcy = (px1 + px2) / 2, (py1 + py2) / 2
        central = [min(cand, key=lambda t: (t[1][0] - pcx) ** 2 + (t[1][1] - pcy) ** 2)[0]]
    x1 = min(b[0] for b in central)
    y1 = min(b[1] for b in central)
    x2 = max(b[0] + b[2] for b in central)
    y2 = max(b[1] + b[3] for b in central)
    return (x1, y1, x2, y2)


def crop_square(frame, bbox, pad=30):
    x1, y1, x2, y2 = bbox
    x1, y1, x2, y2 = x1 - pad, y1 - pad, x2 + pad, y2 + pad
    H, W = frame.shape[:2]
    side = min(max(x2 - x1, y2 - y1), H, W)
    ccx, ccy = (x1 + x2) / 2, (y1 + y2) / 2
    cx1 = max(0, min(int(round(ccx - side / 2)), W - side))
    cy1 = max(0, min(int(round(ccy - side / 2)), H - side))
    return frame[cy1:cy1 + side, cx1:cx1 + side].copy(), (cx1, cy1, cx1 + side, cy1 + side)


# ---------------- step3: binary + 分類 ----------------
def to_binary(bgr):
    """轉黑底白線(同 cls 訓練資料格式)。"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    blk = max(15, (gray.shape[0] // 5) | 1)
    b = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, blk, 12)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    if n > 1:
        biggest = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        b = (lbl == biggest).astype(np.uint8) * 255
    return b


class Flow:
    def __init__(self, paper_w=DEFAULT_PAPER, cls_w=DEFAULT_CLS,
                 sam_w=DEFAULT_SAM, device=None, paper_conf=0.4, pad=30, size=224):
        from ultralytics import YOLO, SAM
        self.device = pick_device(device)
        self.paper = YOLO(str(paper_w))
        self.sam = SAM(str(sam_w))
        self.cls = YOLO(str(cls_w))
        self.paper_conf = paper_conf
        self.pad = pad
        self.size = size
        print(f"[flow] device={self.device}")
        print(f"[flow] paper(yolo bbox)={paper_w}")
        print(f"[flow] sam2={sam_w}")
        print(f"[flow] cls={cls_w}  classes={self.cls.names}")

    def _paper(self, frame):
        """step1 紙張定位：paper 模型 bbox -> SAM2 精修 mask（純 YOLO 路線，無 CV）。"""
        return paper_mask_sam(frame, self.paper, self.sam, self.device, self.paper_conf)

    def paper_only(self, frame):
        """只做 step1：paper 模型 bbox + SAM2 找白紙(無 CV)，把 mask 疊藍色顯示。"""
        mask = self._paper(frame)
        vis = frame.copy()
        if mask is None or int((mask > 0).sum()) == 0:
            print("  找白紙(YOLO+SAM2) -> 失敗")
            cv2.putText(vis, "NO PAPER", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            return vis, None, "yolo+sam2"
        area_pct = 100 * int((mask > 0).sum()) / mask.size
        print(f"  找白紙(YOLO+SAM2) -> 佔畫面 {area_pct:.1f}%")
        blue = np.zeros_like(vis); blue[mask > 0] = (255, 128, 0)
        vis = cv2.addWeighted(vis, 1.0, blue, 0.35, 0)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, (0, 0, 255), 2)
        cv2.putText(vis, f"yolo+sam2 paper  {area_pct:.0f}%", (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return vis, mask, "yolo+sam2"

    def run(self, frame):
        """跑一張，逐步印出，回傳 dict(ok,label,conf,vis,binary)。"""
        vis = frame.copy()

        # step1: paper 模型 bbox + SAM2 找白紙(無 CV)
        mask = self._paper(frame)
        if mask is None or int((mask > 0).sum()) == 0:
            print("  step1 找白紙(YOLO+SAM2) -> 失敗")
            cv2.putText(vis, "NO PAPER", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            return {"ok": False, "reason": "no_paper", "vis": vis}
        area_pct = 100 * int((mask > 0).sum()) / mask.size
        print(f"  step1 找白紙(YOLO+SAM2) -> OK 佔畫面 {area_pct:.1f}%")
        # 畫 mask：半透明藍 + 輪廓
        blue = np.zeros_like(vis); blue[mask > 0] = (255, 128, 0)
        vis = cv2.addWeighted(vis, 1.0, blue, 0.25, 0)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, (255, 128, 0), 2)

        # step2: 紙內 CV 找圖形
        bbox = find_shape_bbox(frame, mask)
        if bbox is None:
            print("  step2 找圖形 -> 失敗")
            cv2.putText(vis, "NO SHAPE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            return {"ok": False, "reason": "no_shape", "vis": vis}
        print(f"  step2 找圖形 -> OK bbox={bbox}")

        # step3: 切圖 + binary + 分類
        crop, sq = crop_square(frame, bbox, self.pad)
        cv2.rectangle(vis, (sq[0], sq[1]), (sq[2], sq[3]), (0, 255, 0), 3)
        binary = cv2.resize(to_binary(crop), (self.size, self.size), interpolation=cv2.INTER_AREA)
        bin_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        res = self.cls.predict(source=bin_bgr, imgsz=self.size, device=self.device, verbose=False)[0]
        i = int(res.probs.top1)
        label, conf = res.names[i], float(res.probs.top1conf)
        print(f"  step3 分類 -> {label} ({conf*100:.1f}%)")
        cv2.putText(vis, f"{label} {conf*100:.1f}%", (sq[0], max(sq[1] - 10, 24)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        return {"ok": True, "label": label, "conf": conf, "vis": vis, "binary": bin_bgr}


def show(r, title):
    vis = r.get("vis")
    if vis is None:
        return
    h = 480
    left = cv2.resize(vis, (int(vis.shape[1] * h / vis.shape[0]), h))
    if r["ok"]:
        right = cv2.resize(r["binary"], (h, h))
        cv2.putText(right, f'{r["label"]} {r["conf"]*100:.1f}%', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        canvas = cv2.hconcat([left, right])
    else:
        canvas = left
    cv2.imshow(title, canvas)


def main():
    ap = argparse.ArgumentParser(description="paper定位 + CV找圖形 + cls分類（可接相機）")
    ap.add_argument("--paper", default=str(DEFAULT_PAPER))
    ap.add_argument("--sam", default=str(DEFAULT_SAM))
    ap.add_argument("--cls", default=str(DEFAULT_CLS))
    ap.add_argument("--image", default=None)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--device", default=None)
    ap.add_argument("--paper-only", action="store_true",
                    help="只顯示白紙 mask（除錯用，不找圖形/不分類）")
    args = ap.parse_args()

    flow = Flow(paper_w=args.paper, cls_w=args.cls, sam_w=args.sam, device=args.device)
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

    # 檔案 / 資料夾模式
    if args.image or args.dir:
        if args.image:
            imgs = [Path(args.image)]
        else:
            src = Path(args.dir)
            if not src.is_dir():
                print(f"[錯誤] 找不到資料夾 {src}")
                return
            imgs = sorted(p for p in src.iterdir() if p.suffix.lower() in exts)
        if not imgs:
            print("[錯誤] 沒有圖片")
            return
        win = "flow (any key=next, q=quit)"
        for i, p in enumerate(imgs, 1):
            frame = cv2.imread(str(p))
            if frame is None:
                print(f"[{i}/{len(imgs)}] 讀取失敗：{p.name}")
                continue
            print(f"[{i}/{len(imgs)}] {p.name}")
            if args.paper_only:
                vis, _, _ = flow.paper_only(frame)
                h = 560
                cv2.imshow(win, cv2.resize(vis, (int(vis.shape[1] * h / vis.shape[0]), h)))
            else:
                show(flow.run(frame), win)
            if (cv2.waitKey(0) & 0xFF) in (ord("q"), 27):
                break
        cv2.destroyAllWindows()
        return

    # 相機模式
    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        print(f"[錯誤] 無法開啟相機 {args.cam}")
        return
    if args.paper_only:
        print("即時顯示白紙 mask   q/ESC = 離開")
        win = "flow paper-only (q=quit)"
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            vis, _, _ = flow.paper_only(frame)
            cv2.imshow(win, vis)
            if (cv2.waitKey(1) & 0xFF) in (ord("q"), 27):
                break
        cap.release()
        cv2.destroyAllWindows()
        return

    print("SPACE/s = 拍照並辨識   q/ESC = 離開")
    win = "flow camera (SPACE=classify, q=quit)"
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[錯誤] 讀取畫面失敗")
            break
        view = frame.copy()
        cv2.putText(view, "SPACE/s = classify   q/ESC = quit", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow(win, view)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key in (ord(" "), ord("s")):
            print("--- 拍照，開始跑流程 ---")
            r = flow.run(frame)
            show(r, "result (any key=back)")
            cv2.waitKey(0)
            cv2.destroyWindow("result (any key=back)")
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
