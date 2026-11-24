"""File-backed diagram validation, SVG export, and atomic preview writes."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import base64
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from drawio_cli import resolve_drawio
from validate import check_page

MAX_XML_BYTES = 8 * 1024 * 1024
MAX_SVG_BYTES = 16 * 1024 * 1024
DRAWIO_SVG_DOCTYPE = (b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
                      b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">')


def revision(xml: bytes) -> str:
    return sha256(xml).hexdigest()


def validate_xml(xml: bytes) -> None:
    if not xml or len(xml) > MAX_XML_BYTES or b"<!DOCTYPE" in xml.upper():
        raise ValueError("图数据为空、过大或包含不允许的 DTD")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f"draw.io XML 无法解析：{exc}") from exc
    if root.tag != "mxfile":
        raise ValueError("仅接受原生 .drawio <mxfile> 文件")
    pages = root.findall("diagram")
    if not pages or any(page.find("mxGraphModel") is None for page in pages):
        raise ValueError("仅接受未压缩且包含 mxGraphModel 的 .drawio")
    errors = [finding for page in pages for finding in check_page(page)[0]]
    if errors:
        raise ValueError(f"图结构校验失败：{errors[0]['message']}")


def decode_svg(data_uri: str) -> bytes:
    prefix = "data:image/svg+xml"
    if not isinstance(data_uri, str) or not data_uri.startswith(prefix) or "," not in data_uri:
        raise ValueError("缺少 SVG 导出数据")
    header, payload = data_uri.split(",", 1)
    if ";base64" in header:
        svg = base64.b64decode(payload, validate=True)
    else:
        from urllib.parse import unquote_to_bytes
        svg = unquote_to_bytes(payload)
    validate_svg(svg)
    return svg


def validate_svg(svg: bytes) -> None:
    if not svg or len(svg) > MAX_SVG_BYTES:
        raise ValueError("SVG 为空或过大")
    without_standard_doctype = svg.replace(DRAWIO_SVG_DOCTYPE, b"", 1)
    if b"<!DOCTYPE" in without_standard_doctype.upper():
        raise ValueError("SVG 包含不允许的 DTD")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError(f"SVG 无法解析：{exc}") from exc
    if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
        raise ValueError("导出结果不是 SVG")


def export_svg(drawio: Path, svg: Path, executable: str | None = None) -> None:
    executable = executable or resolve_drawio()
    if not executable:
        raise RuntimeError("未找到 draw.io CLI；请提供已有 SVG，或在 XTeam 中使用浏览器导出")
    try:
        result = subprocess.run(
            [executable, "-x", "-f", "svg", "-o", str(svg), str(drawio)],
            capture_output=True, text=True, timeout=90, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"draw.io SVG 导出失败：{exc}") from exc
    if result.returncode or not svg.is_file():
        raise RuntimeError(f"draw.io SVG 导出失败：{result.stderr.strip()[:500]}")
    validate_svg(svg.read_bytes())


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
