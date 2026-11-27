#!/usr/bin/env python3
"""Close vertical-lane gaps and snap safe near-straight edge ports."""

import argparse
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

from check_conventions import lane_gaps, near_straight_edges, nonrectangular


def number(value):
    return format(value, ".6f").rstrip("0").rstrip(".")


def set_style_values(style, updates):
    parts = (style or "").split(";")
    found = set()
    for index, part in enumerate(parts):
        if "=" not in part:
            continue
        key = part.split("=", 1)[0]
        if key in updates:
            parts[index] = f"{key}={updates[key]}"
            found.add(key)
    for key, value in updates.items():
        if key not in found:
            parts.insert(-1 if parts[-1] == "" else len(parts), f"{key}={value}")
    return ";".join(parts)


def normalize(tree):
    cells = tree.getroot().findall(".//mxCell")
    changes, unresolved = [], []
    for left, right, gap, width in lane_gaps(cells):
        left.find("mxGeometry").set("width", number(width))
        changes.append(f"{left.get('id')}: width {number(width)} (closed {number(gap)}px gap before {right.get('id')})")
    for edge, direction, offset, shared, source_box, target_box, source, target in near_straight_edges(cells):
        sx, sy, sw, sh = source_box
        tx, ty, tw, th = target_box
        source_nonrect, target_nonrect = nonrectangular(source), nonrectangular(target)
        if source_nonrect and target_nonrect:
            source_center = sy + sh / 2 if direction == "horizontal" else sx + sw / 2
            target_center = ty + th / 2 if direction == "horizontal" else tx + tw / 2
            if abs(source_center - target_center) > 0.5:
                unresolved.append(f"{edge.get('id')}: align the two non-rectangular nodes before using a straight edge")
                continue
            shared = (source_center + target_center) / 2
        elif source_nonrect:
            shared = sy + sh / 2 if direction == "horizontal" else sx + sw / 2
        elif target_nonrect:
            shared = ty + th / 2 if direction == "horizontal" else tx + tw / 2
        if direction == "horizontal":
            fractions = ((shared - sy) / sh, (shared - ty) / th)
            updates = {"exitX": "1" if sx < tx else "0",
                       "entryX": "0" if sx < tx else "1",
                       "exitY": number(fractions[0]), "entryY": number(fractions[1])}
        else:
            fractions = ((shared - sx) / sw, (shared - tx) / tw)
            updates = {"exitY": "1" if sy < ty else "0",
                       "entryY": "0" if sy < ty else "1",
                       "exitX": number(fractions[0]), "entryX": number(fractions[1])}
        if not all(0.2 <= value <= 0.8 for value in fractions):
            unresolved.append(f"{edge.get('id')}: near-{direction} {number(offset)}px offset needs node alignment")
            continue
        updates.update({"exitDx": "0", "exitDy": "0", "entryDx": "0", "entryDy": "0"})
        edge.set("style", set_style_values(edge.get("style"), updates))
        changes.append(f"{edge.get('id')}: snapped {direction} ports ({number(offset)}px offset)")
    return changes, unresolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diagram", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--in-place", action="store_true")
    group.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    try:
        tree = ET.parse(args.diagram)
        changes, unresolved = normalize(tree)
        output = args.diagram if args.in_place else args.output
        if changes:
            output.parent.mkdir(parents=True, exist_ok=True)
            tree.write(output, encoding="utf-8", xml_declaration=True)
        elif output != args.diagram:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.diagram, output)
    except (OSError, ET.ParseError) as exc:
        parser.error(str(exc))
    for item in changes:
        print("fixed:", item)
    for item in unresolved:
        print("review:", item)
    print(f"{len(changes)} fixed, {len(unresolved)} need manual review; output: {output}")
    return 1 if unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
