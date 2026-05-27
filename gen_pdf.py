import re, os, subprocess, json, tempfile
from pathlib import Path
import markdown

MD_FILE = Path("/Users/william/Desktop/test/設計文件書_FMD_AI_Screener.md")
PDF_FILE = Path("/Users/william/Desktop/test/設計文件書_FMD_AI_Screener.pdf")
IMG_DIR = Path("/tmp/mermaid_imgs")
os.makedirs(IMG_DIR, exist_ok=True)

content = MD_FILE.read_text(encoding="utf-8")

# Brand colors
BRAND_BG = "#ffffff"
BRAND_DARK = "#000000"
BRAND_PINK = "#000000"
BRAND_BLUE = "#000000"
BRAND_WHITE = "#FFFFFF"

# Step 1: Extract mermaid blocks and replace with placeholders
pattern = re.compile(r'```mermaid\s*\n(.*?)\n```', re.DOTALL)
mermaid_blocks = pattern.findall(content)
print(f"Found {len(mermaid_blocks)} mermaid blocks")

img_tags = []
for i, block in enumerate(mermaid_blocks, 1):
    mmd_path = IMG_DIR / f"diagram_{i}.mmd"
    png_path = IMG_DIR / f"diagram_{i}.png"
    svg_path = IMG_DIR / f"diagram_{i}.svg"
    mmd_path.write_text(block.strip(), encoding="utf-8")

    if "erDiagram" in block:
        # ER diagram: SVG -> scale viewBox 2x -> puppeteer screenshot at 2x pixel density
        subprocess.run(["mmdc", "-i", str(mmd_path), "-o", str(svg_path), "-b", "transparent"],
                       capture_output=True, text=True, timeout=30)
        if svg_path.exists():
            svg = svg_path.read_text(encoding="utf-8")
            # Fix only the root <svg> tag: remove max-width, shrink viewBox 2x for bigger text
            svg_start = svg.index('<svg')
            svg_end = svg.index('>', svg_start)
            root_tag = svg[svg_start:svg_end+1]
            rest = svg[svg_end+1:]
            import re as re2
            # Shrink viewBox 2x so text renders 2x bigger at same viewport
            root_tag = re2.sub(r'viewBox="0 0 (\d+\.?\d*) (\d+\.?\d*)"',
                               lambda m: f'viewBox="0 0 {float(m.group(1))/8} {float(m.group(2))/8}"',
                               root_tag)
            # Remove max-width constraint
            root_tag = re2.sub(r'\s+style="[^"]*"', '', root_tag)
            svg = root_tag + rest
            svg_path.write_text(svg, encoding="utf-8")
            pup_script = f"""
const p=require('/opt/homebrew/lib/node_modules/puppeteer');
(async()=>{{
  const b=await p.launch({{headless:'new',args:['--no-sandbox']}});
  const pg=await b.newPage();
  await pg.setViewport({{width:5000,height:1000,deviceScaleFactor:1}});
  await pg.goto('file://{svg_path}',{{waitUntil:'networkidle0'}});
  await pg.screenshot({{path:'{png_path}'}});
  await b.close();
}})();"""
            sub_result = subprocess.run(["node", "-e", pup_script],
                                        capture_output=True, text=True, timeout=60)
            if png_path.exists():
                img_tags.append(f'<div style="text-align:center;margin:20px 0;"><img src="file://{png_path}" style="max-width:100%;height:auto;border:1px solid #e0e0e0;border-radius:6px;"></div>')
                print(f"  Diagram {i}: OK (2x)")
            else:
                print(f"  Diagram {i}: Puppeteer failed")
        else:
            print(f"  Diagram {i}: SVG failed")
    else:
        cmd = ["mmdc", "-i", str(mmd_path), "-o", str(png_path), "-b", "transparent"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if png_path.exists():
            img_tags.append(f'<div style="text-align:center;margin:20px 0;"><img src="file://{png_path}" style="max-width:100%;height:auto;border:1px solid #e0e0e0;border-radius:6px;"></div>')
            print(f"  Diagram {i}: OK")
        else:
            print(f"  Diagram {i}: FAILED: {result.stderr}")

# Step 2: Replace mermaid blocks with img tags
text_with_imgs = pattern.sub(lambda m: f'\n\n{img_tags.pop(0)}\n\n', content)

# Step 3: Convert markdown to HTML
md = markdown.Markdown(extensions=['tables', 'fenced_code', 'codehilite'])
html_body = md.convert(text_with_imgs)

# Step 4: Build full HTML
html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>設計文件書 FMD_AI_Screener</title>
<style>
  body {{
    font-family: 'Noto Sans CJK TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif;
    color: #111111;
    background: #fff;
    font-size: 13px;
    line-height: 1.7;
    margin: 35px 45px;
  }}
  h1 {{
    color: #111111;
    border-bottom: 3px solid {BRAND_PINK};
    padding-bottom: 8px;
    font-size: 22px;
    margin-top: 0;
  }}
  h2 {{
    color: #111111;
    border-left: 5px solid {BRAND_BLUE};
    padding-left: 10px;
    font-size: 17px;
    margin-top: 32px;
  }}
  h3 {{ color: {BRAND_BLUE}; font-size: 15px; margin-top: 24px; }}
  h4 {{ color: {BRAND_PINK}; font-size: 14px; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 12.5px;
    margin: 14px 0;
  }}
  th {{
    background: {BRAND_BG};
    color: #111111;
    border: 1px solid #b0c8e0;
    padding: 7px 11px;
    font-weight: bold;
    text-align: left;
  }}
  td {{
    border: 1px solid #d0d0d0;
    padding: 6px 10px;
    vertical-align: top;
  }}
  tr:nth-child(even) td {{ background: #f9fbfe; }}
  hr {{ border: none; border-top: 1px solid {BRAND_BG}; margin: 28px 0; }}
  code {{ background: #f3f6fa; padding: 1px 5px; border-radius: 3px; font-size: 11.5px; color: {BRAND_PINK}; }}
  pre {{ background: #f8f9fb; border: 1px solid #dde4ee; border-radius: 6px; padding: 14px; overflow-x: auto; font-size: 11.5px; line-height: 1.5; }}
  pre code {{ background: none; padding: 0; color: inherit; }}
  strong {{ color: {BRAND_PINK}; }}
  em {{ color: {BRAND_BLUE}; }}
  a {{ color: {BRAND_BLUE}; text-decoration: none; }}
  img {{ max-width: 100%; height: auto; }}
  blockquote {{ border-left: 4px solid {BRAND_BLUE}; margin: 14px 0; padding: 4px 14px; color: #444; background: {BRAND_BG}; }}
  ul, ol {{ padding-left: 22px; }}
  li {{ margin: 4px 0; }}
  @page {{ margin: 15mm 14mm; size: A4; }}
  @media print {{ body {{ margin: 20px 30px; }} }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

html_path = Path("/tmp/fmd_doc.html")
html_path.write_text(html, encoding="utf-8")
print(f"HTML: {html_path}")

# Step 5: Puppeteer to PDF (no header/footer)
puppeteer_script = """
const puppeteer = require('/opt/homebrew/lib/node_modules/puppeteer');
const path = require('path');

(async () => {
  const htmlPath = process.argv[2];
  const pdfPath = process.argv[3];

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0' });

  await page.pdf({
    path: pdfPath,
    format: 'A4',
    printBackground: true,
    displayHeaderFooter: false,
    margin: { top: '15mm', bottom: '15mm', left: '14mm', right: '14mm' }
  });

  await browser.close();
  console.log('PDF done');
})();
"""

script_path = Path("/tmp/puppeteer_pdf.js")
script_path.write_text(puppeteer_script, encoding="utf-8")

result = subprocess.run(
    ["node", str(script_path), str(html_path), str(PDF_FILE)],
    capture_output=True, text=True, timeout=120
)
if result.returncode == 0:
    print(f"PDF OK: {PDF_FILE} ({PDF_FILE.stat().st_size} bytes)")
else:
    print(f"Failed: {result.stderr}")
