"""
把 YOLOv8 segmentation 資料集（Roboflow 匯出的 polygon 標註）
就地轉成 YOLOv8 detection 資料集：每個多邊形取外接框(min/max) 當 bbox。

這是無損的位置轉換——用的是原本的人工標註，不需要任何模型預測。

seg  label 格式：  cls x1 y1 x2 y2 ... xn yn        (座標皆為 0~1 正規化)
det  label 格式：  cls xc yc w h                     (同樣正規化)

用法：
  python seg2det.py --src "crayon-graph.v2i.yolov8" --dst "crayon-graph-det"
"""

import argparse
import shutil
from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
SPLITS = ("train", "valid", "val", "test")


def poly_line_to_bbox(parts):
    """把一行 seg 標註(cls + 一串 x,y)轉成 det 的 'cls xc yc w h'。
    回傳字串；若格式不對(欄位不足或非多邊形)回傳 None。"""
    cls = parts[0]
    coords = parts[1:]
    if len(coords) < 6 or len(coords) % 2 != 0:
        return None  # 至少 3 個點才算多邊形，且座標需成對
    xs = coords[0::2]
    ys = coords[1::2]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xc = (xmin + xmax) / 2
    yc = (ymin + ymax) / 2
    w = xmax - xmin
    h = ymax - ymin
    if w <= 0 or h <= 0:
        return None
    return f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}"


def convert_label(src_txt: Path, dst_txt: Path, single: bool = False):
    """轉一個 label 檔。single=True 時把所有類別併成 class 0。
    回傳 (轉出行數, 跳過行數)。"""
    out_lines, skipped = [], 0
    for raw in src_txt.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split()
        if len(parts) == 5:  # 已經是 det 格式
            if single:
                parts[0] = "0"
            out_lines.append(" ".join(parts))
            continue
        try:
            cls = "0" if single else parts[0]
            nums = [cls] + [float(v) for v in parts[1:]]
        except ValueError:
            skipped += 1
            continue
        line = poly_line_to_bbox(nums)
        if line is None:
            skipped += 1
        else:
            out_lines.append(line)
    dst_txt.write_text(("\n".join(out_lines) + "\n") if out_lines else "",
                       encoding="utf-8")
    return len(out_lines), skipped


def clean_dir(d: Path):
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)


def find_splits(src: Path):
    found = {}
    for s in SPLITS:
        img, lbl = src / s / "images", src / s / "labels"
        if img.is_dir() and lbl.is_dir():
            found[s] = (img, lbl)
    return found


def read_names(src: Path):
    import yaml
    y = next(iter(src.glob("*.yaml")), None)
    if y is None:
        raise FileNotFoundError(f"{src} 內找不到 data.yaml")
    data = yaml.safe_load(y.read_text(encoding="utf-8"))
    names = data.get("names")
    return names, data.get("nc", len(names) if names else 0)


def write_yaml(dst: Path, splits: dict, names, nc):
    lines = [f"path: {dst.resolve().as_posix()}"]
    if "train" in splits:
        lines.append("train: train/images")
    val = "valid" if "valid" in splits else ("val" if "val" in splits else None)
    if val:
        lines.append(f"val: {val}/images")
    if "test" in splits:
        lines.append("test: test/images")
    lines += [f"nc: {nc}", f"names: {names}"]
    (dst / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="seg 資料集 -> det 資料集（外接框）")
    ap.add_argument("--src", required=True, help="來源 seg 資料集根目錄")
    ap.add_argument("--dst", required=True, help="輸出 det 資料集根目錄")
    ap.add_argument("--single", nargs="?", const="shape", default=None,
                    help="把所有類別併成單一類別（預設名稱 shape，可自訂如 --single object）")
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    splits = find_splits(src)
    if not splits:
        raise FileNotFoundError(f"{src} 找不到 train/valid/test 的 images/labels")
    if args.single:
        names, nc = [args.single], 1
    else:
        names, nc = read_names(src)

    total_lines, total_skip, total_imgs = 0, 0, 0
    for s, (img_dir, lbl_dir) in splits.items():
        out_img, out_lbl = dst / s / "images", dst / s / "labels"
        clean_dir(out_img)
        clean_dir(out_lbl)
        for p in img_dir.iterdir():
            if p.suffix.lower() in IMG_EXTS:
                shutil.copyfile(p, out_img / p.name)
                total_imgs += 1
        for p in lbl_dir.iterdir():
            if p.suffix.lower() == ".txt":
                n, sk = convert_label(p, out_lbl / p.name, single=bool(args.single))
                total_lines += n
                total_skip += sk
        print(f"[seg2det] {s}: 圖片複製、label 轉框完成")

    write_yaml(dst, splits, names, nc)
    print(f"[seg2det] 完成 -> {dst.resolve()}")
    print(f"[seg2det] 圖片 {total_imgs} 張、bbox {total_lines} 個"
          + (f"，跳過 {total_skip} 行異常" if total_skip else ""))
    print(f"[seg2det] 類別: {names}")


if __name__ == "__main__":
    main()
