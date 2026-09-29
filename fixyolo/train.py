"""
訓練 YOLOv8 segmentation 模型。

流程：
  1. 先對 Roboflow 資料集做曝光/對比增強（見 augment.py），
     每張原圖 -> 原圖 + 6 張增強（可調），產生一份 dataset_aug。
  2. 用增強後的資料集訓練 YOLOv8-seg。

用法：
  python train.py --dataset "path/to/roboflow_dataset"
  python train.py --dataset "..." --epochs 150 --model yolov8s-seg.pt --no-augment

輸出的最佳權重在 runs/segment/<name>/weights/best.pt，
訓練結束後會複製一份到本資料夾的 best.pt 供 main.py 使用。
"""

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

from augment import build_augmented_dataset


def main():
    ap = argparse.ArgumentParser(description="訓練 YOLOv8-seg（含曝光/對比增強）")
    ap.add_argument("--dataset", required=True, help="Roboflow 資料集根目錄")
    ap.add_argument("--aug-out", default="dataset_aug", help="增強後資料集輸出目錄")
    ap.add_argument("--no-augment", action="store_true", help="跳過增強，直接用原資料集")
    ap.add_argument("--model", default="yolov8n-seg.pt",
                    help="基礎模型 (yolov8n/s/m/l-seg.pt)")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8)  # RTX 4070 8GB 建議 8，OOM 再降 4
    ap.add_argument("--device", default=None, help="'0' 用 GPU，'cpu' 用 CPU，預設自動")
    ap.add_argument("--name", default="fmd_seg", help="訓練輸出資料夾名稱")
    args = ap.parse_args()

    # 1. 資料增強 -> 取得要餵給 YOLO 的 data.yaml
    if args.no_augment:
        yaml_candidates = list(Path(args.dataset).glob("*.yaml"))
        if not yaml_candidates:
            raise FileNotFoundError(f"{args.dataset} 內找不到 data.yaml")
        data_yaml = yaml_candidates[0]
        print(f"[train] 略過增強，使用原始 {data_yaml}")
    else:
        print("[train] 開始曝光/對比增強 ...")
        data_yaml = build_augmented_dataset(args.dataset, args.aug_out)

    # 2. 訓練
    #    這裡關閉 ultralytics 內建的幾何增強不必要地過強的部分，
    #    但保留一些預設，光度增強我們已在前處理做過。
    device = args.device if args.device is not None else ""  # "" 讓 ultralytics 自動選
    model = YOLO(args.model)
    results = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        name=args.name,
        patience=30,
    )

    # 3. 把 best.pt 複製到本資料夾方便 main.py 使用
    save_dir = Path(results.save_dir) if hasattr(results, "save_dir") else None
    if save_dir is None:
        save_dir = Path("runs/segment") / args.name
    best = save_dir / "weights" / "best.pt"
    if best.exists():
        shutil.copyfile(best, Path(__file__).parent / "best.pt")
        print(f"[train] 訓練完成，最佳權重已複製到 {Path(__file__).parent / 'best.pt'}")
    else:
        print(f"[train] 訓練完成，但找不到 {best}，請至 runs/ 查看")


if __name__ == "__main__":
    main()
