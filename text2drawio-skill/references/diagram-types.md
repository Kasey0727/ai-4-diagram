# Black-and-white flowchart and vertical swimlane conventions

Adapted from the "Cross-Functional Flowchart (Swimlane)" and "Flowchart (enhanced)" sections of upstream `references/diagram-types.md` at commit `6550495129d9a42eff7e71434d15bfc9846b6202`.

## Cross-functional flowchart (swimlane)

A flowchart split by **who does what** — one vertical column per role, department, or system. Columns run left to right; the sequence runs top to bottom. Use the flowchart node vocabulary below.

| Element | Style | Notes |
| --- | --- | --- |
| Pool (process) | `swimlane;html=1;horizontal=1;startSize=40;collapsible=0;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;` | Outer container; process title across the top |
| Lane (participant) | `swimlane;html=1;horizontal=1;startSize=40;collapsible=0;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;` | Child of pool; one tall side-by-side column per system, with a horizontal header at the top |
| Steps | Flowchart styles below | Step `parent` = lane ID; coordinates relative to lane |
| Handoff edge | `edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;fontColor=#000000;endArrow=block;` | Connects steps across columns |
| Layout | Top to bottom sequence | Keep steps inside their system's column; leave clear horizontal corridors for cross-system edges |

Create lane geometries with the same `y` and `height`, and make every pair touch exactly: `next.x = current.x + current.width` in pool-relative coordinates. For example, three 300 px wide lanes start at x = 0, 300, and 600. Do not add a gutter between columns; keep spacing inside the lane around its nodes. The visible header band is at the top of each column. `scripts/normalize_geometry.py` can fill accidental gaps by extending the left lane without moving its children or any edge waypoint.

For a direct horizontal handoff, use right/left side ports at the same **absolute y**; for a direct vertical edge, use bottom/top ports at the same **absolute x**. Pin all four port fractions explicitly and do not add waypoints to an intended straight line. When node centers differ slightly, compute both fractional ports from one shared coordinate, rather than rounding `exitY` and `entryY` (or `exitX` and `entryX`) independently. Keep ellipse/cylinder endpoints at the side center (`0.5`) because draw.io projects off-center ports onto their curved perimeter. The normalizer fills missing ports and snaps small mismatches up to 24 px only when the resulting ports remain away from shape corners; larger detours still need explicit routing or node alignment.

## Flowchart nodes

| Element | Style | Notes |
| --- | --- | --- |
| Start/End | `ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;` | White oval |
| Process | `rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;` | White rectangle |
| Decision | `rhombus;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;` | White diamond |
| I/O | `shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;` | White parallelogram |
| Subprocess | `rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;` plus double border | White rectangle |
| Exception step | `rounded=0;whiteSpace=wrap;html=1;fillColor=#000000;strokeColor=#000000;fontColor=#FFFFFF;` | Optional black fill for emphasis; keep label legible |
| Yes/No branches | `value="是"` / `value="否"` on edges | Same source port, same orthogonal line style and black stroke; branch from a common stem |

For a two-way decision, both edges should use the same `exitX` and `exitY` and the same first waypoint. Use further waypoints to form symmetric right-angle turns to their respective targets. Keep the labels on the two diverging arms, close to the split. If the physical branches require different attachment points to avoid collisions, use one decision-to-junction edge and connect both labeled alternatives from a small junction node instead of silently giving the two branches different ports.
