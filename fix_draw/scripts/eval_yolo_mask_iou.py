# eval_yolo_mask_iou.py
# -*- coding: utf-8 -*-
"""
量測 YOLO segmentation 模型的 mask IoU / Dice。

跟 `yolo val` 的差別：
  * `yolo val` 給的是 COCO 標準 mask mAP，逐實例、跨多個 IoU 門檻的綜合分數。
  * 這支給的是「逐張影像的 mask IoU 平均值」，跟本專案 pipeline 的實際用法一致
    （ch3-t1 / ch3-t3 / ch4-t1 都只取信心值最高的那一個 mask 來用）。
論文兩個數字都可以報：mAP 放表格、mean IoU 放內文。

支援兩種 Roboflow 匯出格式，會自動偵測：

  A) YOLOv8 Segmentation（多邊形 txt）
        <root>/images/xxx.jpg
        <root>/labels/xxx.txt   每行： 類別 x1 y1 x2 y2 ...（座標正規化 0~1）

  B) Semantic Segmentation Masks（PNG 遮罩，圖與遮罩平放同一層）
        <root>/xxx.jpg
        <root>/xxx_mask.png     像素值對應 _classes.csv，預設非 0 即前景

用法：
    python eval_yolo_mask_iou.py --model ../ch3-t1/models/best.pt --data eval/ch3-t1
    python eval_yolo_mask_iou.py --model ../ch4-t1/best.pt --data ../../paper_yolo/test
    python eval_yolo_mask_iou.py --model ../ch3-t1/models/best.pt --data eval/ch3-t1 \
           --classes paper --mode union --save-vis out_vis
"""
import argparse
import statistics
import sys
import warnings
from pathlib import Path

import cv2
import numpy as np

warnings.filterwarnings("ignore")

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
MASK_SUFFIX = "_mask.png"


def parse_args():
    ap = argparse.ArgumentParser(description="計算 YOLO segmentation 的 mask IoU / Dice")
    ap.add_argument("--model", required=True, help="權重路徑（.pt）")
    ap.add_argument("--data", required=True,
                    help="測試集根目錄；polygon 格式要有 images/ 與 labels/，"
                         "mask 格式則是圖與 *_mask.png 平放同一層")
    ap.add_argument("--gt", choices=["auto", "polygon", "mask"], default="auto",
                    help="GT 標註格式，預設自動偵測")
    ap.add_argument("--mask-value", type=int, default=-1,
                    help="mask 格式時，只把等於這個像素值的區域當前景（見 _classes.csv）；"
                         "預設 -1 表示非 0 即前景")
    ap.add_argument("--classes", default="",
                    help="只評估這些類別，逗號分隔，可用索引或名稱；預設全部。"
                         "（mask 格式的 GT 沒有類別之分，此選項只會過濾預測結果）")
    ap.add_argument("--mode", choices=["best", "union"], default="best",
                    help="best=只取信心值最高的一個 mask（與本專案 pipeline 一致，預設）；"
                         "union=把所有符合類別的 mask 聯集起來")
    ap.add_argument("--conf", type=float, default=0.25, help="信心值門檻")
    ap.add_argument("--imgsz", type=int, default=640, help="推論輸入尺寸")
    ap.add_argument("--save-vis", default="",
                    help="輸出疊圖到這個目錄：綠=GT、紅=預測、黃=重疊")
    return ap.parse_args()


def load_gt_mask(label_path: Path, h: int, w: int, keep_cls: set):
    """把 YOLO-seg 多邊形標註畫成二值遮罩；回傳 (mask, 多邊形數量, 是否為 bbox 格式)。"""
    mask = np.zeros((h, w), dtype=np.uint8)
    n_poly = 0
    bbox_only = False
    if not label_path.exists():
        return mask, 0, False

    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 7:
            # 5 個數字是 bbox 格式（cls cx cy w h），不是多邊形，無法算 mask IoU
            if len(parts) == 5:
                bbox_only = True
            continue
        cls = int(float(parts[0]))
        if keep_cls and cls not in keep_cls:
            continue
        coords = np.array([float(v) for v in parts[1:]], dtype=np.float32)
        if coords.size % 2:
            coords = coords[:-1]
        pts = coords.reshape(-1, 2) * np.array([w, h], dtype=np.float32)
        cv2.fillPoly(mask, [pts.astype(np.int32)], 1)
        n_poly += 1

    return mask, n_poly, bbox_only


