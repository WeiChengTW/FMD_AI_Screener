"""
ch2-t1 完整流程 + 即時鏡頭評分（不修改任何原檔）。

直接 import PDMS2_web 的原始模組跑「全部流程」：
  1. get_pixel_per_cm_from_a4  A4 量 px->cm（本檔複製自 ch2-t1/main.py，原檔不動）
  2. prepare.Preparer          定位紙張 -> 圈手繪圖形 -> 224 binary
  3. classify.Classifier       4 類分類（circle/cross/other/square），必須是 circle
  4. check_point               骨架端點距離(px) -> offset cm -> 分數
     分數：perfect 或 offset<=1.2 -> 2；<=2.5 -> 1；其餘 -> 0；非 circle -> 0

操作：
  g 或 空白鍵  對當前畫面跑完整 ch2-t1 流程並顯示分數
  r  框選 ROI（滑鼠左鍵拖曳）— 只把框內畫面送去評分
  c  清除 ROI
  q 或 ESC  離開

用法（在 fix_draw 下）：
  python scripts/ch2t1_live.py --cam 1 --device 0
"""

import argparse
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# ---- 讓 import 得到 PDMS2_web 的原始模組（原檔不動）----
FIX_DRAW = Path(__file__).resolve().parent.parent          # fix_draw/
PDMS = FIX_DRAW.parent / "PDMS2_web"                        # PDMS2_web/
sys.path.insert(0, str(PDMS))                              # prepare.py / classify.py
sys.path.insert(0, str(PDMS / "ch2-t1"))                   # check_point.py

from prepare import Preparer          # noqa: E402  用 PDMS2_web/models
from classify import Classifier       # noqa: E402
from check_point import check_point   # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "ch2t1_out"
TARGET = "circle"
SCALE = 2
REAL_WIDTH_CM = 29.7


