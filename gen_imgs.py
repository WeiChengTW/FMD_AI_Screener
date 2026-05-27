import re, os, subprocess
from pathlib import Path

MD_FILE = Path("/Users/william/Desktop/test/設計文件書_FMD_AI_Screener.md")
IMG_DIR = Path("/Users/william/Desktop/test/imgs")
IMG_DIR.mkdir(exist_ok=True)

content = MD_FILE.read_text(encoding="utf-8")

pattern = re.compile(r'```mermaid\s*\n(.*?)\n```', re.DOTALL)
mermaid_blocks = pattern.findall(content)
print(f"Found {len(mermaid_blocks)} mermaid blocks")

for i, block in enumerate(mermaid_blocks, 1):
    mmd_path = IMG_DIR / f"diagram_{i}.mmd"
    png_path = IMG_DIR / f"diagram_{i}.png"
    svg_path = IMG_DIR / f"diagram_{i}.svg"
    mmd_path.write_text(block.strip(), encoding="utf-8")

    if "erDiagram" in block:
        # ER diagram: mmdc -> SVG -> shrink viewBox 8x -> puppeteer screenshot
        subprocess.run(["mmdc", "-i", str(mmd_path), "-o", str(svg_path), "-b", "transparent"],
                       capture_output=True, text=True, timeout=30)
        if svg_path.exists():
            svg = svg_path.read_text(encoding="utf-8")
            svg_start = svg.index('<svg')
            svg_end = svg.index('>', svg_start)
            root_tag = svg[svg_start:svg_end+1]
            rest = svg[svg_end+1:]
            import re as re2
            root_tag = re2.sub(r'viewBox="0 0 (\d+\.?\d*) (\d+\.?\d*)"',
                               lambda m: f'viewBox="0 0 {float(m.group(1))/8} {float(m.group(2))/8}"',
                               root_tag)
            root_tag = re2.sub(r'\s+style="[^"]*"', '', root_tag)
            svg = root_tag + rest
            svg_path.write_text(svg, encoding="utf-8")
            pup_script = f"""
const p=require('/opt/homebrew/lib/node_modules/puppeteer');
(async()=>{{
  const b=await p.launch({{headless:'new',args:['--no-sandbox']}});
  const pg=await b.newPage();
  await pg.setViewport({{width:20000,height:4000,deviceScaleFactor:1}});
  await pg.goto('file://{svg_path}',{{waitUntil:'networkidle0'}});
  await pg.screenshot({{path:'{png_path}'}});
  await b.close();
}})();"""
            subprocess.run(["node", "-e", pup_script], capture_output=True, text=True, timeout=60)
            if png_path.exists():
                print(f"  Diagram {i}: OK (erDiagram, 5000x1000)")
            else:
                print(f"  Diagram {i}: Puppeteer failed")
        else:
            print(f"  Diagram {i}: SVG failed")
    else:
        # Regular diagram: mmdc -> PNG directly
        cmd = ["mmdc", "-i", str(mmd_path), "-o", str(png_path), "-b", "transparent"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if png_path.exists():
            print(f"  Diagram {i}: OK")
        else:
            print(f"  Diagram {i}: FAILED: {result.stderr}")

print(f"\nImages saved to: {IMG_DIR}")
for p in sorted(IMG_DIR.glob("diagram_*.png")):
    print(f"  {p.name} ({p.stat().st_size // 1024} KB)")
