#!/usr/bin/env python3
"""Serve one diagram preview and persist edits to its workspace files."""

from __future__ import annotations

import argparse
import fcntl
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from preview_files import (MAX_XML_BYTES, MAX_SVG_BYTES, atomic_write,
                           decode_svg, export_svg, revision, validate_xml)
from drawio_cli import resolve_drawio

MAX_REQUEST_BYTES = 2 * (MAX_XML_BYTES + MAX_SVG_BYTES)


class DiagramHandler(SimpleHTTPRequestHandler):
    directory_path: Path
    diagram_path: Path
    svg_path: Path
    drawio_cli: str | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.directory_path), **kwargs)

    def send_json(self, code: int, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/api/diagram":
            return super().do_GET()
        try:
            xml = self.diagram_path.read_bytes()
            self.send_json(200, {"xml": xml.decode("utf-8-sig"), "revision": revision(xml)})
        except (OSError, UnicodeDecodeError) as exc:
            self.send_json(500, {"error": str(exc)})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/diagram":
            return self.send_json(404, {"error": "未找到接口"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_REQUEST_BYTES:
                return self.send_json(413, {"error": "请求体为空或过大"})
            body = json.loads(self.rfile.read(length))
            xml_text = body.get("xml")
            if not isinstance(xml_text, str):
                raise ValueError("缺少 XML")
            xml = xml_text.encode("utf-8")
            validate_xml(xml)
            fallback_svg = decode_svg(body.get("svg"))
            base_revision = body.get("baseRevision")
            if not isinstance(base_revision, str):
                raise ValueError("缺少基础版本")
            lock_path = self.diagram_path.with_suffix(self.diagram_path.suffix + ".lock")
            with lock_path.open("a+b") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                current = self.diagram_path.read_bytes()
                if revision(current) != base_revision:
                    return self.send_json(409, {"error": "图已被其他会话修改；请刷新页面后重新编辑"})
                svg = fallback_svg
                with tempfile.TemporaryDirectory(dir=self.directory_path) as temporary:
                    draft = Path(temporary) / self.diagram_path.name
                    rendered = Path(temporary) / self.svg_path.name
                    draft.write_bytes(xml)
                    try:
                        export_svg(draft, rendered, self.drawio_cli)
                        svg = rendered.read_bytes()
                    except (RuntimeError, ValueError) as exc:
                        self.log_message("server SVG export failed, using browser SVG: %s", exc)
                atomic_write(self.svg_path, svg)
                atomic_write(self.diagram_path, xml)
                self.send_json(200, {"revision": revision(xml), "drawio": self.diagram_path.name,
                                     "svg": self.svg_path.name})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except OSError as exc:
            self.send_json(500, {"error": f"写入工作区失败：{exc}"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True, help="Persistent workspace output directory")
    parser.add_argument("--drawio", required=True, help=".drawio filename inside directory")
    parser.add_argument("--port", type=int, choices=(5555, 6666, 7777, 8888), default=7777)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--drawio-cli", help="Optional server-side SVG re-export executable")
    args = parser.parse_args()
    directory = args.directory.resolve()
    diagram = (directory / args.drawio).resolve()
    if diagram.parent != directory or diagram.suffix.lower() != ".drawio" or not diagram.is_file():
        parser.error("--drawio must name an existing .drawio file directly inside --directory")
    validate_xml(diagram.read_bytes())
    DiagramHandler.directory_path = directory
    DiagramHandler.diagram_path = diagram
    DiagramHandler.svg_path = directory / f"{diagram.stem}.preview.svg"
    DiagramHandler.drawio_cli = args.drawio_cli or resolve_drawio()
    server = ThreadingHTTPServer((args.bind, args.port), DiagramHandler)
    print(f"Serving http://127.0.0.1:{args.port}/{diagram.stem}.html", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
