# Grayscale flowchart and vertical swimlane conventions

Adapted from the "Cross-Functional Flowchart (Swimlane)" and "Flowchart (enhanced)" sections of upstream `references/diagram-types.md` at commit `6550495129d9a42eff7e71434d15bfc9846b6202`.

## Cross-functional flowchart (swimlane)

A flowchart split by **who does what** — one vertical column per role, department, or system. Columns run left to right; the sequence runs top to bottom. Use the flowchart node vocabulary below.

| Element | Style | Notes |
| --- | --- | --- |
| Pool (process) | `swimlane;html=1;horizontal=1;startSize=40;collapsible=0;fillColor=#ffffff;strokeColor=#666666;` | Outer container; process title across the top |
| Lane (participant) | `swimlane;html=1;horizontal=1;startSize=40;collapsible=0;fillColor=#fafafa;strokeColor=#aaaaaa;` | Child of pool; one tall side-by-side column per system, with a horizontal header at the top |
| Steps | Flowchart styles below | Step `parent` = lane ID; coordinates relative to lane |
| Handoff edge | `edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#555555;endArrow=block;` | Connects steps across columns |
| Layout | Top to bottom sequence | Keep steps inside their system's column; leave clear horizontal corridors for cross-system edges |

Create lane geometries with the same `y` and `height`, distinct `x` values, and no horizontal overlap. For example, three 300 px wide lanes can start at x = 0, 300, and 600 relative to the pool. The visible header band is at the top of each column.

## Flowchart nodes

| Element | Style | Notes |
| --- | --- | --- |
| Start/End | `ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#555555;` | White oval |
| Process | `rounded=0;whiteSpace=wrap;html=1;fillColor=#f2f2f2;strokeColor=#555555;` | Light gray rectangle |
| Decision | `rhombus;whiteSpace=wrap;html=1;fillColor=#e6e6e6;strokeColor=#444444;` | Medium gray diamond |
| I/O | `shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fillColor=#f2f2f2;strokeColor=#555555;` | Light gray parallelogram |
| Subprocess | `rounded=0;whiteSpace=wrap;html=1;fillColor=#e6e6e6;strokeColor=#555555;` plus double border | Medium gray rectangle |
| Yes/No branches | `value="是"` / `value="否"` on edges | Same source port, same orthogonal line style and gray stroke; branch from a common stem |

For a two-way decision, both edges should use the same `exitX` and `exitY` and the same first waypoint. Use further waypoints to form symmetric right-angle turns to their respective targets. Keep the labels on the two diverging arms, close to the split. If the physical branches require different attachment points to avoid collisions, use one decision-to-junction edge and connect both labeled alternatives from a small junction node instead of silently giving the two branches different ports.
