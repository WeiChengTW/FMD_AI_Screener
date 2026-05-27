#!/usr/bin/env python3
"""
PNG → draw.io 匯出工具
將 imgs/diagram_*.png 打包成一個 .drawio 檔案，每張圖一頁
"""

import base64, struct
from pathlib import Path

IMG_DIR = Path("imgs")

DIAGRAM_NAMES = [
    "2.2 系統範圍",
    "2.3 三層式架構",
    "3.1.2 部署架構",
    "3.2.1 類別圖",
    "3.4.1 使用案例圖",
    "3.4.2 循序圖",
    "3.4.3 活動圖",
    "附錄D ER圖",
]

PNG_FILES = [
    "diagram_1.png",
    "diagram_2.png",
    "diagram_3.png",
    "diagram_4.png",
    "diagram_5.png",
    "diagram_6.png",
    "diagram_7.png",
    "diagram_8a.png",
]


def get_png_size(path: Path):
    """從 PNG binary header 讀取寬高"""
    with open(path, "rb") as f:
        f.read(8)   # PNG signature
        f.read(4)   # IHDR chunk length
        f.read(4)   # "IHDR"
        w = struct.unpack(">I", f.read(4))[0]
        h = struct.unpack(">I", f.read(4))[0]
    return w, h


def make_drawio(entries):
    """entries: list of (name, b64_data, width, height)"""
    pages = ""
    for i, (name, b64, w, h) in enumerate(entries, 1):
        # 縮放至最大 1600px 寬，保持比例
        max_w = 1600
        if w > max_w:
            scale = max_w / w
            dw, dh = int(w * scale), int(h * scale)
        else:
            dw, dh = w, h

        pages += f"""  <diagram id="p{i}" name="{name}">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1654" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="" style="shape=image;html=1;verticalLabelPosition=bottom;labelBackgroundColor=default;verticalAlign=top;align=center;strokeColor=none;fillColor=none;aspect=fixed;image=data:image/png;base64,{b64}" vertex="1" parent="1">
          <mxGeometry x="27" y="27" width="{dw}" height="{dh}" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
"""
    return f'<mxfile host="Electron" version="21.0.0">\n{pages}</mxfile>'


def main():
    entries = []

    for fname, name in zip(PNG_FILES, DIAGRAM_NAMES):
        path = IMG_DIR / fname
        if not path.exists():
            print(f"  [跳過] {fname} 不存在")
            continue

        w, h = get_png_size(path)
        b64 = base64.b64encode(path.read_bytes()).decode()
        size_kb = path.stat().st_size // 1024
        print(f"  {fname}: {w}x{h}px ({size_kb} KB)")
        entries.append((name, b64, w, h))

    if not entries:
        print("找不到任何 PNG 圖片")
        return

    out = Path("設計文件書_FMD_AI_Screener.drawio")
    xml = make_drawio(entries)
    out.write_text(xml, encoding="utf-8")
    print(f"\n匯出完成: {out} ({out.stat().st_size // 1024} KB)")
    print(f"共 {len(entries)} 頁，用 draw.io / diagrams.net 開啟即可編輯")


if __name__ == "__main__":
    main()
