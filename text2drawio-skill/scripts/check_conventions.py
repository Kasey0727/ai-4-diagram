#!/usr/bin/env python3
"""Check pure black/white colors, vertical lanes, and consistent decision edges."""

import argparse
import sys
import xml.etree.ElementTree as ET

from validate import abs_rect, endpoint


ALLOWED_COLORS = {"#000000", "#FFFFFF"}
BRANCH_KEYS = ("edgeStyle", "rounded", "orthogonalLoop", "jettySize",
               "strokeColor", "strokeWidth", "endArrow", "endSize")
GEOMETRY_TOLERANCE = 0.5
STRAIGHT_SNAP_LIMIT = 24.0


def style_map(style):
    result = {}
    for part in (style or "").split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            result[key] = value
    return result


def geometry(cell):
    node = cell.find("mxGeometry")
    if node is None:
        return None
    try:
        return tuple(float(node.get(key, "0")) for key in ("x", "y", "width", "height"))
    except ValueError:
        return None


def first_waypoint(edge):
    node = edge.find("./mxGeometry/Array/mxPoint")
    if node is None:
        return None
    try:
        return float(node.get("x")), float(node.get("y"))
    except (TypeError, ValueError):
        return None


def lane_gaps(cells):
    """Adjacent sibling swimlanes with visible horizontal gaps."""
    by_parent = {}
    for cell in cells:
        by_parent.setdefault(cell.get("parent"), []).append(cell)
    for pool in cells:
        if pool.get("vertex") != "1" or "swimlane" not in (pool.get("style") or ""):
            continue
        lanes = [cell for cell in by_parent.get(pool.get("id"), [])
                 if cell.get("vertex") == "1" and "swimlane" in (cell.get("style") or "")]
        boxes = [(cell, geometry(cell)) for cell in lanes]
        if len(boxes) < 2 or any(box is None for _, box in boxes):
            continue
        boxes.sort(key=lambda pair: pair[1][0])
        for (left, (lx, _, lw, _)), (right, (rx, _, _, _)) in zip(boxes, boxes[1:]):
            gap = rx - lx - lw
            if gap > GEOMETRY_TOLERANCE:
                yield left, right, gap, rx - lx


def nonrectangular(cell):
    style = cell.get("style") or ""
    shape = style_map(style).get("shape")
    return "ellipse" in style.split(";") or (shape is not None and shape not in ("rect", "rectangle"))


def near_straight_edges(cells):
    """Small port mismatch on an otherwise direct horizontal/vertical edge."""
    by_id = {cell.get("id"): cell for cell in cells if cell.get("id")}
    for edge in cells:
        if edge.get("edge") != "1" or edge.find("./mxGeometry/Array/mxPoint") is not None:
            continue
        source, target = by_id.get(edge.get("source")), by_id.get(edge.get("target"))
        if source is None or target is None or any(
                "rhombus" in (cell.get("style") or "") for cell in (source, target)):
            continue
        source_box, target_box = abs_rect(source, by_id), abs_rect(target, by_id)
        start, end = endpoint(edge, "source", by_id), endpoint(edge, "target", by_id)
        if not all((source_box, target_box, start, end)):
            continue
        style = style_map(edge.get("style"))
        if style.get("edgeStyle") != "orthogonalEdgeStyle":
            continue
        try:
            exit_x, exit_y = float(style["exitX"]), float(style["exitY"])
            entry_x, entry_y = float(style["entryX"]), float(style["entryY"])
        except (KeyError, ValueError):
            exit_x = exit_y = entry_x = entry_y = None
        sx, sy, sw, sh = source_box
        tx, ty, tw, th = target_box
        if exit_x is None:
            horizontal = ((sx + sw <= tx or tx + tw <= sx)
                          and abs((sy + sh / 2) - (ty + th / 2)) <= STRAIGHT_SNAP_LIMIT)
            vertical = ((sy + sh <= ty or ty + th <= sy)
                        and abs((sx + sw / 2) - (tx + tw / 2)) <= STRAIGHT_SNAP_LIMIT)
        else:
            horizontal = ((exit_x == 1 and entry_x == 0 and sx + sw <= tx)
                          or (exit_x == 0 and entry_x == 1 and tx + tw <= sx))
            vertical = ((exit_y == 1 and entry_y == 0 and sy + sh <= ty)
                        or (exit_y == 0 and entry_y == 1 and ty + th <= sy))
        if horizontal:
            first_y = sy + sh / 2 if exit_x is None else start[1]
            last_y = ty + th / 2 if exit_x is None else end[1]
            offset = abs(first_y - last_y)
            perimeter_offset = ((nonrectangular(source) and exit_y is not None and abs(exit_y - 0.5) > 0.000001)
                                or (nonrectangular(target) and entry_y is not None and abs(entry_y - 0.5) > 0.000001))
            if offset <= STRAIGHT_SNAP_LIMIT and (exit_x is None or offset > GEOMETRY_TOLERANCE or perimeter_offset):
                yield edge, "horizontal", offset, (first_y + last_y) / 2, source_box, target_box, source, target
        elif vertical:
            first_x = sx + sw / 2 if exit_x is None else start[0]
            last_x = tx + tw / 2 if exit_x is None else end[0]
            offset = abs(first_x - last_x)
            perimeter_offset = ((nonrectangular(source) and exit_x is not None and abs(exit_x - 0.5) > 0.000001)
                                or (nonrectangular(target) and entry_x is not None and abs(entry_x - 0.5) > 0.000001))
            if offset <= STRAIGHT_SNAP_LIMIT and (exit_x is None or offset > GEOMETRY_TOLERANCE or perimeter_offset):
                yield edge, "vertical", offset, (first_x + last_x) / 2, source_box, target_box, source, target


