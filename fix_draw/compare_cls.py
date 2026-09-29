"""比較兩顆分類模型在 class_data_split/val 上的準確率與混淆矩陣。"""
import glob
import os
import numpy as np
from ultralytics import YOLO

VAL_DIR = "class_data_split/val"
MODELS = {
    "yolov8n-cls (現用)": "runs/classify/train/weights/best.pt",
    "yolov8s-cls (新)":   "runs/classify/cls_s/weights/best.pt",
}
CLASSES = sorted(d for d in os.listdir(VAL_DIR)
                 if os.path.isdir(os.path.join(VAL_DIR, d)))
IDX = {c: i for i, c in enumerate(CLASSES)}

# 收集 val 影像與真值
items = []
for c in CLASSES:
    for p in glob.glob(os.path.join(VAL_DIR, c, "*")):
        items.append((p, IDX[c]))
print(f"val 影像 {len(items)} 張，類別 {CLASSES}\n")

for name, w in MODELS.items():
    m = YOLO(w)
    n = sum(p.numel() for p in m.model.parameters())
    cm = np.zeros((len(CLASSES), len(CLASSES)), dtype=int)
    for p, t in items:
        r = m.predict(source=p, imgsz=224, device=0, verbose=False)[0]
        cm[t, int(r.probs.top1)] += 1
    acc = cm.trace() / cm.sum()
    print("=" * 52)
    print(f"{name}  |  params={n:,}  |  val acc={acc*100:.2f}%")
    print("-" * 52)
    print("        " + "".join(f"{c[:5]:>7}" for c in CLASSES) + "   (pred)")
    for i, c in enumerate(CLASSES):
        per = cm[i].sum()
        recall = cm[i, i] / per if per else 0
        print(f"{c[:6]:>6}  " + "".join(f"{v:>7}" for v in cm[i])
              + f"   recall={recall*100:5.1f}%")
    print()
