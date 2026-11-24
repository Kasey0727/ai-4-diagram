#!/usr/bin/env python3
"""Render native .drawio XML with the official diagrams.net viewer in headless Chromium."""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


VIEWER_URL = "https://viewer.diagrams.net/js/viewer-static.min.js"
XTEAM_CHROMIUM = "/opt/ms-playwright/chromium-1234/chrome-linux64/chrome"
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
RESULT_PATTERN = re.compile(r'<pre id="render-result">([A-Za-z0-9+/=]+)</pre>')


def resolve_chromium(explicit: str | None = None) -> str | None:
    candidates = [explicit, os.environ.get("DRAWIO_CHROMIUM")]
    candidates += [shutil.which(name) for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")]
    candidates += [XTEAM_CHROMIUM, MAC_CHROME]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
    return None


def chrome_args(chromium: str, profile: Path) -> list[str]:
    return [chromium, "--headless=new", "--no-first-run", "--no-default-browser-check",
            "--disable-extensions", "--disable-gpu", "--disable-dev-shm-usage",
            f"--user-data-dir={profile}", "--no-sandbox"]


def viewer_html(xml: str) -> str:
    payload = json.dumps({"xml": xml, "nav": False, "resize": False,
                          "toolbar": "", "border": 0, "lightbox": False},
                         ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html><html><head><meta charset="utf-8"></head><body>
<div class="mxgraph" data-mxgraph="{html.escape(payload, quote=True)}"></div>
<script src="{VIEWER_URL}"></script>
<script>
(() => {{
  let previous = '', stable = 0;
  const poll = setInterval(() => {{
    const svg = document.querySelector('.mxgraph svg');
    let value = '';
    if (svg && svg.querySelector('g')) {{
      const copy = svg.cloneNode(true);
      const box = svg.getBoundingClientRect();
      if (box.width > 0 && box.height > 0) {{
        copy.setAttribute('width', String(Math.ceil(box.width)));
        copy.setAttribute('height', String(Math.ceil(box.height)));
        copy.setAttribute('viewBox', `0 0 ${{Math.ceil(box.width)}} ${{Math.ceil(box.height)}}`);
        copy.setAttribute('style', 'background:#FFFFFF;color-scheme:light');
        value = new XMLSerializer().serializeToString(copy);
      }}
    }}
    if (value && value === previous) stable++; else stable = 0;
    previous = value;
    if (stable >= 3) {{
      clearInterval(poll);
      const bytes = new TextEncoder().encode(value);
      let binary = '';
      for (let i = 0; i < bytes.length; i += 8192)
        binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      const result = document.createElement('pre');
      result.id = 'render-result'; result.textContent = btoa(binary);
      document.body.appendChild(result);
    }}
  }}, 150);
}})();
</script></body></html>"""


def svg_size(svg: bytes) -> tuple[float, float]:
    root = ET.fromstring(svg)
    view_box = root.get("viewBox", "").replace(",", " ").split()
    if len(view_box) == 4:
        width, height = float(view_box[2]), float(view_box[3])
    else:
        width = float(root.get("width", "0").removesuffix("px"))
        height = float(root.get("height", "0").removesuffix("px"))
    if not (width > 0 and height > 0 and math.isfinite(width) and math.isfinite(height)):
        raise RuntimeError("Chromium 导出的 SVG 没有有效尺寸")
    return width, height


def render(drawio: Path, svg: Path, chromium: str | None = None,
           png: Path | None = None, png_width: int = 2000) -> None:
    from preview_files import validate_svg, validate_xml

    browser = resolve_chromium(chromium)
    if not browser:
        raise RuntimeError("未找到 Chromium；可设置 DRAWIO_CHROMIUM 或传 --chromium")
    xml_bytes = drawio.read_bytes()
    validate_xml(xml_bytes)
    if png is not None and png_width < 1:
        raise ValueError("PNG 宽度必须为正数")
    with tempfile.TemporaryDirectory(prefix="text2drawio-render-") as temporary:
        work = Path(temporary)
        source = work / "viewer.html"
        source.write_text(viewer_html(xml_bytes.decode("utf-8-sig")), encoding="utf-8")
        command = chrome_args(browser, work / "profile") + [
            "--virtual-time-budget=30000", "--dump-dom", source.as_uri()]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=90, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Chromium 渲染失败：{exc}") from exc
        match = RESULT_PATTERN.search(result.stdout)
        if result.returncode or not match:
            detail = result.stderr.strip()[-500:]
            raise RuntimeError(f"官方 viewer 未生成 SVG（Chromium {result.returncode}）：{detail}")
        rendered = base64.b64decode(match.group(1), validate=True)
        validate_svg(rendered)
        svg.parent.mkdir(parents=True, exist_ok=True)
        svg.write_bytes(rendered)
        if png is not None:
            width, height = svg_size(rendered)
            target_height = math.ceil(png_width * height / width)
            if target_height > 12000:
                raise RuntimeError("PNG 高度超过 Chromium 截图限制；请调小 --width")
            screenshot = work / "screenshot.html"
            screenshot.write_text(
                '<!doctype html><html><head><meta charset="utf-8"><style>'
                'html,body{margin:0;padding:0;background:white;overflow:hidden}'
                f'img{{display:block;width:{png_width}px;height:{target_height}px}}'
                '</style></head><body>'
                f'<img src="{svg.resolve().as_uri()}"></body></html>', encoding="utf-8")
            png.parent.mkdir(parents=True, exist_ok=True)
            screenshot_command = chrome_args(browser, work / "screenshot-profile") + [
                f"--window-size={png_width},{target_height}",
                f"--screenshot={png.resolve()}", screenshot.as_uri()]
            try:
                shot = subprocess.run(screenshot_command, capture_output=True, text=True,
                                      timeout=60, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError(f"Chromium PNG 截图失败：{exc}") from exc
            if shot.returncode or not png.is_file() or not png.stat().st_size:
                raise RuntimeError(f"Chromium PNG 截图失败：{shot.stderr.strip()[-500:]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drawio", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True, help="SVG output path")
    parser.add_argument("--png", type=Path, help="Also capture a PNG for visual review")
    parser.add_argument("--width", type=int, default=2000, help="PNG width")
    parser.add_argument("--chromium", help="Chromium executable path")
    args = parser.parse_args()
    try:
        render(args.drawio, args.output, args.chromium, args.png, args.width)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(args.output.resolve())
    if args.png:
        print(args.png.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
