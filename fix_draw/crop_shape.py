"""
路線 B：偵測紙張 -> 紙內用 OpenCV 找手繪圖形輪廓 -> 框起來 -> 切下來。

流程：
  1. 用 best.pt (paper 分割) 找出白紙區域，取信心最高的一張 paper mask
  2. 只在紙內把深色筆跡二值化 (Otsu)，避開紙張邊緣
  3. 把所有夠大的筆跡輪廓合併成一個外接框 = 手繪圖形位置
  4. 依框把圖形切下來 (crop)，之後可丟給分類模型

(可選) 切下來的圖再丟給分類模型 (.h5)；預設不分類，只做到切圖。
分類前處理：resize 224 -> 灰階 -> 反轉Otsu二值(黑底白線)。

用法：
  python crop_shape.py --dir some_folder                    # 只切圖(預設)
  python crop_shape.py --dir some_folder --save out         # 指定輸出資料夾
  python crop_shape.py --image one.jpg                      # 只跑一張
  python crop_shape.py --dir x --circle-model new_model.h5  # 接上分類模型
操作：任意鍵 = 下一張，  q / ESC = 中止
切下來的圖存在 <輸出>/crops/，可視化存在 <輸出>/vis/
"""

import argparse
from pathlib import Path

import cv2
import numpy as np


def pick_device(arg):
    if arg:
        return arg
    try:
        import torch
        return "0" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


