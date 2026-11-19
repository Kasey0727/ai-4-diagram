#!/usr/bin/env python3
"""Check grayscale, vertical swimlanes, and consistent two-way decision edges."""

import argparse
import re
import sys
import xml.etree.ElementTree as ET


HEX_COLOR = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")
BRANCH_KEYS = ("edgeStyle", "rounded", "orthogonalLoop", "jettySize",
               "strokeColor", "strokeWidth", "endArrow", "endSize")


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


def is_gray(hex_value):
    if len(hex_value) == 3:
        channels = [int(c * 2, 16) for c in hex_value]
    else:
        channels = [int(hex_value[i:i + 2], 16) for i in (0, 2, 4)]
    return len(set(channels)) == 1


def inspect(path):
    root = ET.parse(path).getroot()
    cells = root.findall(".//mxCell")
    findings = []

    for cell in cells:
        for color in HEX_COLOR.findall(cell.get("style") or ""):
            if not is_gray(color):
                findings.append(f"{cell.get('id')}: non-grayscale style color #{color}")

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