def load_gt_png(mask_path: Path, h: int, w: int, mask_value: int):
    """讀 Roboflow semantic-mask PNG；回傳 (mask, 前景像素數, False)。"""
    if not mask_path.exists():
        return np.zeros((h, w), dtype=np.uint8), 0, False

    m = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    if m is None:
        return np.zeros((h, w), dtype=np.uint8), 0, False
    if m.ndim == 3:
        # 彩色遮罩（每類一個顏色）退化成「非黑即前景」
        m = m[:, :, :3].max(axis=2)

    mask = (m == mask_value) if mask_value >= 0 else (m > 0)
    mask = mask.astype(np.uint8)
    if mask.shape != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    return mask, int(mask.sum()), False


def resolve_layout(root: Path, gt_mode: str):
    """判斷資料集格式；回傳 (mode, img_dir, lbl_dir, images)。"""
    img_dir, lbl_dir = root / "images", root / "labels"
    has_polygon = img_dir.is_dir() and lbl_dir.is_dir()
    flat = [p for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
            and not p.name.endswith(MASK_SUFFIX)]
    has_mask = bool(flat) and any(root.glob(f"*{MASK_SUFFIX}"))

    if gt_mode == "auto":
        gt_mode = "polygon" if has_polygon else ("mask" if has_mask else "")
        if not gt_mode:
            return None, None, None, []

    if gt_mode == "polygon":
        if not has_polygon:
            print(f"polygon 格式需要 {img_dir} 與 {lbl_dir}，但找不到。", file=sys.stderr)
            return None, None, None, []
        images = sorted(p for p in img_dir.iterdir()
                        if p.suffix.lower() in IMAGE_EXTS)
        return "polygon", img_dir, lbl_dir, images

    if not has_mask:
        print(f"mask 格式需要 {root} 底下有圖片與 *{MASK_SUFFIX}，但找不到。", file=sys.stderr)
        return None, None, None, []
    return "mask", root, root, sorted(flat)


def predict_mask(model, img_path: Path, h: int, w: int, keep_cls: set, args):
    """推論並回傳二值遮罩；沒偵測到回傳全 0。"""
    # retina_masks=True 讓輸出的 mask 直接是原圖尺寸，省掉自己還原 letterbox 的麻煩
    res = model.predict(str(img_path), conf=args.conf, imgsz=args.imgsz,
                        retina_masks=True, verbose=False)[0]

    pred = np.zeros((h, w), dtype=np.uint8)
    if res.masks is None or len(res.masks.data) == 0:
        return pred, 0

    cls_arr = res.boxes.cls.cpu().numpy().astype(int)
    conf_arr = res.boxes.conf.cpu().numpy()
    idxs = [i for i in range(len(cls_arr)) if not keep_cls or cls_arr[i] in keep_cls]
    if not idxs:
        return pred, 0

    if args.mode == "best":
        idxs = [max(idxs, key=lambda i: conf_arr[i])]

    for i in idxs:
        m = res.masks.data[i].cpu().numpy()
        if m.shape != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        pred |= (m > 0.5).astype(np.uint8)

    return pred, len(idxs)


def iou_dice(gt: np.ndarray, pred: np.ndarray):
    inter = int(np.logical_and(gt, pred).sum())
    union = int(np.logical_or(gt, pred).sum())
    tot = int(gt.sum()) + int(pred.sum())
    # 兩邊都空白時視為完全正確，避免 0/0
    iou = 1.0 if union == 0 else inter / union
    dice = 1.0 if tot == 0 else 2 * inter / tot
    return iou, dice


def save_overlay(img_path: Path, gt, pred, out_dir: Path, iou: float):
    img = cv2.imread(str(img_path))
    if img is None:
        return
    overlay = img.copy()
    overlay[gt > 0] = (0, 255, 0)                      # GT 綠
    overlay[pred > 0] = (0, 0, 255)                    # 預測 紅
    overlay[np.logical_and(gt, pred)] = (0, 255, 255)  # 重疊 黃
    img = cv2.addWeighted(img, 0.55, overlay, 0.45, 0)
    for color, thick in (((255, 255, 255), 5), ((0, 0, 0), 2)):
        cv2.putText(img, f"IoU={iou:.3f}", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, color, thick)
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / f"{img_path.stem}_iou.jpg"), img)


