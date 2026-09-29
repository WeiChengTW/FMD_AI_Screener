"""
先用 paper model (best.pt) 定位並切出紙張，
再用 ch2-t1 的形狀偵測模型 (YOLO.pt, 5類 circle/cross/diamond/rectangle/triangle)
把紙上「所有」形狀一個一個切下來，逐張顯示。

與 crop_shape.py 的差別：
  crop_shape.py    = 純 OpenCV 找單一置中圖形 (無需形狀模型)
  crop_shapes_yolo = 用 ch2-t1 的 YOLO 偵測，一張紙可切出多個形狀、且附類別

用法：
  python crop_shapes_yolo.py --dir some_folder            # 逐張顯示
  python crop_shapes_yolo.py --image one.jpg
  python crop_shapes_yolo.py --dir x --size 224           # 切圖統一 224x224
  python crop_shapes_yolo.py --dir x --shape-conf 0.25    # 調形狀偵測門檻
操作：任意鍵 = 下一張，  q / ESC = 中止
輸出：<來源>_shapes/crops/  (每個形狀一張)、vis/ (紙張+所有框)
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

from crop_shape import get_paper_mask, pick_device

SHAPE_MODEL = "../PDMS2_web/ch2-t1/model/YOLO.pt"


def crop_paper(frame, paper_mask):
    """只保留紙張區域(區外填白)，並切到外接框。回傳 (crop, (ox,oy))。
    用多邊形逼近把 mask 簡化成乾淨的紙張四邊形，抹掉溢出到桌墊/黑板的小突起。"""
    if int((paper_mask > 0).sum()) == 0:
        return frame.copy(), (0, 0)
    cnts, _ = cv2.findContours(paper_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
    clean = np.zeros_like(paper_mask)
    cv2.drawContours(clean, [approx], -1, 255, cv2.FILLED)
    # 再往內縮一點點，確保完全不含桌墊/黑板邊
    area = int((clean > 0).sum())
    k = max(3, int(0.012 * np.sqrt(area)))
    clean = cv2.erode(clean, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    # 紙張外填白，讓後續偵測看不到桌墊
    out = frame.copy()
    out[clean == 0] = (255, 255, 255)
    xs = np.where(clean.any(axis=0))[0]
    ys = np.where(clean.any(axis=1))[0]
    x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
    return out[y1:y2, x1:x2].copy(), (x1, y1)


def to_binary(bgr):
    """把形狀切圖轉成黑底白線(同 ch2-t1 模型輸入格式)。
    用 adaptive threshold 抗陰影漸層。回傳單通道 uint8 (0/255)。"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    blk = max(15, (gray.shape[0] // 5) | 1)
    b = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, blk, 12)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)))
    # 只留最大連通塊 = 主要圖形，去掉紙格/邊緣的零星雜線
    n, lbl, st, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    if n > 1:
        biggest = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        b = (lbl == biggest).astype(np.uint8) * 255
    return b


def detect_shapes(paper_crop, shape_yolo, device, conf, iou, pad, size):
    """在紙張切圖上偵測所有形狀。回傳 list of dict(bbox, cls, conf, crop)。"""
    res = shape_yolo.predict(source=paper_crop, conf=conf, iou=iou,
                             device=device, verbose=False)[0]
    names = res.names
    out = []
    if res.boxes is None or len(res.boxes) == 0:
        return out, names
    H, W = paper_crop.shape[:2]
    boxes = res.boxes.xyxy.cpu().numpy()
    clss = res.boxes.cls.cpu().numpy().astype(int)
    confs = res.boxes.conf.cpu().numpy()
    for (bx1, by1, bx2, by2), c, cf in zip(boxes, clss, confs):
        x1 = max(0, int(bx1) - pad)
        y1 = max(0, int(by1) - pad)
        x2 = min(W, int(bx2) + pad)
        y2 = min(H, int(by2) + pad)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = paper_crop[y1:y2, x1:x2].copy()
        if size > 0 and crop.size > 0:
            crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
        out.append({"bbox": (x1, y1, x2, y2), "cls": names[c],
                    "conf": float(cf), "crop": crop})
    return out, names


