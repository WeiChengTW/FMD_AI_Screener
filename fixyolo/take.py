"""
拍照收集資料用。開啟相機，即時預覽：
  空白鍵 / s = 拍照存檔
  r         = 框選 / 重新框選裁切範圍（再按一次可更新）
  q / ESC   = 離開

存檔到 --out 目錄，檔名自動從現有最大編號往後累加（不會覆蓋）。

用法：
  python take.py
  python take.py --out captures --cam 0 --prefix img
"""

import argparse
import time
from pathlib import Path

import cv2


def next_index(out_dir: Path, prefix: str) -> int:
    """找出目前資料夾內同 prefix 的最大編號，回傳下一個編號。"""
    idx = 0
    for p in out_dir.glob(f"{prefix}_*.jpg"):
        try:
            n = int(p.stem.split("_")[-1])
            idx = max(idx, n)
        except ValueError:
            continue
    return idx + 1


def select_crop(cap):
    """抓一張畫面讓使用者用滑鼠框裁切範圍。回傳 (x,y,w,h) 或 None。"""
    ok, frame = cap.read()
    if not ok:
        print("[錯誤] 取得畫面失敗，無法框選")
        return None
    win = "select crop (drag box, ENTER=OK, c=cancel)"
    roi = cv2.selectROI(win, frame, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow(win)
    x, y, w, h = (int(v) for v in roi)
    if w == 0 or h == 0:  # 直接按 ENTER 沒框 -> 取消
        return None
    return (x, y, w, h)


def main():
    ap = argparse.ArgumentParser(description="開相機拍照收集資料")
    ap.add_argument("--out", default="captures", help="照片輸出目錄")
    ap.add_argument("--cam", type=int, default=0, help="相機編號")
    ap.add_argument("--prefix", default="img", help="檔名前綴")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--crop", default="n", choices=["y", "n"],
                    help="y = 開始前先框裁切範圍，之後每張都裁成該範圍")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Windows 用 CAP_DSHOW 開啟較快且穩定
    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        print(f"[錯誤] 無法開啟相機 {args.cam}")
        return

    # --crop y：開始前先框一次裁切範圍
    crop_roi = None  # (x, y, w, h)
    if args.crop == "y":
        crop_roi = select_crop(cap)
        if crop_roi is None:
            print("[提示] 未框選範圍，改用整張畫面")
        else:
            print(f"[提示] 裁切範圍 x={crop_roi[0]} y={crop_roi[1]} "
                  f"w={crop_roi[2]} h={crop_roi[3]}")

    idx = next_index(out_dir, args.prefix)
    count = 0
    print("空白鍵/s=拍照  r=框選裁切範圍  q/ESC=離開")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[錯誤] 讀取畫面失敗")
            break

        # 疊上提示文字（只顯示在預覽，不影響存檔畫面）
        view = frame.copy()
        if crop_roi is not None:
            x, y, w, h = crop_roi
            cv2.rectangle(view, (x, y), (x + w, y + h), (0, 255, 0), 2)  # 顯示裁切框
        cv2.putText(view, f"saved: {count}   next: {args.prefix}_{idx:04d}.jpg",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(view, "SPACE/s = shot   r = crop   q/ESC = quit",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("take (collect photos)", view)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):  # q 或 ESC
            break
        if key == ord("r"):  # r = 框選 / 重新框選裁切範圍
            new_roi = select_crop(cap)
            if new_roi is None:
                crop_roi = None
                print("[提示] 取消裁切，改用整張畫面")
            else:
                crop_roi = new_roi
                print(f"[提示] 裁切範圍 x={crop_roi[0]} y={crop_roi[1]} "
                      f"w={crop_roi[2]} h={crop_roi[3]}")
            continue
        if key in (ord(" "), ord("s")):
            save_frame = frame
            if crop_roi is not None:
                x, y, w, h = crop_roi
                save_frame = frame[y:y + h, x:x + w]  # 裁切成指定範圍
            fname = out_dir / f"{args.prefix}_{idx:04d}.jpg"
            cv2.imwrite(str(fname), save_frame)  # 存乾淨的畫面（已裁切）
            print(f"已存 {fname}")
            idx += 1
            count += 1
            # 拍照閃一下白框回饋
            flash = frame.copy()
            cv2.rectangle(flash, (0, 0), (flash.shape[1] - 1, flash.shape[0] - 1),
                          (255, 255, 255), 20)
            cv2.imshow("take (collect photos)", flash)
            cv2.waitKey(60)

    cap.release()
    cv2.destroyAllWindows()
    print(f"結束，共拍了 {count} 張，存於 {out_dir.resolve()}")


if __name__ == "__main__":
    main()
