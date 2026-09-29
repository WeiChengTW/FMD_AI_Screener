"""
把 class_data/<class>/*.jpg 切成 ultralytics classify 需要的結構，並對 train 做幾何增強：
  class_data_split/
    train/<class>/...   ← 每張原圖 -> 原圖 + 平移 + 旋轉15° + 上下顛倒 = 4 張
    val/<class>/...      ← 保持原圖，不增強（避免近似重複洩漏灌水 val 準確率）

白底手繪圖：旋轉/平移的補邊填白 (255)。

用法：
  python split_cls_dataset.py --src class_data --dst class_data_split --val 0.2
  python split_cls_dataset.py --no-aug            # 只切分不增強
"""
import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
# binary 圖為黑底白形，補邊要填黑以配合背景（3 通道各給 0，避免只填單一通道變色）
BG = (0, 0, 0)


def aug_shift(img, dx_frac=0.1, dy_frac=0.1):
    """平移：往右下各偏移影像尺寸的一定比例，補邊填黑（配合黑底）。"""
    h, w = img.shape[:2]
    M = np.float32([[1, 0, int(w * dx_frac)], [0, 1, int(h * dy_frac)]])
    return cv2.warpAffine(img, M, (w, h), borderValue=BG)


def aug_rotate(img, angle=15):
    """繞中心旋轉，補邊填黑（配合黑底）。"""
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), borderValue=BG)


def aug_vflip(img):
    """上下顛倒。"""
    return cv2.flip(img, 0)


# 後綴 -> 增強函式（原圖另外保留）
AUGS = {
    "shift": aug_shift,
    "rot15": aug_rotate,
    "vflip": aug_vflip,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="class_data")
    ap.add_argument("--dst", default="class_data_split")
    ap.add_argument("--val", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-aug", action="store_true", help="只切分，不做增強")
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    if dst.exists():
        shutil.rmtree(dst)
    random.seed(args.seed)

    classes = sorted(p.name for p in src.iterdir() if p.is_dir())
    print(f"classes = {classes}")

    for c in classes:
        files = [f for f in (src / c).iterdir() if f.suffix.lower() in IMG_EXT]
        random.shuffle(files)
        n_val = int(len(files) * args.val)
        val_files, train_files = files[:n_val], files[n_val:]

        # val：原圖直接複製
        (dst / "val" / c).mkdir(parents=True, exist_ok=True)
        for f in val_files:
            shutil.copy2(f, dst / "val" / c / f.name)

        # train：原圖 + 3 種增強
        out_train = dst / "train" / c
        out_train.mkdir(parents=True, exist_ok=True)
        n_train_out = 0
        for f in train_files:
            img = cv2.imread(str(f))
            if img is None:
                print(f"  [警告] 無法讀取，略過：{f.name}")
                continue
            cv2.imwrite(str(out_train / f.name), img)  # 原圖
            n_train_out += 1
            if not args.no_aug:
                for suffix, fn in AUGS.items():
                    out_name = f"{f.stem}_{suffix}{f.suffix}"
                    cv2.imwrite(str(out_train / out_name), fn(img))
                    n_train_out += 1

        print(f"  {c}: train_orig={len(train_files)} -> train_out={n_train_out}, val={len(val_files)}")

    print(f"done -> {dst}")


if __name__ == "__main__":
    main()
