"""
測試腳本：開相機拍一張照片，用訓練好的 YOLOv8 模型偵測物件，
再用 SAM2 依 YOLO 的框(bbox)做精細分割，把結果畫出來。

操作：
  相機預覽視窗中
    空白鍵 / s = 拍照並執行 YOLO + SAM2 分割
    q / ESC   = 離開
  結果視窗按任意鍵回到預覽繼續拍。

用法：
  python main.py                        # 用本資料夾 best.pt + sam2_b.pt
  python main.py --weights best.pt --sam sam2_b.pt --cam 0
  python main.py --image some.jpg       # 不開相機，直接跑一張圖

首次執行 SAM2 會自動下載權重 (sam2_b.pt 約 ~150MB)。
若沒有 GPU 可加 --device cpu（SAM2 在 CPU 上較慢）。
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


def overlay_masks(image, masks, boxes=None, names=None, classes=None, confs=None):
    """把 SAM2 的 masks 半透明疊到影像上，並畫 YOLO 的框與類別。"""
    out = image.copy()
    rng = np.random.default_rng(42)
    for i, mask in enumerate(masks):
        m = mask.astype(bool)
        color = rng.integers(60, 256, size=3).tolist()
        colored = np.zeros_like(out)
        colored[m] = color
        out = cv2.addWeighted(out, 1.0, colored, 0.45, 0)
        # 畫輪廓讓邊界更清楚
        contours, _ = cv2.findContours(
            m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(out, contours, -1, color, 2)

    if boxes is not None:
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = [int(v) for v in box]
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = ""
            if names is not None and classes is not None:
                label = str(names.get(int(classes[i]), int(classes[i])))
            if confs is not None:
                label = f"{label} {confs[i]:.2f}".strip()
            if label:
                cv2.putText(out, label, (x1, max(y1 - 8, 18)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return out


def segment(frame, yolo, sam, device, conf):
    """YOLO 偵測 -> 以 bbox 提示 SAM2 分割。回傳疊圖結果。"""
    res = yolo.predict(source=frame, conf=conf, device=device, verbose=False)[0]

    if res.boxes is None or len(res.boxes) == 0:
        print("[main] YOLO 未偵測到任何物件")
        return frame.copy()

    boxes = res.boxes.xyxy.cpu().numpy()
    classes = res.boxes.cls.cpu().numpy().astype(int)
    confs = res.boxes.conf.cpu().numpy()
    names = res.names

    # 用 YOLO 的框當作 SAM2 的提示，取得精細 mask
    sam_res = sam.predict(source=frame, bboxes=boxes, device=device, verbose=False)[0]

    masks = []
    if sam_res.masks is not None:
        for m in sam_res.masks.data.cpu().numpy():
            mm = (m > 0.5).astype(np.uint8)
            if mm.shape[:2] != frame.shape[:2]:
                mm = cv2.resize(mm, (frame.shape[1], frame.shape[0]),
                                interpolation=cv2.INTER_NEAREST)
            masks.append(mm)
        print(f"[main] YOLO 偵測 {len(boxes)} 個框，SAM2 產生 {len(masks)} 個 mask")
    else:
        print("[main] SAM2 未產生 mask，只顯示 YOLO 框")

    return overlay_masks(frame, masks, boxes, names, classes, confs)


def main():
    ap = argparse.ArgumentParser(description="YOLOv8 + SAM2 分割測試")
    ap.add_argument("--weights", default="best.pt", help="YOLO 權重路徑")
    ap.add_argument("--sam", default="sam2_b.pt",
                    help="SAM2 權重 (sam2_t/sam2_b/sam2_l.pt)，會自動下載")
    ap.add_argument("--cam", type=int, default=0, help="相機編號")
    ap.add_argument("--image", default=None, help="直接指定圖片檔（不開相機）")
    ap.add_argument("--dir", default=None, help="跑整個資料夾的圖片，逐張顯示結果")
    ap.add_argument("--conf", type=float, default=0.4, help="YOLO 置信度門檻")
    ap.add_argument("--device", default=None, help="'0' GPU / 'cpu'，預設自動")
    ap.add_argument("--save", default=None, help="結果存檔路徑（可選）")
    args = ap.parse_args()

    if not Path(args.weights).exists():
        print(f"[錯誤] 找不到 YOLO 權重 {args.weights}，請先用 train.py 訓練")
        return

    from ultralytics import YOLO, SAM
    device = pick_device(args.device)
    print(f"[main] device = {device}")
    yolo = YOLO(args.weights)
    sam = SAM(args.sam)

    # 模式一：直接跑單張圖
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"[錯誤] 無法讀取 {args.image}")
            return
        result = segment(frame, yolo, sam, device, args.conf)
        if args.save:
            cv2.imwrite(args.save, result)
            print(f"[main] 已存 {args.save}")
        cv2.imshow("result (YOLO + SAM2)", result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    # 模式二：跑整個資料夾，逐張顯示
    if args.dir:
        src = Path(args.dir)
        if not src.is_dir():
            print(f"[錯誤] 找不到資料夾 {src}")
            return
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        imgs = sorted(p for p in src.iterdir() if p.suffix.lower() in exts)
        if not imgs:
            print(f"[錯誤] {src} 內沒有圖片")
            return
        # 結果存檔目錄：--save 指定則用它，否則存到 <資料夾>_result
        out_dir = Path(args.save) if args.save else src.parent / f"{src.name}_result"
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"[main] 共 {len(imgs)} 張，任意鍵=下一張  q/ESC=中止")
        for i, p in enumerate(imgs, 1):
            frame = cv2.imread(str(p))
            if frame is None:
                print(f"[{i}/{len(imgs)}] 讀取失敗，略過：{p.name}")
                continue
            print(f"[{i}/{len(imgs)}] {p.name}")
            result = segment(frame, yolo, sam, device, args.conf)
            cv2.imwrite(str(out_dir / f"{p.stem}_result.jpg"), result)

            title = f"[{i}/{len(imgs)}] {p.name}  (any key=next, q=quit)"
            cv2.imshow("result (YOLO + SAM2)", result)
            key = cv2.waitKey(0) & 0xFF
            if key in (ord("q"), 27):
                print("[main] 使用者中止")
                break
        cv2.destroyAllWindows()
        print(f"[main] 完成，結果存於 {out_dir.resolve()}")
        return

    # 模式三：開相機拍照
    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"[錯誤] 無法開啟相機 {args.cam}")
        return
    print("空白鍵/s=拍照並分割  q/ESC=離開")

    shot = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[錯誤] 讀取畫面失敗")
            break
        view = frame.copy()
        cv2.putText(view, "SPACE/s = shot+segment   q/ESC = quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("camera (YOLO + SAM2)", view)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key in (ord(" "), ord("s")):
            print("[main] 拍照，執行 YOLO + SAM2 ...")
            result = segment(frame, yolo, sam, device, args.conf)
            if args.save:
                out_path = args.save if shot == 0 else f"{Path(args.save).stem}_{shot}{Path(args.save).suffix}"
                cv2.imwrite(out_path, result)
                print(f"[main] 已存 {out_path}")
            shot += 1
            cv2.imshow("result (YOLO + SAM2)", result)
            cv2.waitKey(0)
            cv2.destroyWindow("result (YOLO + SAM2)")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
