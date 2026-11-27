---
name: text2drawio-skill
description: Turn natural-language requirements into editable native .drawio system interaction diagrams, then build a fixed HTML/SVG viewer for XTeam preview and file-backed edits. Use vertical swimlane columns, black-and-white diagrams, consistent decision branches, structural validation, and PNG visual review.
---

# Natural language to editable draw.io

`text2drawio-skill` is adapted from Agents365-ai/drawio-skill at commit `6550495129d9a42eff7e71434d15bfc9846b6202` (MIT; see `LICENSE`). The agent plans and writes native diagram XML. Scripts validate/export it, render a fixed viewer template, and persist browser edits. They do not interpret natural language or inspect pixels on their own.

## Requirements

- Python 3 for the bundled scripts.
- For SVG/PNG export, use the draw.io desktop CLI when installed. Otherwise `scripts/render_svg.py` uses the official diagrams.net viewer and headless Chromium; it needs browser access to `viewer.diagrams.net`. The browser search checks PATH's `chrome-headless-shell` before PATH's Chromium/Chrome, and XTeam's headless-shell path before its full Chrome path. XTeam reported a 90-second `--dump-dom` timeout with its full Chrome build, while its headless shell rendered successfully. `DRAWIO_CHROMIUM` can point to a nonstandard executable. A previously rendered SVG may be supplied to `build_preview.py --svg` only when it corresponds to the final XML. If neither renderer works, provide the validated `.drawio` and state that visual self-review could not run.
- Graphviz `dot` only if using optional `scripts/autolayout.py` for a large generic graph. Its grouped layout is not a substitute for hand-authored swimlane containment.
- An image viewing capability in the host agent to inspect the exported PNG. Never claim visual review or repair if the host cannot read the PNG.

## Create

1. Extract the participants, actions, order, conditions, exception paths, and requested diagram type. Keep assumptions and unanswered questions visible in the response. For a system interaction swimlane, use one **vertical column** per participating system; time flows top to bottom. Put each step inside the column of the system performing it.
2. Read the compact [swimlane quickstart](references/swimlane-quickstart.md) before writing native XML. Read [diagram-types.md](references/diagram-types.md) or [xml-authoring.md](references/xml-authoring.md) only when the request needs a nonstandard shape or complex routing; do not reread unchanged references in the same conversation. Plan positions, container nesting, connection ports, and routing corridors. Use only `#000000` and `#FFFFFF` for every fill, stroke, font, background, and label color. Avoid transparency, named colors, gray, and gradients. For a large non-swimlane graph, optionally describe nodes/edges as JSON and use `python3 scripts/autolayout.py graph.json -o diagram.drawio` if Graphviz is installed.
3. Write an uncompressed `output/diagram.drawio` file with `<mxfile>`, `<mxGraphModel>`, root cells `0` and `1`, stable unique cell IDs, `mxGeometry` for each shape and edge, and source/target IDs for connections. Set `fillColor`, `strokeColor`, and `fontColor` explicitly on every vertex, and set black `strokeColor` on every edge. Keep labels short enough to fit. Use relative coordinates for child cells inside lanes.
4. For each decision with two alternatives, place both outgoing edges at the **same exact port** on the decision cell. Give them the same `edgeStyle`, `rounded`, `strokeWidth`, `strokeColor`, and arrow settings. Prefer a short shared stem to one branching point, then explicit orthogonal waypoints to the two targets; label the diverging arms `是` and `否` near the split. Distinguish outcomes by text, shape, or black fill with white text, not a different line color or type.
5. Run `python3 scripts/normalize_geometry.py output/diagram.drawio --in-place`, then `python3 scripts/validate.py output/diagram.drawio --score` and `python3 scripts/check_conventions.py output/diagram.drawio`. The normalizer fills gaps between sibling lanes without moving nodes and snaps only near-straight, waypoint-free edge ports; inspect its change list. Fix remaining errors before preview. `build_preview.py` repeats this gate so a missed command cannot deliver a diagram with these defects. Treat geometry warnings as review prompts: draw.io computes many edge paths only at render time.
6. Put `diagram.drawio` in the intended output directory, then build the HTML/SVG and a PNG for visual review in one command. The PNG is captured from the same SVG; do not separately run `export_png.py` in this workflow. Keep generated content in XML and optional assumptions/questions JSON; never author a one-off HTML page. For example:

   ```bash
   python3 scripts/build_preview.py output/diagram.drawio --output-dir output --title "系统交互图" --review-png
   ```

   Add `--notes-json output/notes.json` when providing assumptions and open questions in the viewer; the JSON has `assumptions` and `questions` string arrays. The build produces `diagram.drawio`, `diagram.preview.svg`, `diagram.preview.png`, and `diagram.html`.
7. Open the returned PNG with the host's image viewing tool. Check lane orientation, pure black-and-white palette, branch junction and labels, overlapping shapes, clipped text, and edges crossing unrelated shapes. If multiple edges stack at a node boundary, run `python3 scripts/edgeports.py` on the `.drawio`, then rerun steps 5–7; it preserves manually pinned decision ports. If defects remain, edit the XML and rerun steps 5–7. Make at most **two automatic visual repair rounds** after the initial draft. Report remaining defects plainly. Never claim visual review if the host cannot read the PNG.
8. Read [XTeam delivery](references/xteam-delivery.md) for hosting and writeback, then show the preview and editable `.drawio` to the user. Apply up to **five user-feedback rounds** in the current creation cycle. For each round, change only affected cells where practical, then validate, rebuild once, and review again. Keep the round count in the conversation; no bundled script enforces it. After the fifth round, deliver the latest file and describe any remaining requested refinement.

The `.drawio` XML is the editable source of truth. The PNG is for agent review. The SVG/HTML pair is the fixed-code user preview. Browser edits must be POSTed to the workspace service before reporting that they were saved.