# ---- 複製自 ch2-t1/main.py 的 A4 量測（原檔不動）----
def get_pixel_per_cm_from_a4(image_path, real_width_cm=REAL_WIDTH_CM):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("圖片讀取失敗")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("找不到輪廓")
    a4_contour = max(contours, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(a4_contour, True)
    approx = cv2.approxPolyDP(a4_contour, epsilon, True)
    if len(approx) != 4:
        raise ValueError("無法偵測 A4 紙四邊形輪廓")
    pts = approx.reshape(4, 2).astype(np.float32)
    pts = sorted(pts, key=lambda p: p[0])
    left = sorted(pts[0:2], key=lambda p: p[1])
    right = sorted(pts[2:4], key=lambda p: p[1])
    tl, bl = left
    tr, br = right
    a4_pixel_width = np.linalg.norm(tr - tl)
    return float(a4_pixel_width / real_width_cm)


# ---- 完整 ch2-t1 評分（邏輯對齊 ch2-t1/main.py 的 main()）----
def grade_ch2t1(img_path, prep, clf, cp):
    """回傳 dict：score, label, conf, offset_cm, reason, result_img。"""
    out = {"score": -1, "label": None, "conf": None,
           "offset_cm": None, "reason": "", "result_img": None}

    # A4 px->cm
    try:
        pixel_per_cm = get_pixel_per_cm_from_a4(img_path)
    except ValueError as e:
        out["reason"] = f"a4_fail: {e}"
        out["result_img"] = cv2.imread(img_path)
        return out

    # prepare：找紙張 + 圈圖形 + binary
    stem = os.path.splitext(os.path.basename(img_path))[0]
    r = prep.prepare(img_path, OUT_DIR / "ready", stem)
    if not r["ok"]:
        out["reason"] = f"prepare_fail: {r['reason']}"
        out["result_img"] = r.get("vis")
        return out

    # classify：4 類
    label, conf = clf.classify(r["binary_bgr"])
    out["label"], out["conf"] = label, conf

    if label != TARGET:
        img = cv2.imread(r["color_path"])
        cv2.putText(img, f"Other: {label}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 0, 255), 2)
        out["score"] = 0
        out["reason"] = f"not_circle ({label})"
        out["result_img"] = img
        return out

    # 圓形：端點距離 -> offset -> 分數
    clean = cv2.imread(r["binary_path"], cv2.IMREAD_GRAYSCALE)
    inv_path = os.path.splitext(r["binary_path"])[0] + "_inv.jpg"
    cv2.imwrite(inv_path, 255 - clean)  # 白底黑線（check_point 期待輸入）
    px, result_img = cp.check_point(inv_path)
    offset = px / pixel_per_cm
    out["offset_cm"] = float(offset)
    cv2.putText(result_img, f"Offset : {offset:.2f} cm", (20, 50),
                cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 255, 0), 1)
    out["result_img"] = result_img

    if px == 0.0 or offset <= 1.2:
        out["score"] = 2
    elif offset <= 2.5:
        out["score"] = 1
    else:
        out["score"] = 0
    return out


# ---- ROI 框選 ----
class RoiState:
    def __init__(self):
        self.roi = None
        self.selecting = False
        self.p0 = None
        self.p1 = None

    def rect(self):
        if self.selecting and self.p0 and self.p1:
            x1, y1 = self.p0
            x2, y2 = self.p1
            return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        return self.roi


def make_mouse_cb(state, mode_on):
    def cb(event, x, y, flags, _p):
        if not mode_on():
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


SCORE_COLOR = {2: (0, 200, 0), 1: (0, 200, 200), 0: (0, 0, 255), -1: (0, 0, 255)}


def draw_result_overlay(view, res):
    """把分數/offset/形狀疊在即時畫面上。"""
    sc = res["score"]
    col = SCORE_COLOR.get(sc, (0, 0, 255))
    txt = f"SCORE = {sc}" if sc >= 0 else "SCORE = -1 (fail)"
    cv2.putText(view, txt, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.1, col, 3)
    y = 105
    if res["label"] is not None:
        cv2.putText(view, f"shape: {res['label']} ({(res['conf'] or 0)*100:.1f}%)",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
        y += 28
    if res["offset_cm"] is not None:
        cv2.putText(view, f"offset: {res['offset_cm']:.2f} cm",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
        y += 28
    if res["reason"]:
        cv2.putText(view, res["reason"], (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--device", default=None)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ready").mkdir(parents=True, exist_ok=True)

    print("[ch2t1] 載入模型中 ...（Preparer + Classifier）")
    prep = Preparer(device=args.device)         # PDMS2_web/models/paper_seg + sam2_b + shape
    clf = Classifier(device=args.device)        # PDMS2_web/models/shape_cls
    cp = check_point(SCALE=SCALE)

    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        print(f"[ch2t1] 無法開啟攝影機 {args.cam}")
        return

    WIN = "ch2-t1 live (g/space=grade, r=ROI, c=clear, q=quit)"
    cv2.namedWindow(WIN)
    roi_state = RoiState()
    roi_mode = {"on": False}
    cv2.setMouseCallback(WIN, make_mouse_cb(roi_state, lambda: roi_mode["on"]))

    last_res = None
    print("[ch2t1] g/space=評分  r=框ROI  c=清除  q/ESC=離開")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[ch2t1] 讀取失敗")
            break
        view = frame.copy()

        rect = roi_state.rect()
        if rect is not None:
            cv2.rectangle(view, (rect[0], rect[1]), (rect[2], rect[3]),
                          (0, 255, 255), 2)
            cv2.putText(view, "ROI", (rect[0], max(20, rect[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        mode = "ROI" if roi_state.roi else "FULL"
        cv2.putText(view, f"[{mode}] g/space=grade  r=ROI  c=clear  q=quit",
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        if last_res is not None:
            draw_result_overlay(view, last_res)

        cv2.imshow(WIN, view)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            roi_mode["on"] = True
            roi_state.roi = None
            print("[ch2t1] 框選模式：滑鼠拖曳畫框")
        if key == ord("c"):
            roi_mode["on"] = False
            roi_state.roi = None
            roi_state.selecting = False
            print("[ch2t1] 已清除 ROI")
        if key in (ord("g"), ord(" ")):
            # 取要評分的畫面（ROI 內或整張），存檔後跑完整流程
            H, W = frame.shape[:2]
            if roi_state.roi:
                x1, y1, x2, y2 = roi_state.roi
                x1 = max(0, min(x1, W - 1)); y1 = max(0, min(y1, H - 1))
                x2 = max(x1 + 1, min(x2, W)); y2 = max(y1 + 1, min(y2, H))
                shot = frame[y1:y2, x1:x2].copy()
            else:
                shot = frame
            ts = time.strftime("%Y%m%d_%H%M%S")
            shot_path = str(OUT_DIR / f"ch2-t1_{ts}.jpg")
            cv2.imwrite(shot_path, shot)
            print(f"\n[ch2t1] === 評分 {shot_path} ===")
            t0 = time.time()
            try:
                res = grade_ch2t1(shot_path, prep, clf, cp)
            except Exception as e:
                res = {"score": -1, "label": None, "conf": None,
                       "offset_cm": None, "reason": f"exception: {e}",
                       "result_img": shot}
            dt = time.time() - t0
            print(f"[ch2t1] score={res['score']}  label={res['label']}  "
                  f"offset={res['offset_cm']}  reason={res['reason']}  ({dt:.2f}s)")
            last_res = res
            # 存結果圖 + 另開視窗顯示
            if res["result_img"] is not None:
                res_path = str(OUT_DIR / f"ch2-t1_{ts}_result.jpg")
                cv2.imwrite(res_path, res["result_img"])
                cv2.imshow("ch2-t1 result", res["result_img"])

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