class CircleClassifier:
    """ch2-t1 的 circle 分類模型 (Keras .h5)，接收 BGR 影像回傳 (類別, 信心)。"""

    def __init__(self, model_path, class_names=("Other", "circle_or_oval"),
                 image_size=(224, 224)):
        # 相容不同版本 optree 的 shim (與 ch2-t1/circle_or_oval.py 相同)
        try:
            import optree
            if not hasattr(optree, "tree_is_leaf"):
                def _leaf(x, *a, **k):
                    fn = getattr(optree, "treespec_is_leaf", None) \
                        or getattr(optree, "treespec_is_strict_leaf", None)
                    try:
                        return bool(fn(x)) if fn else False
                    except Exception:
                        return False
                optree.tree_is_leaf = _leaf
        except Exception:
            pass

        from tensorflow.keras.models import load_model
        self.class_names = list(class_names)
        self.image_size = image_size
        self.model = load_model(model_path)
        print(f"[circle] 模型載入完成: {model_path}")

    def preprocess(self, bgr):
        """複製 ch2-t1 的前處理：resize224 -> 灰階 -> 反轉Otsu二值(黑底白線)。"""
        img224 = cv2.resize(bgr, self.image_size, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(img224, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary  # uint8 (224,224), 0/255

    def predict_bgr(self, bgr):
        """bgr: OpenCV 影像。回傳 (類別名稱, 信心度 float)。"""
        binary = self.preprocess(bgr)
        # 模型輸入為 3 通道 /255 (與 load_img 讀二值 jpg 一致)
        rgb = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB).astype("float32") / 255.0
        pred = self.model.predict(rgb[None], verbose=0)[0]
        i = int(np.argmax(pred))
        return self.class_names[i], float(pred[i])


def get_paper_mask(frame, yolo, device, conf):
    """回傳信心最高的 paper mask (uint8, 0/255)，找不到回傳 None。"""
    res = yolo.predict(source=frame, conf=conf, device=device, verbose=False)[0]
    if res.masks is None or len(res.masks) == 0:
        return None
    confs = res.boxes.conf.cpu().numpy()
    best = int(np.argmax(confs))
    m = res.masks.data.cpu().numpy()[best]
    mask = (m > 0.5).astype(np.uint8)
    if mask.shape[:2] != frame.shape[:2]:
        mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    return mask * 255


def find_shape_bbox(frame, paper_mask, min_area_ratio=0.0005):
    """在紙內找手繪圖形的外接框。回傳 (x1,y1,x2,y2) 或 None，以及二值化 ink 圖。"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    paper_area = int((paper_mask > 0).sum())
    if paper_area == 0:
        return None, None

    # YOLO 的 paper mask 邊緣常溢出到黑板，往內縮一圈把邊界去掉
    k = max(5, int(0.035 * np.sqrt(paper_area)))
    inner = cv2.erode(paper_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    if int((inner > 0).sum()) == 0:
        return None, None

    # adaptive threshold 抓「局部變暗」的筆跡，抗白紙上不均勻的陰影漸層
    blk = int(0.06 * np.sqrt(paper_area))
    blk = max(15, blk | 1)  # 奇數
    adap = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, blk, 12)
    ink = ((adap > 0) & (inner > 0)).astype(np.uint8) * 255
    # 連接斷筆、去雜點
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = min_area_ratio * paper_area
    # 每個筆跡塊：(bbox, 中心點)
    cand = []
    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        cand.append(((x, y, w, h), (x + w / 2, y + h / 2)))
    if not cand:
        return None, ink

    # 圖形一定畫在紙張中央：只保留「中心落在紙張中央區域」的筆跡塊，
    # 白紙邊緣的陰影/雜訊在外圍會被排除；圖形的多筆(十字/直角)都在中央會保留
    xs = np.where(inner.any(axis=0))[0]
    ys = np.where(inner.any(axis=1))[0]
    px1, px2, py1, py2 = xs.min(), xs.max(), ys.min(), ys.max()
    mx = 0.22 * (px2 - px1)  # 中央區域：紙張 bbox 往內縮 22%
    my = 0.22 * (py2 - py1)
    cl, cr, ct, cb = px1 + mx, px2 - mx, py1 + my, py2 - my
    central = [b for b, (cx, cy) in cand if cl <= cx <= cr and ct <= cy <= cb]

    if not central:
        # 中央沒東西，退而取離紙張中心最近的單一塊
        pcx, pcy = (px1 + px2) / 2, (py1 + py2) / 2
        central = [min(cand, key=lambda t: (t[1][0] - pcx) ** 2
                       + (t[1][1] - pcy) ** 2)[0]]

    x1 = min(b[0] for b in central)
    y1 = min(b[1] for b in central)
    x2 = max(b[0] + b[2] for b in central)
    y2 = max(b[1] + b[3] for b in central)
    return (x1, y1, x2, y2), ink


def skeletonize_crop(bgr):
    """骨架化(同 ch2-t1 的 skeletonize)，回傳 BGR 顯示圖(黑底白骨架)。
    二值化改用 adaptive threshold，抗切圖上的陰影漸層(全域Otsu會把陰影當筆跡)。"""
    from skimage.morphology import skeletonize
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    blk = max(15, (gray.shape[0] // 5) | 1)  # 奇數
    binary = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, blk, 12)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)))
    skel = skeletonize(binary > 0).astype(np.uint8) * 255
    return cv2.cvtColor(skel, cv2.COLOR_GRAY2BGR)


def process(frame, yolo, device, conf, pad=30, size=0):
    """回傳 (可視化圖, 切下來的圖 or None)。size>0 時把方形crop縮成 size×size。"""
    vis = frame.copy()
    paper_mask = get_paper_mask(frame, yolo, device, conf)
    if paper_mask is None:
        cv2.putText(vis, "NO PAPER", (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 2)
        return vis, None

    # 畫紙張輪廓（藍）
    cnts, _ = cv2.findContours(paper_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, cnts, -1, (255, 128, 0), 2)

    bbox, _ = find_shape_bbox(frame, paper_mask)
    if bbox is None:
        cv2.putText(vis, "NO SHAPE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 2)
        return vis, None

    x1, y1, x2, y2 = bbox
    # 先往外擴 pad 像素，再依最長邊改成正方形(以中心對齊)
    x1, y1 = x1 - pad, y1 - pad
    x2, y2 = x2 + pad, y2 + pad
    H, W = frame.shape[:2]
    side = min(max(x2 - x1, y2 - y1), H, W)  # 邊長不超過畫面
    ccx, ccy = (x1 + x2) / 2, (y1 + y2) / 2
    cx1 = int(round(ccx - side / 2))
    cy1 = int(round(ccy - side / 2))
    # 若超出畫面就平移(而非裁掉)，維持正方形
    cx1 = max(0, min(cx1, W - side))
    cy1 = max(0, min(cy1, H - side))
    cx2, cy2 = cx1 + side, cy1 + side
    crop = frame[cy1:cy2, cx1:cx2].copy()
    if size > 0 and crop.size > 0:  # 統一縮成 size×size
        crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)

    cv2.rectangle(vis, (cx1, cy1), (cx2, cy2), (0, 255, 0), 3)
    cv2.putText(vis, "shape", (cx1, max(cy1 - 8, 18)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    return vis, crop


def _panel(img, h, text=None):
    """把單張圖縮到高度 h，並在頂端加標題列。"""
    if img is not None and img.size > 0:
        p = cv2.resize(img, (int(img.shape[1] * h / img.shape[0]), h))
    else:
        p = np.full((h, h, 3), 60, np.uint8)
        cv2.putText(p, "none", (20, h // 2), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (200, 200, 200), 2)
    bar = np.full((36, p.shape[1], 3), 30, np.uint8)
    if text:
        cv2.putText(bar, text, (8, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.65, (255, 255, 255), 2)
    return np.vstack([bar, p])


def show_pair(vis, crop, title, label=None, ok=None, skeleton=None):
    """可視化 / 切圖 / 骨架 三欄並排顯示；label 為分類結果字串。"""
    h = 560
    color = (0, 200, 0) if ok else (0, 0, 255)
    crop_txt = label if label else "crop"
    panels = [_panel(vis, h, "paper + shape"),
              _panel(crop, h, crop_txt)]
    if label:  # 分類結果用彩色蓋一次
        cv2.putText(panels[1], crop_txt, (8, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.65, color, 2)
    if skeleton is not None:
        panels.append(_panel(skeleton, h, "skeleton"))
    cv2.imshow(title, np.hstack(panels))


def main():
    ap = argparse.ArgumentParser(description="偵測紙張 + CV 找手繪圖形並切下來")
    ap.add_argument("--weights", default="best.pt", help="paper 分割 YOLO 權重")
    ap.add_argument("--dir", default=None, help="要跑的圖片資料夾")
    ap.add_argument("--image", default=None, help="只跑單張圖片")
    ap.add_argument("--conf", type=float, default=0.4, help="paper 偵測置信度門檻")
    ap.add_argument("--pad", type=int, default=30, help="圖形框往外擴的像素數")
    ap.add_argument("--size", type=int, default=0,
                    help="把方形切圖統一縮成 size×size(例如 224)，0=不縮放")
    ap.add_argument("--device", default=None, help="'0' GPU / 'cpu'，預設自動")
    ap.add_argument("--save", default=None, help="輸出資料夾（切圖+可視化），預設 <來源>_shape")
    ap.add_argument("--circle-model", default="",
                    help="circle 分類模型 (.h5) 路徑；預設空=只切圖不分類。"
                         "明天重訓好模型後填路徑即可接上")
    args = ap.parse_args()

    if not Path(args.weights).exists():
        print(f"[錯誤] 找不到權重 {args.weights}")
        return
    if not args.dir and not args.image:
        print("[錯誤] 請用 --dir 或 --image 指定輸入")
        return

    from ultralytics import YOLO
    device = pick_device(args.device)
    print(f"[crop] device = {device}, weights = {args.weights}")
    yolo = YOLO(args.weights)

    # 載入 ch2-t1 circle 分類器（可選）
    classifier = None
    if args.circle_model:
        if Path(args.circle_model).exists():
            print("[crop] 載入 circle 分類模型中…")
            classifier = CircleClassifier(args.circle_model)
        else:
            print(f"[crop][警告] 找不到 circle 模型 {args.circle_model}，只切圖不分類")

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

    out_dir = Path(args.save) if args.save else base.parent / f"{base.name}_shape"
    crop_dir = out_dir / "crops"
    vis_dir = out_dir / "vis"
    skel_dir = out_dir / "skeleton"
    crop_dir.mkdir(parents=True, exist_ok=True)
    vis_dir.mkdir(parents=True, exist_ok=True)
    skel_dir.mkdir(parents=True, exist_ok=True)

    win = "paper + shape (any key=next, q=quit)"
    print(f"[crop] 共 {len(imgs)} 張，任意鍵=下一張  q/ESC=中止")
    ok_cnt = 0
    for i, p in enumerate(imgs, 1):
        frame = cv2.imread(str(p))
        if frame is None:
            print(f"[{i}/{len(imgs)}] 讀取失敗：{p.name}")
            continue
        vis, crop = process(frame, yolo, device, args.conf, args.pad, args.size)
        cv2.imwrite(str(vis_dir / f"{p.stem}_vis.jpg"), vis)
        label, is_circle, skel = None, False, None
        if crop is not None and crop.size > 0:
            cv2.imwrite(str(crop_dir / f"{p.stem}_crop.jpg"), crop)
            skel = skeletonize_crop(crop)
            cv2.imwrite(str(skel_dir / f"{p.stem}_skel.jpg"), skel)
            ok_cnt += 1
            info = f"crop {crop.shape[1]}x{crop.shape[0]}"
            if classifier is not None:
                cls, conf = classifier.predict_bgr(crop)
                is_circle = (cls == "circle_or_oval")
                label = f"{cls}  {conf*100:.1f}%"
                info += f"  -> {label}"
            print(f"[{i}/{len(imgs)}] {p.name}  -> {info}")
        else:
            print(f"[{i}/{len(imgs)}] {p.name}  -> 未切到圖形")

        show_pair(vis, crop, win, label, is_circle, skel)
        key = cv2.waitKey(0) & 0xFF
        if key in (ord("q"), 27):
            print("[crop] 使用者中止")
            break
    cv2.destroyAllWindows()
    print(f"[crop] 完成，成功切圖 {ok_cnt}/{len(imgs)}")
    print(f"[crop] 切圖 -> {crop_dir.resolve()}")
    print(f"[crop] 骨架 -> {skel_dir.resolve()}")
    print(f"[crop] 可視化 -> {vis_dir.resolve()}")


if __name__ == "__main__":
    main()
