"""
資料增強：對 Roboflow (YOLO segmentation 格式) 資料集的每張圖做
曝光 / 對比 處理，讓模型更能適應不同環境光。

重點：這裡只做「光度變換」(亮度/對比/gamma/CLAHE)，
不改變幾何形狀，所以 segmentation 的 polygon 標註完全有效，
每張增強圖只要「複製同一個 .txt label」改名即可。

每張原圖會產生 1 張原圖 + 6 張增強 = 7 張（可自行增減 VARIATIONS）。

可單獨執行：
    python augment.py --dataset "path/to/roboflow_dataset" --out "dataset_aug"
也會被 train.py 呼叫。
"""

import argparse
import shutil
from pathlib import Path

import cv2
import numpy as np


# ------------------------- 光度變換 -------------------------
def adjust_gamma(img, gamma):
    """gamma > 1 變亮，gamma < 1 變暗。"""
    inv = 1.0 / gamma
    table = np.array(
        [((i / 255.0) ** inv) * 255 for i in range(256)], dtype=np.uint8
    )
    return cv2.LUT(img, table)


def adjust_contrast(img, alpha, beta=0):
    """alpha 為對比係數(>1 增強對比)，beta 為亮度偏移。"""
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)


def apply_clahe(img, clip=2.5, grid=8):
    """自適應直方圖均衡化，強化局部對比，對不均勻光照特別有效。"""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


# 每一項：(後綴名稱, 處理函式)。可自由增減。
VARIATIONS = {
    "bright": lambda im: adjust_gamma(im, 1.5),          # 曝光提高
    "dark": lambda im: adjust_gamma(im, 0.6),            # 曝光降低
    "high_contrast": lambda im: adjust_contrast(im, 1.4, -20),   # 高對比
    "low_contrast": lambda im: adjust_contrast(im, 0.75, 25),    # 低對比
    "clahe": lambda im: apply_clahe(im),                 # 局部對比強化
    "bright_contrast": lambda im: adjust_contrast(adjust_gamma(im, 1.3), 1.2, 0),  # 亮+對比
}


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def augment_split(images_dir: Path, labels_dir: Path,
                  out_images: Path, out_labels: Path):
    """對單一 split（例如 train）做增強。原圖也會被複製過去。"""
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    img_paths = [p for p in images_dir.iterdir() if p.suffix.lower() in IMG_EXTS]
    print(f"[augment] {images_dir} 共 {len(img_paths)} 張原圖")

    total = 0
    for img_path in img_paths:
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  [警告] 無法讀取，略過：{img_path.name}")
            continue

        stem = img_path.stem
        label_src = labels_dir / f"{stem}.txt"  # segmentation 標註

        def emit(suffix, image):
            """寫出一張圖，並複製對應 label（光度變換不影響標註）。"""
            nonlocal total
            new_stem = stem if suffix == "orig" else f"{stem}_{suffix}"
            cv2.imwrite(str(out_images / f"{new_stem}.jpg"), image)
            if label_src.exists():
                shutil.copyfile(label_src, out_labels / f"{new_stem}.txt")
            total += 1

        emit("orig", img)  # 保留原圖
        for suffix, fn in VARIATIONS.items():
            try:
                emit(suffix, fn(img))
            except Exception as e:  # noqa: BLE001
                print(f"  [警告] {suffix} 處理失敗 {img_path.name}: {e}")

    print(f"[augment] {out_images} 產生 {total} 張")
    return total


def find_split_dirs(dataset: Path):
    """
    支援兩種 Roboflow 結構：
      dataset/train/images, dataset/train/labels
      dataset/images/train, dataset/labels/train
    回傳 {split: (images_dir, labels_dir)}。
    """
    splits = {}
    for split in ("train", "valid", "val", "test"):
        a_img, a_lbl = dataset / split / "images", dataset / split / "labels"
        b_img, b_lbl = dataset / "images" / split, dataset / "labels" / split
        if a_img.is_dir() and a_lbl.is_dir():
            splits[split] = (a_img, a_lbl)
        elif b_img.is_dir() and b_lbl.is_dir():
            splits[split] = (b_img, b_lbl)
    return splits


def build_augmented_dataset(dataset_dir, out_dir, augment_splits=("train",)):
    """
    產生一份新的資料集：train 做增強，valid/test 原樣複製。
    回傳新的 data.yaml 路徑。
    """
    dataset = Path(dataset_dir).resolve()
    out = Path(out_dir).resolve()
    splits = find_split_dirs(dataset)
    if not splits:
        raise FileNotFoundError(
            f"在 {dataset} 找不到 train/valid/test 的 images/labels 結構"
        )

    for split, (img_dir, lbl_dir) in splits.items():
        out_img = out / split / "images"
        out_lbl = out / split / "labels"
        if split in augment_splits:
            augment_split(img_dir, lbl_dir, out_img, out_lbl)
        else:
            # 驗證/測試集不做增強，直接複製
            out_img.mkdir(parents=True, exist_ok=True)
            out_lbl.mkdir(parents=True, exist_ok=True)
            for p in img_dir.iterdir():
                if p.suffix.lower() in IMG_EXTS:
                    shutil.copyfile(p, out_img / p.name)
            for p in lbl_dir.iterdir():
                if p.suffix.lower() == ".txt":
                    shutil.copyfile(p, out_lbl / p.name)
            print(f"[augment] {split} 原樣複製完成")

    return write_data_yaml(dataset, out, splits)


def write_data_yaml(src_dataset: Path, out: Path, splits: dict):
    """依原始 data.yaml 的類別資訊，寫出指向增強資料夾的新 data.yaml。"""
    names, nc = read_names_from_yaml(src_dataset)

    def rel(split):
        return f"{split}/images"

    lines = [f"path: {out.as_posix()}"]
    if "train" in splits:
        lines.append(f"train: {rel('train')}")
    val_split = "valid" if "valid" in splits else ("val" if "val" in splits else None)
    if val_split:
        lines.append(f"val: {rel(val_split)}")
    if "test" in splits:
        lines.append(f"test: {rel('test')}")
    lines.append(f"nc: {nc}")
    lines.append(f"names: {names}")

    out_yaml = out / "data.yaml"
    out_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[augment] 已寫出 {out_yaml}")
    return out_yaml


def read_names_from_yaml(dataset: Path):
    """讀原始 data.yaml 取得 names / nc。找不到就報錯提醒。"""
    yaml_path = None
    for cand in dataset.glob("*.yaml"):
        yaml_path = cand
        break
    if yaml_path is None:
        raise FileNotFoundError(f"在 {dataset} 找不到 data.yaml（Roboflow 匯出應含此檔）")

    try:
        import yaml  # PyYAML，ultralytics 會一併安裝
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        names = data.get("names")
        nc = data.get("nc", len(names) if names else 0)
        return names, nc
    except ImportError:
        # 沒有 PyYAML 時的簡易解析
        raise ImportError("請先安裝 pyyaml：pip install pyyaml")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="曝光/對比資料增強")
    ap.add_argument("--dataset", required=True, help="Roboflow 資料集根目錄")
    ap.add_argument("--out", default="dataset_aug", help="輸出增強資料集目錄")
    args = ap.parse_args()
    yaml_path = build_augmented_dataset(args.dataset, args.out)
    print(f"完成，訓練時使用：{yaml_path}")
