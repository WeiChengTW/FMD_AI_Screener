"""
用現有 pipeline(紙張 mask + CV find_shape_bbox) 自動標註「單類 shape 偵測」資料集，
供訓練一顆取代 CV 的形狀定位 YOLO(暗環境更穩)。

輸出：
  shape_det_ds/
    images/train|val/*.jpg
    labels/train|val/*.txt   (YOLO 格式，class 0 = shape)
    vis/*.jpg                 (畫上自動標註框，供人工檢查/挑錯)
    data.yaml

用法：
  python bootstrap_shape_labels.py
  python bootstrap_shape_labels.py --val 0.2
標壞的：直接刪掉 vis/ 對應圖 → 再跑 --prune 會把 images/labels 內對應檔一起移除。
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

import cv2

# 重用 PDMS2_web/shape_pipeline 的紙張定位 + CV 找圖形
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "PDMS2_web"))
from shape_pipeline import (ShapePipeline, locate_paper, find_shape_bbox)

# 來源影像資料夾（整張照片）
SOURCES = [
    ROOT / "captures",
    ROOT.parent / "PDMS2_web" / "kid",   # 遞迴抓 ch2-t1/2/3
]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def collect_images():
    imgs = []
    for src in SOURCES:
        if not src.exists():
            continue
        for p in src.rglob("*"):
            if p.suffix.lower() not in IMG_EXT:
                continue
            n = p.name.lower()
            if "result" in n or "detected" in n or "cropped" in n or "_vis" in n:
                continue
            # kid 只取 ch2 畫圖三關
            if "kid" in str(src) and not any(k in n for k in ("ch2-t1", "ch2-t2", "ch2-t3")):
                continue
            imgs.append(p)
    return sorted(set(imgs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="shape_det_ds")
    ap.add_argument("--val", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out = ROOT / args.out
    if out.exists():
        shutil.rmtree(out)
    for sub in ["images/train", "images/val", "labels/train", "labels/val", "vis"]:
        (out / sub).mkdir(parents=True, exist_ok=True)

    imgs = collect_images()
    print(f"來源影像 {len(imgs)} 張")
    random.seed(args.seed)
    random.shuffle(imgs)
    n_val = int(len(imgs) * args.val)

    pipe = ShapePipeline()  # 只用它載好的 paper/sam 模型
    ok = fail = 0
    for i, p in enumerate(imgs):
        frame = cv2.imread(str(p))
        if frame is None:
            fail += 1
            continue
        mask = locate_paper(frame, pipe.paper, pipe.sam, pipe.device, pipe.paper_conf)
        bbox = find_shape_bbox(frame, mask) if mask is not None else None
        if bbox is None:
            fail += 1
            print(f"  [跳過] 定位失敗: {p.name}")
            continue

        x1, y1, x2, y2 = bbox
        H, W = frame.shape[:2]
        cx, cy = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H
        bw, bh = (x2 - x1) / W, (y2 - y1) / H

        split = "val" if i < n_val else "train"
        stem = f"{p.parent.name}_{p.stem}"
        cv2.imwrite(str(out / f"images/{split}/{stem}.jpg"), frame)
        (out / f"labels/{split}/{stem}.txt").write_text(
            f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
        vis = frame.copy()
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.imwrite(str(out / f"vis/{stem}.jpg"), vis)
        ok += 1

    (out / "data.yaml").write_text(
        f"path: {out.as_posix()}\ntrain: images/train\nval: images/val\n"
        f"nc: 1\nnames: ['shape']\n", encoding="utf-8")
    print(f"\n完成：標註成功 {ok}，失敗/跳過 {fail}")
    print(f"資料集 -> {out}")
    print(f"請檢查 {out/'vis'} 的框，標壞的把該圖從 vis/ 刪掉(或直接刪 images+labels 對應檔)。")


if __name__ == "__main__":
    main()