def main():
    args = parse_args()
    from ultralytics import YOLO

    root = Path(args.data).resolve()
    if not root.is_dir():
        print(f"找不到目錄：{root}", file=sys.stderr)
        return 1
    gt_mode, img_dir, lbl_dir, images = resolve_layout(root, args.gt)
    if not gt_mode:
        print(f"{root} 認不出是 polygon 還是 mask 格式。", file=sys.stderr)
        return 1
    if not images:
        print(f"{img_dir} 裡沒有圖片。", file=sys.stderr)
        return 1

    model = YOLO(args.model)
    if model.task != "segment":
        print(f"這個權重是 task={model.task}，不是 segmentation，算不了 mask IoU。",
              file=sys.stderr)
        return 1

    # --classes 同時接受索引與名稱
    name2idx = {v: k for k, v in model.names.items()}
    keep_cls = set()
    for tok in (t.strip() for t in args.classes.split(",") if t.strip()):
        if tok.isdigit():
            keep_cls.add(int(tok))
        elif tok in name2idx:
            keep_cls.add(name2idx[tok])
        else:
            print(f"未知類別 '{tok}'，可用：{model.names}", file=sys.stderr)
            return 1

    gt_desc = "多邊形 txt" if gt_mode == "polygon" else (
        f"PNG 遮罩（前景={'非 0' if args.mask_value < 0 else args.mask_value}）")
    print(f"模型      : {args.model}")
    print(f"類別      : {model.names}"
          + (f"  （只評估 {sorted(keep_cls)}）" if keep_cls else ""))
    print(f"測試集    : {root}（{len(images)} 張）")
    print(f"GT 格式   : {gt_desc}")
    print(f"取樣方式  : {args.mode}   conf={args.conf}  imgsz={args.imgsz}")
    print("-" * 72)
    gt_col = "GT多邊形" if gt_mode == "polygon" else "GT前景%"
    print(f"{'影像':<34}{gt_col:>9}{'預測數':>7}{'IoU':>9}{'Dice':>9}")
    print("-" * 72)

    ious, dices, misses = [], [], []
    no_gt = 0
    bbox_warned = False
    vis_dir = Path(args.save_vis).resolve() if args.save_vis else None

    for p in images:
        img = cv2.imread(str(p))
        if img is None:
            print(f"{p.name[:34]:<34}{'讀取失敗':>34}")
            continue
        h, w = img.shape[:2]

        if gt_mode == "polygon":
            gt, n_gt, bbox_only = load_gt_mask(lbl_dir / f"{p.stem}.txt", h, w, keep_cls)
            gt_txt = f"{n_gt}"
        else:
            gt, n_gt, bbox_only = load_gt_png(
                lbl_dir / f"{p.stem}{MASK_SUFFIX}", h, w, args.mask_value)
            gt_txt = f"{n_gt / (h * w) * 100:.1f}"
        if bbox_only and not bbox_warned:
            print(f"  [警告] {p.stem}.txt 是 bbox 格式（5 欄）而非多邊形，"
                  f"這類標註會被當成空白 GT。請改匯出 YOLOv8 Segmentation 格式。")
            bbox_warned = True
        if n_gt == 0:
            no_gt += 1

        pred, n_pred = predict_mask(model, p, h, w, keep_cls, args)
        if n_pred == 0:
            misses.append(p.name)

        iou, dice = iou_dice(gt, pred)
        ious.append(iou)
        dices.append(dice)
        print(f"{p.name[:34]:<34}{gt_txt:>9}{n_pred:>7}{iou:>9.4f}{dice:>9.4f}")

        if vis_dir:
            save_overlay(p, gt, pred, vis_dir, iou)

    print("-" * 72)
    if not ious:
        print("沒有任何可評估的影像。")
        return 1

    sd = statistics.stdev(ious) if len(ious) > 1 else 0.0
    print(f"影像數            : {len(ious)}")
    print(f"Mean IoU          : {statistics.fmean(ious):.4f}  (SD {sd:.4f})")
    print(f"Median IoU        : {statistics.median(ious):.4f}")
    print(f"Min / Max IoU     : {min(ious):.4f} / {max(ious):.4f}")
    print(f"Mean Dice         : {statistics.fmean(dices):.4f}")
    for thr in (0.5, 0.75, 0.9):
        n = sum(1 for v in ious if v >= thr)
        print(f"IoU >= {thr:<4}       : {n}/{len(ious)}  ({n / len(ious) * 100:.1f}%)")
    print(f"完全沒偵測到的影像: {len(misses)}"
          + (f"  → {', '.join(misses[:5])}{' ...' if len(misses) > 5 else ''}"
             if misses else ""))
    if no_gt:
        print(f"[注意] 有 {no_gt} 張圖沒有對應的 GT 多邊形，"
              f"若非刻意的負樣本，請檢查 labels/ 是否齊全。")
    if vis_dir:
        print(f"疊圖已輸出        : {vis_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
