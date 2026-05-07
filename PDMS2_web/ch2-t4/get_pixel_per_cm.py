# get_pixel_per_cm.py  —— 單線版：只裁切，不計算比例；比例改讀 .env
import cv2
import numpy as np
import glob
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"

ORIG_FOLDER = os.path.join("PDMS2_web", "ch2-t4", "images")  # 原始圖片
CROP_FOLDER = os.path.join("PDMS2_web", "ch2-t4", "new")  # 裁切輸出
os.makedirs(CROP_FOLDER, exist_ok=True)


def _read_env_float(key, default):
    if not ENV_PATH.exists():
        return default
    try:
        for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in raw_line:
                continue
            current_key, value = raw_line.split("=", 1)
            if current_key.strip() == key:
                parsed = float(value.strip())
                return parsed if parsed > 0 else default
    except Exception:
        return default
    return default


def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    rect[0] = pts[np.argmin(s)]  # tl
    rect[2] = pts[np.argmax(s)]  # br
    rect[1] = pts[np.argmin(diff)]  # tr
    rect[3] = pts[np.argmax(diff)]  # bl
    return rect


def detect_quad(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    if len(approx) == 4:
        return approx.reshape(4, 2).astype(np.float32)
    # 後援：最小外接矩形
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    return box.astype(np.float32)


def warp_a4(image, quad):
    quad = order_points(quad)
    (tl, tr, br, bl) = quad
    w1 = np.linalg.norm(tr - tl)
    w2 = np.linalg.norm(br - bl)
    h1 = np.linalg.norm(bl - tl)
    h2 = np.linalg.norm(br - tr)
    width_px = int(round(max(w1, w2)))
    height_px = int(round(max(h1, h2)))
    dst = np.array(
        [[0, 0], [width_px - 1, 0], [width_px - 1, height_px - 1], [0, height_px - 1]],
        dtype="float32",
    )
    M = cv2.getPerspectiveTransform(quad, dst)
    warped = cv2.warpPerspective(image, M, (width_px, height_px))
    return warped


def crop_only(image_path, output_path):
    """只裁切白紙，輸出到 output_path；回傳裁切影像 ndarray。"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"圖片讀取失敗：{image_path}")

    quad = detect_quad(img)
    if quad is not None and len(quad) == 4:
        warped = warp_a4(img, quad)
    else:
        # 後援：偵測不到四邊形就整張輸出，保證不報錯
        warped = img.copy()

    ok = cv2.imwrite(output_path, warped)
    if not ok:
        raise IOError(f"寫檔失敗：{output_path}")
    return warped


def load_pixel_per_cm(default=1.0):
    """從 .env 讀比例：PDMS2_PX2CM。"""
    ppcm = _read_env_float("PDMS2_PX2CM", default)
    if ppcm <= 0:
        raise ValueError(".env 內的 PDMS2_PX2CM 非正值")
    return ppcm


if __name__ == "__main__":
    img_num = 1  # ← 改成你要裁切的編號
    in_path = os.path.join(ORIG_FOLDER, f"{img_num}.jpg")
    out_path = os.path.join(CROP_FOLDER, f"new{img_num}.jpg")
    os.makedirs(CROP_FOLDER, exist_ok=True)

    if not os.path.exists(in_path):
        raise FileNotFoundError(f"找不到圖片：{os.path.abspath(in_path)}")

    warped = crop_only(in_path, out_path)
    ppcm = load_pixel_per_cm()

    print(f"已裁切：{in_path} → {out_path}  (size={warped.shape[1]}x{warped.shape[0]})")
    print(f"轉換比例 pixel_per_cm = {ppcm:.6f}（來自 .env）")
