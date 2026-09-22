"""在一張 A4 白紙上產生多個不同 ID 的 ArUco 標記（300 DPI，實際尺寸可列印）。"""
import argparse

import cv2
import numpy as np
from PIL import Image

DPI = 300
A4_CM = (21.0, 29.7)


def cm2px(cm):
    return int(round(cm / 2.54 * DPI))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--size-cm", type=float, default=2.8, help="標記黑框邊長 (cm)")
    p.add_argument("--cols", type=int, default=4)
    p.add_argument("--rows", type=int, default=6)
    p.add_argument("--start-id", type=int, default=0)
    p.add_argument("--out", default="aruco_a4")
    args = p.parse_args()

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    page_w, page_h = cm2px(A4_CM[0]), cm2px(A4_CM[1])
    page = np.full((page_h, page_w), 255, np.uint8)

    m = cm2px(args.size_cm)
    cell_w = page_w // args.cols
    cell_h = (page_h - cm2px(1.2)) // args.rows  # 底部保留頁尾空間

    for r in range(args.rows):
        for c in range(args.cols):
            mid = args.start_id + r * args.cols + c
            if mid >= 50:
                break
            marker = cv2.aruco.generateImageMarker(aruco_dict, mid, m)
            x = c * cell_w + (cell_w - m) // 2
            y = r * cell_h + (cell_h - m) // 2 - cm2px(0.3)
            page[y:y + m, x:x + m] = marker
            label = f"ID {mid}"
            (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
            cv2.putText(page, label, (x + (m - tw) // 2, y + m + cm2px(0.6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 2, cv2.LINE_AA)

    footer = f"DICT_4X4_50  marker {args.size_cm} cm  (print at 100% / actual size)"
    cv2.putText(page, footer, (cm2px(1.0), page_h - cm2px(0.5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2, cv2.LINE_AA)

    img = Image.fromarray(page)
    img.save(f"{args.out}.png", dpi=(DPI, DPI))
    img.save(f"{args.out}.pdf", resolution=DPI)
    print(f"已輸出 {args.out}.png / {args.out}.pdf")


if __name__ == "__main__":
    main()
