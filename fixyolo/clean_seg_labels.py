"""
清理 YOLO segmentation 標註中的無效多邊形。

問題：Roboflow 匯出的 label 混入了退化多邊形（少於 3 個點、含 (0,0)
哨兵點、或面積趨近 0 的線段），與正常 polygon 混在同一個 seg 資料集，
會導致 ultralytics 訓練時報「segment dataset incorrectly formatted」。

規則（逐行判斷，保留好的行、只丟壞的行）：
  * token 數需為奇數且 >= 7（class + 至少 3 個點）
  * 座標 clip 到 [0,1]
  * 去除面積趨近 0 的多邊形
空的 label 檔會保留（ultralytics 視為背景圖，允許）。

用法：
  python clean_seg_labels.py --root dataset_aug            # 直接就地清理
  python clean_seg_labels.py --root dataset_aug --dry-run  # 只統計不改檔
  python clean_seg_labels.py --root cut_shape --dry-run
"""

import argparse
import glob
import os
from pathlib import Path

MIN_POINTS = 3
MIN_AREA = 1e-6  # 正規化座標下的 bbox 面積下限


def clean_line(tokens):
    """回傳清理後的行字串，若該多邊形無效則回傳 None。"""
    if len(tokens) < 7 or (len(tokens) - 1) % 2 != 0:
        return None
    cls = tokens[0]
    coords = [float(t) for t in tokens[1:]]
    pts = [(min(1.0, max(0.0, coords[i])), min(1.0, max(0.0, coords[i + 1])))
           for i in range(0, len(coords), 2)]
    if len(pts) < MIN_POINTS:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if (max(xs) - min(xs)) * (max(ys) - min(ys)) < MIN_AREA:
        return None
    flat = " ".join(f"{v:.6g}" for p in pts for v in p)
    return f"{cls} {flat}"


def process(root: Path, dry_run: bool):
    label_files = glob.glob(str(root / "**" / "labels" / "*.txt"), recursive=True)
    if not label_files:
        # 也支援 labels/<split> 結構
        label_files = glob.glob(str(root / "**" / "*.txt"), recursive=True)
    files_changed = 0
    lines_kept = 0
    lines_dropped = 0
    for f in label_files:
        with open(f, "r") as fh:
            raw = fh.read().strip().splitlines()
        out = []
        dropped_here = 0
        for ln in raw:
            toks = ln.split()
            if not toks:
                continue
            cleaned = clean_line(toks)
            if cleaned is None:
                dropped_here += 1
            else:
                out.append(cleaned)
        lines_kept += len(out)
        lines_dropped += dropped_here
        if dropped_here:
            files_changed += 1
            if not dry_run:
                with open(f, "w") as fh:
                    fh.write("\n".join(out) + ("\n" if out else ""))
    return len(label_files), files_changed, lines_kept, lines_dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--drop-cache", action="store_true",
                    help="清理後刪除 *.cache（下次訓練會重建）")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    total, changed, kept, dropped = process(root, args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"[{mode}] {root}")
    print(f"  label 檔總數: {total}")
    print(f"  受影響檔數  : {changed}")
    print(f"  保留多邊形行: {kept}")
    print(f"  丟棄無效行  : {dropped}")

    if args.drop_cache and not args.dry_run:
        n = 0
        for c in glob.glob(str(root / "**" / "*.cache"), recursive=True):
            os.remove(c)
            n += 1
            print(f"  已刪除 cache: {c}")
        print(f"  共刪除 {n} 個 cache")


if __name__ == "__main__":
    main()