def inspect(path):
    root = ET.parse(path).getroot()
    cells = root.findall(".//mxCell")
    findings = []

    for cell in cells:
        style = style_map(cell.get("style"))
        for key, color in style.items():
            if key.lower().endswith("color") and color.upper() not in ALLOWED_COLORS:
                findings.append(f"{cell.get('id')}: {key} must be #000000 or #FFFFFF, got {color}")
        if cell.get("vertex") == "1":
            for key in ("fillColor", "strokeColor", "fontColor"):
                if key not in style:
                    findings.append(f"{cell.get('id')}: missing explicit {key}")
        if cell.get("edge") == "1":
            for key in (("strokeColor", "fontColor") if cell.get("value") else ("strokeColor",)):
                if key not in style:
                    findings.append(f"{cell.get('id')}: missing explicit {key}")
        if cell.get("vertex") == "1" and cell.get("value"):
            fill, font = style.get("fillColor"), style.get("fontColor", "#000000")
            if fill and fill.upper() == font.upper():
                findings.append(f"{cell.get('id')}: label color matches the fill")

    for element in root.iter():
        for key, color in element.attrib.items():
            if key.lower().endswith("color") or key == "background":
                if color.upper() not in ALLOWED_COLORS:
                    findings.append(f"{element.tag}: {key} must be #000000 or #FFFFFF, got {color}")

    by_parent = {}
    for cell in cells:
        by_parent.setdefault(cell.get("parent"), []).append(cell)

    for pool in cells:
        if "swimlane" not in (pool.get("style") or ""):
            continue
        lanes = [c for c in by_parent.get(pool.get("id"), [])
                 if "swimlane" in (c.get("style") or "") and c.get("vertex") == "1"]
        if len(lanes) < 2:
            continue
        boxes = [(lane.get("id"), geometry(lane)) for lane in lanes]
        if any(box is None for _, box in boxes):
            findings.append(f"{pool.get('id')}: lane missing geometry")
            continue
        boxes.sort(key=lambda item: item[1][0])
        y0, h0 = boxes[0][1][1], boxes[0][1][3]
        for lane_id, (x, y, w, h) in boxes:
            if y != y0 or h != h0 or h <= w:
                findings.append(f"{lane_id}: lane must be a tall column with the same y and height as its peers")
        for (left_id, (lx, _, lw, _)), (right_id, (rx, _, _, _)) in zip(boxes, boxes[1:]):
            if lx + lw > rx:
                findings.append(f"{left_id}/{right_id}: vertical lanes overlap horizontally")

    for left, right, gap, width in lane_gaps(cells):
        findings.append(f"{left.get('id')}/{right.get('id')}: {gap:g}px lane gap; "
                        f"set {left.get('id')} width to {width:g} so the lanes touch")

    for edge, direction, offset, _, _, _, _, _ in near_straight_edges(cells):
        findings.append(f"{edge.get('id')}: near-{direction} direct edge needs explicit aligned ports "
                        f"(port offset {offset:g}px); align absolute anchors and "
                        "keep non-rectangular perimeter ports at the side center")

    for decision in cells:
        if decision.get("vertex") != "1" or "rhombus" not in (decision.get("style") or ""):
            continue
        outgoing = [e for e in cells if e.get("edge") == "1" and e.get("source") == decision.get("id")]
        if len(outgoing) != 2:
            continue
        first, second = outgoing
        a, b = style_map(first.get("style")), style_map(second.get("style"))
        for key in ("exitX", "exitY"):
            if not a.get(key) or a.get(key) != b.get(key):
                findings.append(f"{decision.get('id')}: two branches need the same explicit {key}")
        for key in BRANCH_KEYS:
            if a.get(key) != b.get(key):
                findings.append(f"{decision.get('id')}: two branches differ in {key}")
        if a.get("edgeStyle") != "orthogonalEdgeStyle":
            findings.append(f"{decision.get('id')}: two branches should use orthogonalEdgeStyle")
        wp_a, wp_b = first_waypoint(first), first_waypoint(second)
        if wp_a is None or wp_a != wp_b:
            findings.append(f"{decision.get('id')}: two branches need the same first waypoint")
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagram", help="Uncompressed .drawio XML file")
    args = parser.parse_args()
    try:
        findings = inspect(args.diagram)
    except (OSError, ET.ParseError) as exc:
        parser.error(str(exc))
    for finding in findings:
        print("error:", finding)
    print(f"{len(findings)} convention error(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
