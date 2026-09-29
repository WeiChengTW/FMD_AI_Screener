# YOLOv8 + SAM2 分割訓練 / 測試

## 安裝
```bash
# GPU 使用者建議先照 CUDA 版本裝 torch：https://pytorch.org/get-started/locally/
pip install -r requirements.txt
```

## 檔案
| 檔案 | 用途 |
|------|------|
| `take.py` | 開相機拍照收集資料（空白鍵拍、q 離開） |
| `augment.py` | 曝光/對比增強：每張圖 → 原圖 + 6 張（可調），標註自動沿用 |
| `train.py` | 先增強再訓練 YOLOv8-seg，結束後輸出 `best.pt` |
| `main.py` | 開相機拍照 → YOLO 偵測 → SAM2 依框精細分割並顯示 |

## 流程

### 1. （可選）收集照片
```bash
python take.py --out captures
```
把照片丟到 Roboflow 標註、匯出 **YOLOv8 / segmentation** 格式。

### 2. 訓練（含曝光/對比增強）
```bash
python train.py --dataset "path/to/roboflow_dataset"
```
- 會先產生一份 `dataset_aug`（train 每張變 7 張：原圖 + bright/dark/high_contrast/low_contrast/clahe/bright_contrast）。
- valid/test 不增強。
- 增強種類可在 `augment.py` 的 `VARIATIONS` 增減。
- 常用參數：`--epochs 150 --model yolov8s-seg.pt --batch 16 --device 0`
- 只想用原資料集不增強：加 `--no-augment`
- 完成後 `best.pt` 會複製到本資料夾。

### 3. 測試 / 實拍分割
```bash
python main.py                    # 相機模式，空白鍵拍照分割
python main.py --image test.jpg   # 單張圖模式
```
首次會自動下載 `sam2_b.pt`。沒有 GPU 可加 `--device cpu`。

## 說明
- 曝光/對比屬「光度變換」，不改變物件幾何位置，所以 segmentation polygon 標註完全有效，增強圖直接沿用同一 `.txt`。
- `main.py` 用 YOLO 的 bbox 當 SAM2 的提示（prompt），取得比 YOLO-seg 更精細的邊界。