def draw_vis(paper_crop, dets):
    vis = paper_crop.copy()
    for d in dets:
        x1, y1, x2, y2 = d["bbox"]
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis, f'{d["cls"]} {d["conf"]:.2f}', (x1, max(y1 - 6, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return vis


def make_montage(crops, cell=200, cols=4):
    """把多個形狀切圖排成格狀montage。"""
    if not crops:
        m = np.full((cell, cell, 3), 60, np.uint8)
        cv2.putText(m, "no shape", (20, cell // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        return m
    cols = min(cols, len(crops))
    rows = (len(crops) + cols - 1) // cols
    canvas = np.full((rows * cell, cols * cell, 3), 40, np.uint8)
    for i, c in enumerate(crops):
        cc = cv2.resize(c, (cell, cell))
        r, col = divmod(i, cols)
        canvas[r * cell:(r + 1) * cell, col * cell:(col + 1) * cell] = cc
    return canvas


def show(paper_crop, dets, title):
    h = 560
    left = paper_crop
    left = cv2.resize(left, (int(left.shape[1] * h / left.shape[0]), h))
    right = make_montage([d["crop"] for d in dets])
    right = cv2.resize(right, (int(right.shape[1] * h / right.shape[0]), h))
    cv2.imshow(title, np.hstack([left, right]))


def main():
    ap = argparse.ArgumentParser(description="paper定位 + ch2-t1 YOLO 切出所有形狀")
    ap.add_argument("--paper-weights", default="best.pt", help="紙張分割權重")
    ap.add_argument("--shape-weights", default=SHAPE_MODEL, help="ch2-t1 形狀偵測權重")
    ap.add_argument("--dir", default=None, help="要跑的圖片資料夾")
    ap.add_argument("--image", default=None, help="只跑單張圖片")
    ap.add_argument("--paper-conf", type=float, default=0.4, help="紙張偵測門檻")
    ap.add_argument("--shape-conf", type=float, default=0.25, help="形狀偵測門檻")
    ap.add_argument("--iou", type=float, default=0.3, help="形狀 NMS IoU")
    ap.add_argument("--pad", type=int, default=30, help="形狀框往外擴的像素數")
    ap.add_argument("--size", type=int, default=0, help="切圖統一縮成 size×size，0=不縮放")
    ap.add_argument("--by-class", action="store_true",
                    help="依預測類別把切圖分到 crops/<類別>/ 子資料夾(收集訓練資料用)")
    ap.add_argument("--binary", action="store_true",
                    help="另存黑底白線二值圖到 crops_binary/(同 ch2-t1 模型輸入格式)")
    ap.add_argument("--device", default=None, help="'0' GPU / 'cpu'，預設自動")
    ap.add_argument("--save", default=None, help="輸出資料夾，預設 <來源>_shapes")
    args = ap.parse_args()

    for w in (args.paper_weights, args.shape_weights):
        if not Path(w).exists():
            print(f"[錯誤] 找不到權重 {w}")
            return
    if not args.dir and not args.image:
        print("[錯誤] 請用 --dir 或 --image 指定輸入")
        return

    from ultralytics import YOLO
    device = pick_device(args.device)
    print(f"[shapes] device={device}")
    paper_yolo = YOLO(args.paper_weights)
    shape_yolo = YOLO(args.shape_weights)
    print(f"[shapes] 形狀類別: {shape_yolo.names}")

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    if args.image:
        imgs = [Path(args.image)]
        base = Path(args.image).parent
    else:
        src = Path(args.dir)
        if not src.is_dir():
            print(f"[錯誤] 找不到資料夾 {src}")
            return
        imgs = sorted(p for p in src.iterdir() if p.suffix.lower() in exts)
        base = src
    if not imgs:
        print("[錯誤] 沒有圖片")
        return

    out_dir = Path(args.save) if args.save else base.parent / f"{base.name}_shapes"
    crop_dir = out_dir / "crops"
    vis_dir = out_dir / "vis"
    bin_dir = out_dir / "crops_binary"
    crop_dir.mkdir(parents=True, exist_ok=True)
    vis_dir.mkdir(parents=True, exist_ok=True)
    if args.binary:
        bin_dir.mkdir(parents=True, exist_ok=True)

    win = "paper -> shapes (any key=next, q=quit)"
    print(f"[shapes] 共 {len(imgs)} 張，任意鍵=下一張  q/ESC=中止")
    total_shapes = 0
    for i, p in enumerate(imgs, 1):
        frame = cv2.imread(str(p))
        if frame is None:
            print(f"[{i}/{len(imgs)}] 讀取失敗：{p.name}")
            continue

        paper_mask = get_paper_mask(frame, paper_yolo, device, args.paper_conf)
        if paper_mask is None:
            print(f"[{i}/{len(imgs)}] {p.name} -> 未偵測到紙張")
            show(frame, [], win)
            if (cv2.waitKey(0) & 0xFF) in (ord("q"), 27):
                break
            continue

        paper_crop, _ = crop_paper(frame, paper_mask)
        dets, _ = detect_shapes(paper_crop, shape_yolo, device,
                                args.shape_conf, args.iou, args.pad, args.size)
        total_shapes += len(dets)

        vis = draw_vis(paper_crop, dets)
        cv2.imwrite(str(vis_dir / f"{p.stem}_vis.jpg"), vis)
        for j, d in enumerate(dets):
            if args.by_class:  # 依預測類別分子資料夾，方便之後人工挑錯
                dst = crop_dir / d["cls"]
                dst.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(dst / f"{p.stem}_{j}.jpg"), d["crop"])
            else:
                cv2.imwrite(str(crop_dir / f"{p.stem}_{j}_{d['cls']}.jpg"), d["crop"])
            if args.binary:  # 另存黑底白線二值圖
                bpath = (bin_dir / d["cls"]) if args.by_class else bin_dir
                bpath.mkdir(parents=True, exist_ok=True)
                name = f"{p.stem}_{j}.jpg" if args.by_class \
                    else f"{p.stem}_{j}_{d['cls']}.jpg"
                cv2.imwrite(str(bpath / name), to_binary(d["crop"]))
        summary = ", ".join(f"{d['cls']}({d['conf']:.2f})" for d in dets) or "無"
        print(f"[{i}/{len(imgs)}] {p.name} -> {len(dets)} 形狀: {summary}")

        show(paper_crop, dets, win)
        if (cv2.waitKey(0) & 0xFF) in (ord("q"), 27):
            print("[shapes] 使用者中止")
            break
    cv2.destroyAllWindows()
    print(f"[shapes] 完成，共切出 {total_shapes} 個形狀")
    print(f"[shapes] 切圖 -> {crop_dir.resolve()}")
    if args.binary:
        print(f"[shapes] 黑底白線 -> {bin_dir.resolve()}")
    print(f"[shapes] 可視化 -> {vis_dir.resolve()}")


if __name__ == "__main__":
    main()
