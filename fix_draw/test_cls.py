"""
端到端測試 ch2 完整流程（把每一步拆開、明確印出來，方便確認順序）：
  step1  paper_seg(YOLO bbox) + SAM2  找出紙張 mask   <-- 先找紙張
  step2  在「紙張 mask 範圍內」用 CV 找出手繪圖形 bbox
  step3  切正方形 -> 黑底白線 binary(224)
  step4  4 類分類 (circle / cross / other / square)

重用 PDMS2_web/shape_pipeline 的模型與函式，模型都在 PDMS2_web/models/。

用法：
  python test_cls.py                       # 開相機，SPACE/s=辨識  q/ESC=離開
  python test_cls.py --image one.jpg       # 只跑單張
  python test_cls.py --dir some_folder     # 逐張跑資料夾
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "PDMS2_web"))
from shape_pipeline import (ShapePipeline, get_paper_bbox, sam_mask_from_bbox,
                            paper_mask_cv, find_shape_bbox, crop_square, to_binary)

OUT_DIR = ROOT / "test_cls_out"


def locate_paper_verbose(frame, pipe):
    """明確做『先找紙張』並印出用哪種方法。回傳 (mask, 方法字串) 或 (None, ...)。"""
    H, W = frame.shape[:2]
    frame_area = H * W
    # step1: paper_seg 出 bbox -> SAM2 精修 mask
    bbox = get_paper_bbox(frame, pipe.paper, pipe.device, pipe.paper_conf)
    mask = sam_mask_from_bbox(frame, pipe.sam, bbox, pipe.device) if bbox is not None else None
    if mask is not None and int((mask > 0).sum()) >= 0.3 * frame_area:
        return mask, "paper_seg bbox + SAM2"
    # fallback: CV 最大亮色區塊
    cv_mask = paper_mask_cv(frame)
    if cv_mask is not None and int((cv_mask > 0).sum()) >= 0.3 * frame_area:
        return cv_mask, "CV fallback (paper_seg 太小)"
    return (mask if mask is not None else cv_mask), "低信心(可能不準)"


def run_full(frame, pipe, out_dir, stem):
    """把完整流程逐步跑並印出。回傳 dict(vis, ok, label, conf, binary)。"""
    H, W = frame.shape[:2]
    vis = frame.copy()

    # === step1: 先找紙張 ===
    mask, method = locate_paper_verbose(frame, pipe)
    if mask is None or int((mask > 0).sum()) == 0:
        print("  step1 找紙張 -> 失敗（找不到紙張）")
        cv2.putText(vis, "NO PAPER", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        return {"ok": False, "reason": "no_paper", "vis": vis}
    area_pct = 100 * int((mask > 0).sum()) / (H * W)
    print(f"  step1 找紙張 -> OK（{method}，佔畫面 {area_pct:.1f}%）")
    # 把紙張 mask 疊成半透明藍，並畫輪廓
    blue = np.zeros_like(vis); blue[mask > 0] = (255, 128, 0)
    vis = cv2.addWeighted(vis, 1.0, blue, 0.25, 0)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, cnts, -1, (255, 128, 0), 2)

    # === step2: 在紙張 mask 範圍內找圖形 ===
    bbox = find_shape_bbox(frame, mask)
    if bbox is None:
        print("  step2 找圖形 -> 失敗（紙張內找不到圖形）")
        cv2.putText(vis, "NO SHAPE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        return {"ok": False, "reason": "no_shape", "vis": vis}
    print(f"  step2 找圖形 -> OK bbox={bbox}")

    # === step3: 切圖 + binary ===
    crop, sq = crop_square(frame, bbox, pipe.pad)
    cv2.rectangle(vis, (sq[0], sq[1]), (sq[2], sq[3]), (0, 255, 0), 3)
    binary224 = cv2.resize(to_binary(crop), (pipe.size, pipe.size), interpolation=cv2.INTER_AREA)
    bin_bgr = cv2.cvtColor(binary224, cv2.COLOR_GRAY2BGR)

    # === step4: 分類 ===
    label, conf = pipe.classify_binary(bin_bgr)
    print(f"  step4 分類 -> {label} ({conf*100:.1f}%)")
    cv2.putText(vis, f"{label} {conf*100:.1f}%", (sq[0], max(sq[1] - 10, 24)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / f"{stem}_vis.jpg"), vis)
    cv2.imwrite(str(out_dir / f"{stem}_binary.jpg"), binary224)
    return {"ok": True, "label": label, "conf": conf, "vis": vis, "binary": bin_bgr}


def show(result, title):
    vis = result.get("vis")
    if vis is None:
        return
    h = 480
    left = cv2.resize(vis, (int(vis.shape[1] * h / vis.shape[0]), h))
    if result["ok"]:
        right = cv2.resize(result["binary"], (h, h))
        cv2.putText(right, f'{result["label"]} {result["conf"]*100:.1f}%', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        canvas = cv2.hconcat([left, right])
    else:
        canvas = left
    cv2.imshow(title, canvas)


def main():
    ap = argparse.ArgumentParser(description="ch2 完整流程端到端測試（逐步顯示）")
    ap.add_argument("--image", default=None)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 只借模型；形狀定位這支測試用 CV（傳不存在路徑觸發 CV），紙張仍先用 paper_seg+SAM2
    pipe = ShapePipeline(device=args.device, shape_det_weights="__use_cv__")
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

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
        win = "test_cls (any key=next, q=quit)"
        for i, p in enumerate(imgs, 1):
            frame = cv2.imread(str(p))
            if frame is None:
                print(f"[{i}/{len(imgs)}] 讀取失敗：{p.name}")
                continue
            print(f"[{i}/{len(imgs)}] {p.name}")
            r = run_full(frame, pipe, OUT_DIR, p.stem)
            show(r, win)
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
    print("SPACE/s = 拍照並辨識   q/ESC = 離開")
    win = "test_cls camera (SPACE=classify, q=quit)"
    while True:
        ok, frame = cap.read()
        if not ok:
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
            r = run_full(frame, pipe, OUT_DIR, "shot")
            show(r, "result (any key=back)")
            cv2.waitKey(0)
            cv2.destroyWindow("result (any key=back)")
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
