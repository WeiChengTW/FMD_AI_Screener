"""
訓練 ch2 手繪圖 4 類分類器（circle / cross / other / square），
取代舊的三個二元 .h5（circle_detect / square / cross_final）。

輸入契約（與現有 ImageClassifier.predict 相容）：
  - 圖片以 RGB 3 通道載入，尺寸 224x224
  - 推論端會先做 /255（值域 [0,1]），本模型內部再 Rescaling 到 [-1,1] 餵 MobileNetV2
  - 輸出 4 類 softmax，class_names 依字母排序：['circle','cross','other','square']

用法：
  python train_classifier.py
  python train_classifier.py --data class_data --epochs 30 --ft-epochs 15 --batch 32

輸出：
  shape_cls.keras           最佳模型（依 val_accuracy）
  shape_cls_labels.txt      類別順序（給推論端對照）
  shape_cls_confusion.png   驗證集混淆矩陣
"""

import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models


def build_datasets(data_dir, img_size, batch, seed):
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="training",
        seed=seed,
        image_size=img_size,
        batch_size=batch,
        color_mode="rgb",          # 灰階來源會被複製成 3 通道，與推論一致
        label_mode="categorical",
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="validation",
        seed=seed,
        image_size=img_size,
        batch_size=batch,
        color_mode="rgb",
        label_mode="categorical",
        shuffle=False,
    )
    class_names = train_ds.class_names  # 字母排序：circle, cross, other, square

    # 值域 [0,1]，對齊推論端的 /255
    norm = layers.Rescaling(1.0 / 255)
    train_ds = train_ds.map(lambda x, y: (norm(x), y))
    val_ds = val_ds.map(lambda x, y: (norm(x), y))

    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().prefetch(AUTOTUNE)
    val_ds = val_ds.cache().prefetch(AUTOTUNE)
    return train_ds, val_ds, class_names


def build_model(num_classes, img_size):
    # 輕度資料增強（手繪形狀：翻轉/旋轉/縮放/平移都安全）
    aug = models.Sequential([
        layers.RandomFlip("horizontal_and_vertical"),
        layers.RandomRotation(0.15),
        layers.RandomZoom(0.15),
        layers.RandomTranslation(0.1, 0.1),
    ], name="augment")

    base = tf.keras.applications.MobileNetV2(
        input_shape=(*img_size, 3),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    inputs = layers.Input(shape=(*img_size, 3))          # 期望輸入值域 [0,1]
    x = aug(inputs)
    x = layers.Rescaling(2.0, offset=-1.0)(x)            # [0,1] -> [-1,1] 給 MobileNetV2
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    model = models.Model(inputs, outputs)
    return model, base


def plot_confusion(model, val_ds, class_names, out_path):
    y_true, y_pred = [], []
    for xb, yb in val_ds:
        p = model.predict(xb, verbose=0)
        y_true.extend(np.argmax(yb.numpy(), axis=1))
        y_pred.extend(np.argmax(p, axis=1))
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    n = len(class_names)
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    acc = (y_true == y_pred).mean()
    print(f"[eval] val accuracy = {acc:.4f}")
    print("[eval] confusion matrix (row=true, col=pred):")
    print("        " + "  ".join(f"{c[:6]:>6}" for c in class_names))
    for i, c in enumerate(class_names):
        print(f"{c[:6]:>6}  " + "  ".join(f"{v:>6}" for v in cm[i]))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(n)); ax.set_xticklabels(class_names, rotation=45, ha="right")
        ax.set_yticks(range(n)); ax.set_yticklabels(class_names)
        ax.set_xlabel("pred"); ax.set_ylabel("true")
        ax.set_title(f"val acc = {acc:.3f}")
        for i in range(n):
            for j in range(n):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        fig.colorbar(im); fig.tight_layout(); fig.savefig(out_path, dpi=120)
        print(f"[eval] 混淆矩陣已存到 {out_path}")
    except Exception as e:
        print(f"[eval] 略過混淆矩陣圖：{e}")


def main():
    ap = argparse.ArgumentParser(description="ch2 手繪圖 4 類分類器訓練")
    ap.add_argument("--data", default="class_data", help="分類資料夾根目錄（子資料夾=類別）")
    ap.add_argument("--epochs", type=int, default=30, help="第一階段（凍結 backbone）epoch")
    ap.add_argument("--ft-epochs", type=int, default=15, help="第二階段（微調）epoch")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="shape_cls.keras")
    args = ap.parse_args()

    img_size = (args.imgsz, args.imgsz)
    train_ds, val_ds, class_names = build_datasets(args.data, img_size, args.batch, args.seed)
    print(f"[data] classes = {class_names}")

    model, base = build_model(len(class_names), img_size)

    ckpt = tf.keras.callbacks.ModelCheckpoint(
        args.out, monitor="val_accuracy", save_best_only=True, mode="max", verbose=1)
    early = tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy", patience=10, restore_best_weights=True, mode="max")

    # 階段一：只訓練分類頭
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="categorical_crossentropy", metrics=["accuracy"])
    print("\n[stage 1] 凍結 backbone，訓練分類頭 ...")
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs,
              callbacks=[ckpt, early])

    # 階段二：解凍 backbone 後段微調
    base.trainable = True
    for layer in base.layers[:-40]:   # 只放開最後 ~40 層
        layer.trainable = False
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5),
                  loss="categorical_crossentropy", metrics=["accuracy"])
    print("\n[stage 2] 微調 backbone 後段 ...")
    model.fit(train_ds, validation_data=val_ds, epochs=args.ft_epochs,
              callbacks=[ckpt, early])

    # 載回最佳權重評估
    best = tf.keras.models.load_model(args.out)
    Path("shape_cls_labels.txt").write_text("\n".join(class_names), encoding="utf-8")
    print(f"\n[done] 最佳模型 -> {args.out}，類別順序 -> shape_cls_labels.txt")
    plot_confusion(best, val_ds, class_names, "shape_cls_confusion.png")


if __name__ == "__main__":
    main()
