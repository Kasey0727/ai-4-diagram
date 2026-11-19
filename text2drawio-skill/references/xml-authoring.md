# Authoring .drawio XML

Read this **before hand-writing any `.drawio` XML**. Skip it when the bundled `autolayout.py` writes the XML for a large generic graph.

### File skeleton

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="drawio" version="26.0.0">
  <diagram name="Page-1">
    <mxGraphModel>
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- user shapes start at id="2" -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**Rules:**

- `id="0"` and `id="1"` are required root cells — never omit them
- User shapes start at `id="2"` and increment sequentially
- All shapes have `parent="1"` (unless inside a container — then use container's id)
- All text uses `html=1` in style for proper rendering
- **Never use `--` inside XML comments** — it's illegal per XML spec and causes parse errors
- Escape special characters in attribute values: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- **Multi-line text in labels:** use `&#xa;` for line breaks inside `value` attributes (not literal `\n`). Example: `value="Line 1&#xa;Line 2"`

### SVG text labels

For diagrams destined for web output (including GitHub-rendered SVGs, HTML viewers, or slides rendered as SVG), add `convertToSvg=1;` to each text-bearing cell's style, for example `style="rounded=1;whiteSpace=wrap;html=1;convertToSvg=1;"`. This draw.io 28.0.3+ per-cell setting exports convertible labels as selectable, searchable SVG text instead of raster fallbacks. It is not an export-command switch; generic export commands need no change.

Some content cannot be converted and remains HTML/raster: tables, lists, links, images, cells with `background-color`, and vertical writing. SVG text has no automatic word wrapping; line breaks are fixed at export, so re-export after resizing a shape or lengthening a label. Word-wrapped SVG text requires draw.io 29.6.7 or later.

### Shape types (vertex)

| Style keyword | Use for |
| -------------- | --------- |
| `rounded=0` | plain rectangle (default) |
| `rounded=1` | rounded rectangle — services, modules |
| `ellipse;` | circles/ovals — start/end, databases |
| `rhombus;` | diamond — decision points |
| `shape=mxgraph.aws4.resourceIcon;` | AWS icons |
| `shape=cylinder3;` | cylinder — databases |
| `swimlane;` | group/container with title bar |

For non-trivial shapes, verify that draw.io supports the chosen `shape=mxgraph.*` name. An unknown name can render as a blank box. This focused Skill does not bundle the upstream icon search tools.

### Required properties

```xml
<!-- Rectangle / rounded box -->
<mxCell id="2" value="Label" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="160" height="60" as="geometry" />
</mxCell>

<!-- Cylinder (database) -->
<mxCell id="3" value="DB" style="shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;" vertex="1" parent="1">
  <mxGeometry x="350" y="100" width="120" height="80" as="geometry" />
</mxCell>

<!-- Diamond (decision) -->
<mxCell id="4" value="Check?" style="rhombus;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;" vertex="1" parent="1">
  <mxGeometry x="100" y="220" width="160" height="80" as="geometry" />
</mxCell>
```

### Containers and groups

For architecture diagrams with nested elements, use draw.io's parent-child containment — do **not** just place shapes on top of larger shapes.

| Type | Style | When to use |
| ------ | ------- | ------------- |
| **Group** (invisible) | `group;pointerEvents=0;` | No visual border needed, container has no connections |
| **Swimlane** (titled) | `swimlane;startSize=30;` | Container needs a visible title bar, or container itself has connections |
| **Custom container** | Add `container=1;pointerEvents=0;` to any shape | Any shape acting as a container without its own connections |

**Key rules:**

- Add `pointerEvents=0;` to container styles that should not capture connections between children
- Children set `parent="containerId"` and use coordinates **relative to the container**

```xml
<!-- Swimlane container -->
<mxCell id="svc1" value="User Service" style="swimlane;startSize=30;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="300" height="200" as="geometry"/>
</mxCell>
<!-- Child inside container — coordinates relative to parent -->
<mxCell id="api1" value="REST API" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;" vertex="1" parent="svc1">
  <mxGeometry x="20" y="40" width="120" height="60" as="geometry"/>
</mxCell>
<mxCell id="db1" value="Database" style="shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;" vertex="1" parent="svc1">
  <mxGeometry x="160" y="40" width="120" height="60" as="geometry"/>
</mxCell>
```

### Connector (edge)

**CRITICAL:** Every edge `mxCell` must contain a `<mxGeometry relative="1" as="geometry" />` child element. Self-closing edge cells (`<mxCell ... edge="1" ... />`) are **invalid** and will not render. Always use the expanded form.

```xml
<!-- Directed arrow — always include rounded, orthogonalLoop, jettySize for clean routing -->
<mxCell id="10" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;" edge="1" parent="1" source="2" target="3">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- Arrow with label + explicit entry/exit points to control direction -->
<mxCell id="11" value="HTTP/REST" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;fontColor=#000000;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" parent="1" source="2" target="4">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- Arrow with waypoints — use when edge must route around other shapes -->
<mxCell id="12" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;" edge="1" parent="1" source="3" target="5">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="500" y="50" />
    </Array>
  </mxGeometry>
</mxCell>
```

**Edge style rules:**

- **Animated connectors:** add `flowAnimation=1;` to any edge style to show a moving dot animation along the arrow. Works in SVG export and draw.io desktop — ideal for data-flow and pipeline diagrams. Example: `style="edgeStyle=orthogonalEdgeStyle;flowAnimation=1;rounded=1;..."`
- **Always** include `rounded=1;orthogonalLoop=1;jettySize=auto` — these enable smart routing that avoids overlaps
- Pin `exitX/exitY/entryX/entryY` on every edge when a node has 2+ connections — distributes lines across the shape perimeter. `scripts/edgeports.py <file>` does this for a whole diagram: it picks the side facing each peer and spreads that side's edges over even slots ordered by the far endpoint, so they don't stack or cross at the boundary. It skips ends you pinned by hand and is idempotent
- Add `<Array as="points">` waypoints when an edge must detour around an intermediate shape
- **Leave room for arrowheads:** the final straight segment between the last bend and the target shape must be ≥20px long. If too short, the arrowhead overlaps the bend and looks broken. Fix by increasing node spacing or adding explicit waypoints
- **libavoid obstacle-avoiding routing (editor-side, draw.io ≥ 30):** draw.io can reroute connectors around shapes in the desktop editor. It is not a headless CLI flag. For CLI-authored files keep the orthogonal rules above; if a dense diagram still has crossings after export, open the `.drawio` in draw.io desktop and reroute it there.

### Distributing connections on a shape

When multiple edges connect to the same shape, assign different entry/exit points to prevent stacking:

| Position | exitX/entryX | exitY/entryY | Use when |
| ---------- | ------------- | ------------- | ---------- |
| Top center | 0.5 | 0 | connecting to node above |
| Top-left | 0.25 | 0 | 2nd connection from top |
| Top-right | 0.75 | 0 | 3rd connection from top |
| Right center | 1 | 0.5 | connecting to node on right |
| Bottom center | 0.5 | 1 | connecting to node below |
| Left center | 0 | 0.5 | connecting to node on left |

**Rule:** if a shape has N connections on one side, space them evenly (e.g., 3 connections on bottom → exitX = 0.25, 0.5, 0.75)

### Black-and-white palette (fillColor / strokeColor)

Use exactly `#000000` and `#FFFFFF` for explicit colors. Keep all edge strokes black; use node shape and labels to distinguish outcomes. White fills with black text are the default. An exception node may use black fill with white text.

| Role | fillColor | strokeColor | fontColor |
| --- | --- | --- | --- |
| Start/end, process, decision | `#FFFFFF` | `#000000` | `#000000` |
| Exception process, when emphasized | `#000000` | `#000000` | `#FFFFFF` |
| Lane background | `#FFFFFF` | `#000000` | `#000000` |
| Edges and edge labels | — | `#000000` | `#000000` |

### Legend

Avoid a color legend. Use shape and text labels to explain outcomes. Add a legend only if the diagram introduces another visual convention that a reader cannot infer from the labels.

### Layout tips

**Spacing — scale with complexity:**

| Diagram complexity | Nodes | Horizontal gap | Vertical gap |
| ------------------- | ------- | ---------------- | -------------- |
| Simple | ≤5 | 200px | 150px |
| Medium | 6–10 | 280px | 200px |
| Complex | >10 | 350px | 250px |

**Routing corridors:** between shape rows/columns, leave an extra ~80px empty corridor where edges can route without crossing shapes. Never place a shape in a gap that edges need to traverse.

**Grid alignment:** snap all `x`, `y`, `width`, `height` values to **multiples of 10** — this ensures shapes align cleanly on draw.io's default grid and makes manual editing easier.

**General rules:**

- Plan a grid before assigning x/y coordinates — sketch node positions on paper/mentally first
- Group related nodes in the same horizontal or vertical band
- Use `swimlane` cells for logical grouping with visible borders
- Place heavily-connected "hub" nodes centrally so edges radiate outward instead of crossing
- To force straight vertical connections, pin entry/exit points explicitly on edges:
  `exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0`
- Always center-align a child node under its parent (same center x) to avoid diagonal routing
- **Event bus pattern**: place Kafka/bus nodes in the **center of the service row**, not below — services on either side can reach it with short horizontal arrows (`exitX=1` left side, `exitX=0` right side), eliminating all line crossings
- Horizontal connections (`exitX=1` or `exitX=0`) never cross vertical nodes in the same row; use them for peer-to-peer and publish connections

**Avoiding edge-shape overlap:**

- Before finalizing coordinates, trace each edge path mentally — if it must cross an unrelated shape, either move the shape or add waypoints
- For tree/hierarchical layouts: assign nodes to layers (rows), connect only between adjacent layers to minimize crossings
- For star/hub layouts: place the hub center, satellites around it — edges stay short and radial
- When an edge must span multiple rows/columns, route it along the outer corridor, not through the middle of the diagram

### Decision-diamond branches, pixel-exact pins, and labels

Pitfalls verified from rendered output. `validate.py` does not catch any of them, and vision review both misses them and hallucinates new ones (it once described a clean diamond exit as "wrapping around the box" and approved a screenshot that was actually the browser error page).

| Pitfall | Rule |
| ------- | ---- |
| Decision branches leave from different diamond points or use different line types | For a two-way decision, pin both edges to the same exact port (usually bottom center for top-to-bottom flow), use the same orthogonal edge style, and give them the same first waypoint to form one short shared stem. Split to the two targets with explicit right-angle waypoints. Put `是` and `否` on the diverging arms. If this geometry would cross another shape, add a small junction node rather than changing only one branch to a diagonal line. |
| Vertical edge whose `entryX` is 1–2 px off the source's exit x (easy to hit when boxes snap to a 10 px grid) | Compute the pin with full precision: `entryX = (sourceCenterX − target.x) / target.width`, e.g. `0.0652`, `0.2027`. Style values accept more than two decimals. A 1–2 px mismatch renders as an S-shaped double curve (two `Q` bends) just before the arrowhead. |
| `blockThin` arrowheads (~5×7 px) flush against the target border | Reviewers read the tip as "piercing the box". Use `endArrow=block;endSize=8` for main flow edges. |
| Long labels auto-centered on their own edge | The white label chip visually severs the edge, and near a corner it can cut both segments. Keep only micro-labels (`Yes` / `No`) on the line; offset longer labels (`<mxPoint as="offset" x="…" y="…"/>`) into verified empty space, and shorten any label wider than the corridor it annotates. |
| Trusting "it looks fine" | Inspect the exported PNG and, when possible, the renderer's actual edge paths and label anchors. Visual review can miss or imagine routing defects. |
