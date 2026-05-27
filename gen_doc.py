#!/usr/bin/env python3
"""
FMD_AI_Screener 文件產生器
用法: python3 gen_doc.py [input.md] [output.docx]

流程:
  1. 讀取 markdown（含 mermaid 圖表）
  2. 將 mermaid 區塊 render 成 PNG（使用 mermaid-cli）
  3. 用 markdown 圖片語法取代 mermaid 區塊
  4. pandoc 轉 Word
"""

import re, subprocess, sys
from pathlib import Path

# ====== 設定 ======
MMDC = "mmdc"  # mermaid-cli 指令
IMG_DIR = Path("imgs")  # 圖片輸出資料夾

BRAND_BG = "#E2F2FA"
BRAND_DARK = "#0B2F50"
BRAND_BLUE = "#15A9E0"
BRAND_PINK = "#EF427B"

MMDC_OPTS = ["-b", "transparent"]


def extract_mermaid_blocks(content: str):
    """取出所有 ```mermaid ... ``` 區塊"""
    pattern = re.compile(r'```mermaid\s*\n(.*?)\n```', re.DOTALL)
    return pattern.findall(content)


def mmdc_render(mmd_path: Path, out_path: Path, block: str, index: int):
    """用 mmdc 將 mermaid 區塊 render 成 PNG"""
    is_er = "erDiagram" in block

    if is_er:
        # ER 圖表用大寬度 + scale 2（字夠大）
        cmd = [MMDC, "-i", str(mmd_path), "-o", str(out_path),
               "-b", "transparent", "-w", "20000", "-s", "2"]
    else:
        # 一般圖表預設 2000px 寬
        cmd = [MMDC, "-i", str(mmd_path), "-o", str(out_path),
               "-b", "transparent", "-w", "2000"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        size = out_path.stat().st_size // 1024
        dims = subprocess.run(["file", str(out_path)],
                             capture_output=True, text=True)
        print(f"  [{index}] OK ({size} KB) - {out_path.name}")
        return True
    else:
        print(f"  [{index}] FAILED: {result.stderr[:100]}")
        return False


def gen_doc(md_file: str | Path, out_docx: str | Path = None):
    """
    主要函式：讀 markdown → render 圖表 → 取代 → 轉 Word

    Args:
        md_file:  輸入 markdown 檔路徑
        out_docx:  輸出 Word 檔路徑（預設與 md 同名）
    """
    md_file = Path(md_file)
    IMG_DIR.mkdir(exist_ok=True)

    # 讀取 markdown
    content = md_file.read_text(encoding="utf-8")
    blocks = extract_mermaid_blocks(content)

    if not blocks:
        print("找不到 mermaid 區塊，直接轉 Word")
    else:
        print(f"找到 {len(blocks)} 個 mermaid 區塊")

    # 個別 render
    new_content = content
    for i, block in enumerate(blocks, 1):
        mmd_path = IMG_DIR / f"diagram_{i}.mmd"
        png_path = IMG_DIR / f"diagram_{i}.png"

        mmd_path.write_text(block.strip(), encoding="utf-8")
        ok = mmdc_render(mmd_path, png_path, block, i)

        # 取代 mermaid 區塊為 markdown 圖片語法
        # 找這個 block 在 new_content 中的位置
        pattern = re.compile(r'```mermaid\s*\n' + re.escape(block) + r'\n```', re.DOTALL)
        caption = block.split('\n')[0].strip()[:30] if block.strip() else f"diagram_{i}"
        img_md = f"\n![{caption}]({png_path})\n"
        new_content, n = pattern.subn(img_md, new_content, count=1)

    # 輸出含圖片的 markdown
    md_with_imgs = md_file.parent / f"{md_file.stem}_with_imgs.md"
    md_with_imgs.write_text(new_content, encoding="utf-8")
    print(f"\n含圖片 markdown: {md_with_imgs}")

    # 轉 Word
    if out_docx is None:
        out_docx = md_file.parent / f"{md_file.stem}.docx"
    out_docx = Path(out_docx)

    result = subprocess.run(
        ["pandoc", str(md_with_imgs), "-o", str(out_docx)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        size = out_docx.stat().st_size // 1024
        print(f"Word: {out_docx} ({size} KB)")
    else:
        print(f"pandoc 失敗: {result.stderr}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 0:
        # 預設：找目前目錄下第一個 .md 檔
        md_files = list(Path(".").glob("*.md"))
        if not md_files:
            print("找不到 .md 檔")
            sys.exit(1)
        md_file = md_files[0]
        out_docx = None
    elif len(args) == 1:
        md_file = args[0]
        out_docx = None
    elif len(args) == 2:
        md_file, out_docx = args
    else:
        print("用法: python3 gen_doc.py [input.md] [output.docx]")
        sys.exit(1)

    print(f"輸入: {md_file}")
    if out_docx:
        print(f"輸出: {out_docx}")
    print()
    gen_doc(md_file, out_docx)
