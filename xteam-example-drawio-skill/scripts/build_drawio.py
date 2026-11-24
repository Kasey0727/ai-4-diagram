#!/usr/bin/env python3
"""Build a .drawio file plus an interactive .html preview.

Modes
  spec : build_drawio.py spec.json --out DIR
  wrap : build_drawio.py --wrap existing.drawio --out DIR   (html only)

Engines (--engine)
  svg    (default) inline SVG, zero network dependency, works on intranet
  drawio diagrams.net viewer-static from CDN, highest fidelity

Spec format (JSON)
{
  "title": "登录鉴权流程",
  "direction": "TB",
  "nodes": [
    {"id": "start", "label": "用户点击登录", "type": "start"},
    {"id": "check", "label": "校验验证码", "type": "decision"},
    {"id": "ok",    "label": "登录成功",   "type": "end"}
  ],
  "edges": [
    {"from": "start", "to": "check"},
    {"from": "check", "to": "ok", "label": "通过", "style": "success"},
    {"from": "check", "to": "start", "label": "失败", "style": "danger", "dashed": true}
  ]
}

Node types : start | end | process | subprocess | decision | data | db | doc | note
Edge styles: default | success | danger | muted
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "viewer.html.template"

# Single source of truth for both renderers.
NODE_THEME = {
    "start":      {"shape": "ellipse", "fill": "#EAF2FF", "stroke": "#2F6FEB", "font": "#1B3FA0"},
    "end":        {"shape": "ellipse", "fill": "#FFF1F0", "stroke": "#D64545", "font": "#8A1C1C"},
    "process":    {"shape": "rounded", "fill": "#FFFFFF", "stroke": "#C7CDD6", "font": "#1B1F24"},
    "subprocess": {"shape": "process", "fill": "#F7F9FC", "stroke": "#C7CDD6", "font": "#1B1F24"},
    "decision":   {"shape": "rhombus", "fill": "#FFF8E6", "stroke": "#D9A21B", "font": "#6B4A00"},
    "data":       {"shape": "parallelogram", "fill": "#F4F0FF", "stroke": "#7A5AF8", "font": "#3B2A8A"},
    "db":         {"shape": "cylinder", "fill": "#EAF7F0", "stroke": "#1F9D6B", "font": "#12553B"},
    "doc":        {"shape": "document", "fill": "#FFFFFF", "stroke": "#C7CDD6", "font": "#1B1F24"},
    "note":       {"shape": "note", "fill": "#FFFCE8", "stroke": "#D6C36A", "font": "#5C4C10"},
}
DEFAULT_TYPE = "process"

DEFAULT_SIZES = {
    "start": (150, 56),
    "end": (150, 56),
    "decision": (170, 110),
    "db": (130, 90),
    "note": (170, 80),
}
FALLBACK_SIZE = (190, 64)

EDGE_THEME = {
    "default": {"stroke": "#8A94A6", "font": "#4B5563", "width": 1.5},
    "success": {"stroke": "#1F9D6B", "font": "#12553B", "width": 1.5},
    "danger":  {"stroke": "#D64545", "font": "#8A1C1C", "width": 1.5},
    "muted":   {"stroke": "#B6BDC7", "font": "#8A94A6", "width": 1.2},
}

DRAWIO_SHAPES = {
    "ellipse": "ellipse",
    "rounded": "rounded=1;arcSize=12",
    "process": "shape=process;backgroundOutline=1",
    "rhombus": "rhombus",
    "parallelogram": "shape=parallelogram;perimeter=parallelogramPerimeter",
    "cylinder": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=15",
    "document": "shape=document;boundedLbl=1",
    "note": "shape=note;backgroundOutline=1;darkOpacity=0.05",
}

FONT_SIZE = 13
LINE_HEIGHT = 18
PAD = 48


def die(msg: str) -> None:
    print(f"[drawio] 错误: {msg}", file=sys.stderr)
    sys.exit(1)


def slugify(name: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.strip()).strip("-")
    return slug or "diagram"


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------

def find_back_edges(ids: list[str], edges: list[dict]) -> set[tuple[str, str]]:
    """DFS back edges. Excluding them from layering keeps a retry loop from
    pushing the whole graph down one layer per cycle traversal."""
    color = {i: 0 for i in ids}
    adj = defaultdict(list)
    for e in edges:
        adj[str(e["from"])].append(str(e["to"]))
    back: set[tuple[str, str]] = set()
    for root in ids:
        if color[root]:
            continue
        color[root] = 1
        stack = [(root, iter(adj[root]))]
        while stack:
            node, it = stack[-1]
            pushed = False
            for nxt in it:
                if color[nxt] == 0:
                    color[nxt] = 1
                    stack.append((nxt, iter(adj[nxt])))
                    pushed = True
                    break
                if color[nxt] == 1:
                    back.add((node, nxt))
            if not pushed:
                color[node] = 2
                stack.pop()
    return back


def resolve_layout(spec: dict) -> dict:
    nodes = spec.get("nodes") or []
    edges = spec.get("edges") or []
    if not nodes:
        die("spec 中 nodes 不能为空")

    ids: list[str] = []
    for n in nodes:
        nid = str(n.get("id") or "").strip()
        if not nid:
            die("每个 node 必须有非空 id")
        if nid in ids:
            die(f"node id 重复: {nid}")
        ids.append(nid)
    idset = set(ids)
    node_by_id = {str(n["id"]): n for n in nodes}

    for i, e in enumerate(edges, 1):
        for key in ("from", "to"):
            if str(e.get(key)) not in idset:
                die(f"第 {i} 条边引用了不存在的节点: {e.get(key)!r}")

    direction = str(spec.get("direction", "TB")).upper()
    if direction not in ("TB", "LR"):
        die("direction 只支持 TB 或 LR")

    back_edges = find_back_edges(ids, edges)
    succ = defaultdict(list)
    for e in edges:
        pair = (str(e["from"]), str(e["to"]))
        if pair not in back_edges:
            succ[pair[0]].append(pair[1])

    depth = {i: 0 for i in ids}
    for _ in range(len(ids) + 1):
        changed = False
        for src, targets in succ.items():
            for dst in targets:
                if depth[dst] < depth[src] + 1:
                    depth[dst] = depth[src] + 1
                    changed = True
        if not changed:
            break

    by_depth = defaultdict(list)
    for nid in ids:
        by_depth[depth[nid]].append(nid)
    for d in by_depth:
        by_depth[d].sort(key=lambda x: ids.index(x))

    def size_of(node: dict) -> tuple[int, int]:
        base = DEFAULT_SIZES.get(node.get("type"), FALLBACK_SIZE)
        return int(node.get("width") or base[0]), int(node.get("height") or base[1])

    gap_main, gap_cross = 80, 70

    # Layer thickness on the MAIN axis only (height for TB, width for LR).
    layer_main = {
        d: max(size_of(node_by_id[nid])[1 if direction == "TB" else 0] for nid in layer)
        for d, layer in by_depth.items()
    }

    pos: dict[str, tuple[float, float, int, int]] = {}
    main_cursor = 0.0
    for d in sorted(by_depth):
        layer = by_depth[d]
        sizes = []
        for nid in layer:
            w, h = size_of(node_by_id[nid])
            sizes.append((w, h) if direction == "TB" else (h, w))
        total = sum(c for c, _ in sizes) + gap_cross * (len(layer) - 1)
        cross_cursor = -total / 2
        for nid, (cross, main) in zip(layer, sizes):
            if direction == "TB":
                pos[nid] = (cross_cursor, main_cursor, cross, main)
            else:
                pos[nid] = (main_cursor, cross_cursor, main, cross)
            cross_cursor += cross + gap_cross
        main_cursor += layer_main[d] + gap_main

    for node in nodes:
        nid = str(node["id"])
        x, y, w, h = pos[nid]
        if "x" in node or "y" in node:
            x, y = node.get("x", x), node.get("y", y)
        pos[nid] = (x, y, w, h)

    min_x = min(v[0] for v in pos.values())
    min_y = min(v[1] for v in pos.values())
    shift_x, shift_y = -min_x + PAD, -min_y + PAD

    scene_nodes = []
    for node in nodes:
        nid = str(node["id"])
        x, y, w, h = pos[nid]
        ntype = str(node.get("type") or DEFAULT_TYPE)
        theme = NODE_THEME.get(ntype, NODE_THEME[DEFAULT_TYPE])
        scene_nodes.append({
            "id": nid,
            "label": str(node.get("label", "")),
            "type": ntype,
            "shape": theme["shape"],
            "fill": theme["fill"],
            "stroke": theme["stroke"],
            "font": theme["font"],
            "x": round(x + shift_x, 2),
            "y": round(y + shift_y, 2),
            "w": int(w),
            "h": int(h),
        })

    width = max(n["x"] + n["w"] for n in scene_nodes) + PAD
    height = max(n["y"] + n["h"] for n in scene_nodes) + PAD

    scene_edges = []
    for e in edges:
        est = str(e.get("style") or "default")
        theme = EDGE_THEME.get(est, EDGE_THEME["default"])
        scene_edges.append({
            "from": str(e["from"]),
            "to": str(e["to"]),
            "label": str(e.get("label", "")),
            "style": est,
            "stroke": theme["stroke"],
            "font": theme["font"],
            "width": theme["width"],
            "dashed": bool(e.get("dashed")),
            "back": (str(e["from"]), str(e["to"])) in back_edges,
        })

    return {
        "title": str(spec.get("title") or "流程图"),
        "direction": direction,
        "nodes": scene_nodes,
        "edges": scene_edges,
        "width": round(width, 2),
        "height": round(height, 2),
    }


# --------------------------------------------------------------------------
# drawio serialisation
# --------------------------------------------------------------------------

def drawio_node_style(node: dict) -> str:
    shape = DRAWIO_SHAPES.get(node["shape"], "rounded=1;arcSize=12")
    return (
        f"{shape};whiteSpace=wrap;html=1;"
        f"fillColor={node['fill']};strokeColor={node['stroke']};"
        f"fontColor={node['font']};fontSize={FONT_SIZE};"
    )


def drawio_edge_style(edge: dict) -> str:
    style = (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
        f"strokeColor={edge['stroke']};strokeWidth={edge['width']};"
        f"endArrow=block;endFill=1;fontSize=12;fontColor={edge['font']};"
        "labelBackgroundColor=#FFFFFF;"
    )
    if edge["dashed"]:
        style += "dashed=1;"
    return style


def to_mxfile(scene: dict) -> str:
    mxfile = ET.Element(
        "mxfile", {"host": "app.diagrams.net", "agent": "xteam-drawio-skill", "version": "24.7.17"}
    )
    diagram = ET.SubElement(mxfile, "diagram", {"id": "page-1", "name": scene["title"]})
    model = ET.SubElement(
        diagram, "mxGraphModel",
        {
            "dx": "1200", "dy": "900", "grid": "1", "gridSize": "10", "guides": "1",
            "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "0",
            "pageScale": "1", "pageWidth": "1280", "pageHeight": "900", "math": "0", "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    for node in scene["nodes"]:
        cell = ET.SubElement(
            root, "mxCell",
            {"id": node["id"], "value": node["label"], "style": drawio_node_style(node),
             "vertex": "1", "parent": "1"},
        )
        ET.SubElement(
            cell, "mxGeometry",
            {"x": f"{node['x']:g}", "y": f"{node['y']:g}",
             "width": str(node["w"]), "height": str(node["h"]), "as": "geometry"},
        )

    for idx, edge in enumerate(scene["edges"], 1):
        cell = ET.SubElement(
            root, "mxCell",
            {"id": f"e{idx}", "value": edge["label"], "style": drawio_edge_style(edge),
             "edge": "1", "parent": "1", "source": edge["from"], "target": edge["to"]},
        )
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})

    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode")


# --------------------------------------------------------------------------
# inline svg renderer
# --------------------------------------------------------------------------

def text_units(ch: str) -> float:
    if ord(ch) > 0x2E80:
        return 1.0
    if ch in " .,:;'|!":
        return 0.3
    if ch.isupper():
        return 0.66
    return 0.54


def wrap_label(text: str, max_width: float, font_size: int = FONT_SIZE) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for raw in text.split("\n"):
        if not raw:
            lines.append("")
            continue
        line, used = "", 0.0
        for ch in raw:
            u = text_units(ch) * font_size
            if used + u > max_width and line:
                lines.append(line)
                line, used = "", 0.0
            line += ch
            used += u
        if line:
            lines.append(line)
    return lines


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def svg_node_shape(node: dict) -> str:
    x, y, w, h = node["x"], node["y"], node["w"], node["h"]
    shape = node["shape"]
    common = f'fill="{node["fill"]}" stroke="{node["stroke"]}" stroke-width="1.5"'

    if shape == "ellipse":
        return f'<ellipse cx="{x + w / 2:g}" cy="{y + h / 2:g}" rx="{w / 2:g}" ry="{h / 2:g}" {common}/>'
    if shape == "rhombus":
        pts = f"{x + w / 2:g},{y:g} {x + w:g},{y + h / 2:g} {x + w / 2:g},{y + h:g} {x:g},{y + h / 2:g}"
        return f'<polygon points="{pts}" {common}/>'
    if shape == "parallelogram":
        k = min(w * 0.22, 26)
        pts = f"{x + k:g},{y:g} {x + w:g},{y:g} {x + w - k:g},{y + h:g} {x:g},{y + h:g}"
        return f'<polygon points="{pts}" {common}/>'
    if shape == "cylinder":
        ry = min(h * 0.14, 16)
        body = (
            f"M{x:g},{y + ry:g} L{x:g},{y + h - ry:g} "
            f"A{w / 2:g},{ry:g} 0 0 0 {x + w:g},{y + h - ry:g} "
            f"L{x + w:g},{y + ry:g} Z"
        )
        top = f'<ellipse cx="{x + w / 2:g}" cy="{y + ry:g}" rx="{w / 2:g}" ry="{ry:g}" {common}/>'
        return f'<path d="{body}" {common}/>{top}'
    if shape == "document":
        k = h * 0.16
        d = (
            f"M{x:g},{y:g} L{x + w:g},{y:g} L{x + w:g},{y + h - k:g} "
            f"Q{x + w * 0.75:g},{y + h - k * 2.4:g} {x + w / 2:g},{y + h - k:g} "
            f"Q{x + w * 0.25:g},{y + h + k * 0.4:g} {x:g},{y + h - k:g} Z"
        )
        return f'<path d="{d}" {common}/>'
    if shape == "note":
        k = min(w, h) * 0.24
        d = (
            f"M{x:g},{y:g} L{x + w - k:g},{y:g} L{x + w:g},{y + k:g} "
            f"L{x + w:g},{y + h:g} L{x:g},{y + h:g} Z"
        )
        fold = f'M{x + w - k:g},{y:g} L{x + w - k:g},{y + k:g} L{x + w:g},{y + k:g}'
        return (
            f'<path d="{d}" {common}/>'
            f'<path d="{fold}" fill="none" stroke="{node["stroke"]}" stroke-width="1.2"/>'
        )
    if shape == "process":
        bar = min(w * 0.08, 14)
        inner = (
            f'<line x1="{x + bar:g}" y1="{y:g}" x2="{x + bar:g}" y2="{y + h:g}" '
            f'stroke="{node["stroke"]}" stroke-width="1.2"/>'
            f'<line x1="{x + w - bar:g}" y1="{y:g}" x2="{x + w - bar:g}" y2="{y + h:g}" '
            f'stroke="{node["stroke"]}" stroke-width="1.2"/>'
        )
        return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="3" {common}/>{inner}'

    return (
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" ry="8" {common}/>'
    )


BASELINE = FONT_SIZE * 0.36  # visual centre of a CJK+Latin glyph box above baseline


def svg_text_block(node: dict) -> str:
    if node["shape"] == "rhombus":
        inner_w = node["w"] * 0.52
    elif node["shape"] == "ellipse":
        inner_w = node["w"] * 0.72
    else:
        inner_w = node["w"] - 20
    lines = wrap_label(node["label"], max(inner_w, 30))
    if not lines:
        return ""

    cx = node["x"] + node["w"] / 2
    cy = node["y"] + node["h"] / 2
    # Explicit baseline maths instead of dominant-baseline, which renders
    # inconsistently for CJK across embedded WebKit builds.
    first_y = cy - (len(lines) - 1) * LINE_HEIGHT / 2 + BASELINE
    tspans = []
    for i, line in enumerate(lines):
        dy = 0 if i == 0 else LINE_HEIGHT
        tspans.append(f'<tspan x="{cx:g}" dy="{dy:g}">{esc(line)}</tspan>')
    return (
        f'<text x="{cx:g}" y="{first_y:g}" text-anchor="middle" '
        f'fill="{node["font"]}" font-size="{FONT_SIZE}" font-family="{FONT_FAMILY}">'
        + "".join(tspans)
        + "</text>"
    )


FONT_FAMILY = (
    "-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,Hiragino Sans GB,"
    "Microsoft YaHei,sans-serif"
)


def ports(node: dict) -> dict[str, tuple[float, float]]:
    x, y, w, h = node["x"], node["y"], node["w"], node["h"]
    return {
        "top": (x + w / 2, y),
        "bottom": (x + w / 2, y + h),
        "left": (x, y + h / 2),
        "right": (x + w, y + h / 2),
    }


def rounded_polyline(points: list[tuple[float, float]], r: float = 14) -> str:
    """Polyline with quadratic corner fillets, so back edges read as routed
    wires instead of cutting diagonally through the node stack."""
    if len(points) < 2:
        return ""
    d = [f"M{points[0][0]:g},{points[0][1]:g}"]
    for i in range(1, len(points) - 1):
        px, py = points[i - 1]
        cx, cy = points[i]
        nx, ny = points[i + 1]
        v1 = (px - cx, py - cy)
        v2 = (nx - cx, ny - cy)
        l1 = max((v1[0] ** 2 + v1[1] ** 2) ** 0.5, 1e-6)
        l2 = max((v2[0] ** 2 + v2[1] ** 2) ** 0.5, 1e-6)
        rr = min(r, l1 / 2, l2 / 2)
        ax, ay = cx + v1[0] / l1 * rr, cy + v1[1] / l1 * rr
        bx, by = cx + v2[0] / l2 * rr, cy + v2[1] / l2 * rr
        d.append(f"L{ax:g},{ay:g} Q{cx:g},{cy:g} {bx:g},{by:g}")
    d.append(f"L{points[-1][0]:g},{points[-1][1]:g}")
    return " ".join(d)


def scene_bounds(node: dict, pad: float = 60) -> tuple[float, float]:
    return node["x"] - pad, node["x"] + node["w"] + pad


def svg_edge_path(a: dict, b: dict, back: bool,
                  corridor: tuple[float, float] | None = None,
                  direction: str = "TB"
                  ) -> tuple[str, tuple[float, float]]:
    pa, pb = ports(a), ports(b)
    acx, acy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
    bcx, bcy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    dx, dy = bcx - acx, bcy - acy

    if back:
        # A back edge must run in the cross-axis gutter, never across the
        # main axis: left/right for TB, top/bottom for LR.
        if direction == "TB":
            lo = min(a["x"], b["x"])
            left_bound = max(lo - 46, 16)
            side = "left" if dx <= 0 else "right"
            sx, sy = pa[side]
            ex, ey = pb[side]
            cx = left_bound if side == "left" else left_bound + abs(ex - sx) + 90
            pts = [(sx, sy), (cx, sy), (cx, ey), (ex, ey)]
            mid = (cx, (sy + ey) / 2)
            if abs(ey - sy) < 30:
                mid = ((sx + ex) / 2, sy)
            return rounded_polyline(pts), mid

        # LR: detour through the vertical gutter between the two endpoints.
        mid_y = (min(acy, bcy) + max(acy, bcy)) / 2
        top = min(a["y"], b["y"])
        bottom = max(a["y"] + a["h"], b["y"] + b["h"])
        side = "top" if bcy <= acy else "bottom"
        sx, sy = pa[side]
        ex, ey = pb[side]
        cy = max(top - 44, 16) if side == "top" else bottom + 44
        pts = [(sx, sy), (sx, cy), (ex, cy), (ex, ey)]
        mid = ((sx + ex) / 2, cy)
        if abs(ex - sx) < 30:
            mid = (sx, (sy + ey) / 2)
        return rounded_polyline(pts), mid

    if abs(dy) >= abs(dx):
        s = pa["bottom"] if dy > 0 else pa["top"]
        e = pb["top"] if dy > 0 else pb["bottom"]
        k = max(abs(e[1] - s[1]) * 0.45, 28)
        c1y = s[1] + (k if dy > 0 else -k)
        c2y = e[1] - (k if dy > 0 else -k)
        d = f"M{s[0]:g},{s[1]:g} C{s[0]:g},{c1y:g} {e[0]:g},{c2y:g} {e[0]:g},{e[1]:g}"
        mid = (0.125 * s[0] + 0.375 * s[0] + 0.375 * e[0] + 0.125 * e[0], (s[1] + e[1]) / 2)
        return d, mid

    s = pa["right"] if dx > 0 else pa["left"]
    e = pb["left"] if dx > 0 else pb["right"]
    k = max(abs(e[0] - s[0]) * 0.45, 28)
    c1x = s[0] + (k if dx > 0 else -k)
    c2x = e[0] - (k if dx > 0 else -k)
    d = f"M{s[0]:g},{s[1]:g} C{c1x:g},{s[1]:g} {c2x:g},{e[1]:g} {e[0]:g},{e[1]:g}"
    mid = ((s[0] + e[0]) / 2, 0.125 * s[1] + 0.375 * s[1] + 0.375 * e[1] + 0.125 * e[1])
    return d, mid


def to_svg(scene: dict) -> str:
    by_id = {n["id"]: n for n in scene["nodes"]}
    w, h = scene["width"], scene["height"]

    # One marker per edge colour: context-stroke is not reliable in older
    # WebKit builds used by some embedded preview hosts.
    colors = sorted({e["stroke"] for e in scene["edges"]})
    markers = []
    for i, color in enumerate(colors):
        markers.append(
            f'<marker id="arw{i}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
        )
    marker_index = {c: i for i, c in enumerate(colors)}

    corridor = (
        max(min(n["x"] for n in scene["nodes"]) - 48, 24),
        min(max(n["x"] + n["w"] for n in scene["nodes"]) + 48, w - 24),
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" '
        f'width="{w:g}" height="{h:g}" role="img" aria-label="{esc(scene["title"])}">',
        "<defs>" + "".join(markers) + "</defs>",
    ]

    # Nodes first: edges terminate exactly on the border, so drawing them
    # after the shapes keeps arrowheads visible instead of clipped.
    for node in scene["nodes"]:
        parts.append(f'<g class="node" data-id="{esc(node["id"])}">')
        parts.append(svg_node_shape(node))
        parts.append(svg_text_block(node))
        parts.append("</g>")

    labels = []
    for edge in scene["edges"]:
        a, b = by_id[edge["from"]], by_id[edge["to"]]
        d, mid = svg_edge_path(a, b, edge["back"], corridor, scene.get("direction", "TB"))
        dash = ' stroke-dasharray="5 5"' if edge["dashed"] else ""
        parts.append(
            f'<path d="{d}" fill="none" stroke="{edge["stroke"]}" '
            f'stroke-width="{edge["width"]}" stroke-linecap="round"{dash} '
            f'marker-end="url(#arw{marker_index[edge["stroke"]]})"/>'
        )
        if edge["label"]:
            lines = wrap_label(edge["label"], 150, 12)
            bw = max(sum(text_units(ch) * 12 for ch in l) for l in lines) + 14
            bh = len(lines) * 16 + 6
            labels.append(
                f'<rect x="{mid[0] - bw / 2:g}" y="{mid[1] - bh / 2:g}" '
                f'width="{bw:g}" height="{bh:g}" rx="4" fill="#FFFFFF" opacity="0.96"/>'
            )
            ty = mid[1] - (len(lines) - 1) * 16 / 2
            for i, line in enumerate(lines):
                labels.append(
                    f'<text x="{mid[0]:g}" y="{ty + i * 16 + 4.3:g}" text-anchor="middle" '
                    f'fill="{edge["font"]}" font-size="12" '
                    f'font-family="{FONT_FAMILY}">{esc(line)}</text>'
                )

    parts.extend(labels)
    parts.append("</svg>")
    return "".join(p for p in parts if p)


# --------------------------------------------------------------------------
# html assembly
# --------------------------------------------------------------------------

def render_html(mxfile_xml: str, scene: dict, title: str, drawio_name: str,
                engine: str) -> str:
    if not TEMPLATE.exists():
        die(f"找不到模板: {TEMPLATE}")

    if engine == "drawio":
        payload = json.dumps(
            {"xml": mxfile_xml, "nav": False, "resize": False, "toolbar": "",
             "highlight": "#2F6FEB", "border": 40},
            ensure_ascii=False, separators=(",", ":"),
        )
        canvas = f'<div class="mxgraph" data-mxgraph="{html.escape(payload, quote=True)}"></div>'
        viewer = '<script type="text/javascript" src="https://viewer.diagrams.net/js/viewer-static.min.js"></script>'
    else:
        canvas = to_svg(scene)
        viewer = ""

    mxfile_js = json.dumps(mxfile_xml, ensure_ascii=False).replace("</", "<\\/")
    name_js = json.dumps(drawio_name, ensure_ascii=False).replace("</", "<\\/")

    out = TEMPLATE.read_text(encoding="utf-8")
    out = out.replace("__TITLE__", html.escape(title, quote=True))
    out = out.replace("__DRAWIO_NAME__", html.escape(drawio_name, quote=True))
    out = out.replace("__CANVAS_HTML__", canvas)
    out = out.replace("__MXFILE_JSON__", mxfile_js)
    out = out.replace("__DRAWIO_NAME_JSON__", name_js)
    out = out.replace("__VIEWER_SCRIPT__", viewer)
    return out


def validate(mxfile_xml: str) -> None:
    try:
        rt = ET.fromstring(mxfile_xml)
    except ET.ParseError as exc:
        die(f"XML 不合法: {exc}")
    cells = rt.findall(".//mxCell")
    cell_ids = {c.get("id") for c in cells}
    for c in cells:
        if c.get("source") and c.get("source") not in cell_ids:
            die(f"边的 source 不存在: {c.get('source')}")
        if c.get("target") and c.get("target") not in cell_ids:
            die(f"边的 target 不存在: {c.get('target')}")
    if not any(c.get("vertex") == "1" for c in cells):
        die("没有任何节点")


def write_outputs(mxfile_xml: str, scene: dict, title: str, drawio_name: str,
                  out_dir: Path, engine: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    drawio_path = out_dir / drawio_name
    html_path = out_dir / (drawio_path.stem + ".html")
    drawio_path.write_text(mxfile_xml.rstrip() + "\n", encoding="utf-8")
    html_path.write_text(
        render_html(mxfile_xml, scene, title, drawio_name, engine), encoding="utf-8"
    )
    return drawio_path, html_path


def main() -> None:
    ap = argparse.ArgumentParser(description="生成 .drawio 与可交互 .html")
    ap.add_argument("spec", nargs="?", help="spec JSON 路径")
    ap.add_argument("--wrap", help="已有 .drawio 文件路径，仅生成配套 html")
    ap.add_argument("--out", default=".", help="输出目录，默认当前目录")
    ap.add_argument("--title", help="覆盖标题")
    ap.add_argument("--name", help="覆盖输出文件名（不含扩展名）")
    ap.add_argument(
        "--engine", choices=("svg", "drawio"), default="svg",
        help="渲染引擎：svg 离线零依赖（默认），drawio 走 CDN 高保真",
    )
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()

    if args.wrap:
        src = Path(args.wrap)
        if not src.exists():
            die(f"文件不存在: {src}")
        raw = src.read_text(encoding="utf-8")
        validate(raw)
        title = args.title or src.stem
        scene = scene_from_mxfile(raw, title)
        drawio_name = (args.name or src.stem) + ".drawio"
        drawio_path, html_path = write_outputs(raw, scene, title, drawio_name, out_dir, args.engine)
        print(json.dumps({"drawio": str(drawio_path), "html": str(html_path)}, ensure_ascii=False))
        return

    if not args.spec:
        ap.error("需要 spec 文件或 --wrap 参数")

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    scene = resolve_layout(spec)
    title = args.title or scene["title"]
    mxfile_xml = to_mxfile(scene)
    validate(mxfile_xml)

    drawio_name = (args.name or slugify(title)) + ".drawio"
    drawio_path, html_path = write_outputs(mxfile_xml, scene, title, drawio_name, out_dir, args.engine)
    print(json.dumps({"drawio": str(drawio_path), "html": str(html_path)}, ensure_ascii=False))


def scene_from_mxfile(raw: str, title: str) -> dict:
    """Minimal mxfile -> scene extraction so --wrap can also render SVG."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        die(f"无法解析 drawio 文件: {exc}")

    cells = list(root.iter("mxCell"))
    nodes, edges, node_ids = [], [], set()
    for c in cells:
        if c.get("vertex") == "1":
            g = c.find("mxGeometry")
            if g is None:
                continue
            node_ids.add(c.get("id"))
            style = c.get("style") or ""
            shape = "rounded"
            if "ellipse" in style:
                shape = "ellipse"
            elif "rhombus" in style:
                shape = "rhombus"
            elif "parallelogram" in style:
                shape = "parallelogram"
            elif "cylinder" in style:
                shape = "cylinder"
            elif "shape=document" in style:
                shape = "document"
            elif "shape=note" in style:
                shape = "note"
            elif "shape=process" in style:
                shape = "process"

            def pick(key: str, fallback: str) -> str:
                m = re.search(rf"{key}=(#[0-9A-Fa-f]{{3,8}})", style)
                return m.group(1) if m else fallback

            nodes.append({
                "id": c.get("id"),
                "label": re.sub(r"<[^>]+>", "", html.unescape(c.get("value") or "")),
                "type": DEFAULT_TYPE,
                "shape": shape,
                "fill": pick("fillColor", "#FFFFFF"),
                "stroke": pick("strokeColor", "#C7CDD6"),
                "font": pick("fontColor", "#1B1F24"),
                "x": float(g.get("x") or 0),
                "y": float(g.get("y") or 0),
                "w": float(g.get("width") or 120),
                "h": float(g.get("height") or 60),
            })

    for c in cells:
        if c.get("edge") == "1":
            style = c.get("style") or ""
            edges.append({
                "from": c.get("source"), "to": c.get("target"),
                "label": re.sub(r"<[^>]+>", "", html.unescape(c.get("value") or "")),
                "style": "default",
                "stroke": "#8A94A6", "font": "#4B5563", "width": 1.5,
                "dashed": "dashed=1" in style,
                "back": False,
            })

    if not nodes:
        die("drawio 文件中没有可渲染的节点")

    # normalise coordinates so the SVG viewBox starts near the origin
    min_x = min(n["x"] for n in nodes)
    min_y = min(n["y"] for n in nodes)
    for n in nodes:
        n["x"] = round(n["x"] - min_x + PAD, 2)
        n["y"] = round(n["y"] - min_y + PAD, 2)
        n["w"], n["h"] = int(n["w"]), int(n["h"])

    return {
        "title": title,
        "direction": "TB",
        "nodes": nodes,
        "edges": [e for e in edges if e["from"] in node_ids and e["to"] in node_ids],
        "width": round(max(n["x"] + n["w"] for n in nodes) + PAD, 2),
        "height": round(max(n["y"] + n["h"] for n in nodes) + PAD, 2),
    }


if __name__ == "__main__":
    main()
