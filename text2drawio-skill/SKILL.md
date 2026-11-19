---
name: text2drawio-skill
description: Turn a natural-language request into an editable native .drawio flowchart or system interaction diagram. Use vertical swimlane columns, only black and white, consistent decision branches, structural validation, and PNG visual review.
---

# Natural language to editable draw.io

`text2drawio-skill` is adapted from Agents365-ai/drawio-skill at commit `6550495129d9a42eff7e71434d15bfc9846b6202` (MIT; see `LICENSE`). Its original Python helpers are retained, with local black-and-white defaults in `autolayout.py`. `export_png.py` and `check_conventions.py` are local helpers. The agent plans and writes the diagram; these scripts do not interpret natural language or inspect pixels on their own.

## Requirements

- Python 3 for the bundled scripts.
- draw.io desktop CLI for PNG export. `scripts/drawio_cli.py` resolves common executable names and install paths. If unavailable, provide the validated `.drawio` and state that visual self-review could not run.
- Graphviz `dot` only if using optional `scripts/autolayout.py` for a large generic graph. Its grouped layout is not a substitute for hand-authored swimlane containment.
- An image viewing capability in the host agent to inspect the exported PNG. Never claim visual review or repair if the host cannot read the PNG.

## Create

1. Extract the participants, actions, order, conditions, exception paths, and requested diagram type. Keep assumptions and unanswered questions visible in the response. For a system interaction swimlane, use one **vertical column** per participating system; time flows top to bottom. Put each step inside the column of the system performing it.
2. Read [diagram-types.md](references/diagram-types.md) for vertical swimlanes and [xml-authoring.md](references/xml-authoring.md) before writing native XML. Plan positions, container nesting, connection ports, and routing corridors. Use only `#000000` and `#FFFFFF` for every fill, stroke, font, background, and label color. Avoid transparency, named colors, gray, and gradients. For a large non-swimlane graph, optionally describe nodes/edges as JSON and use `python3 scripts/autolayout.py graph.json -o diagram.drawio` if Graphviz is installed.
3. Write an uncompressed `.drawio` file with `<mxfile>`, `<mxGraphModel>`, root cells `0` and `1`, stable unique cell IDs, `mxGeometry` for each shape and edge, and source/target IDs for connections. Set `fillColor`, `strokeColor`, and `fontColor` explicitly on every vertex, and set black `strokeColor` on every edge. Keep labels short enough to fit. Use relative coordinates for child cells inside lanes.
4. For each decision with two alternatives, place both outgoing edges at the **same exact port** on the decision cell. Give them the same `edgeStyle`, `rounded`, `strokeWidth`, `strokeColor`, and arrow settings. Prefer a short shared stem to one branching point, then explicit orthogonal waypoints to the two targets; label the diverging arms `是` and `否` near the split. Distinguish outcomes by text, shape, or black fill with white text, not a different line color or type.
5. Run `python3 scripts/validate.py diagram.drawio --score` and `python3 scripts/check_conventions.py diagram.drawio`. Fix errors before preview. Treat geometry warnings as review prompts: draw.io computes many edge paths only at render time.
6. Run `python3 scripts/export_png.py diagram.drawio -o diagram.preview.png` to export a draft without embedded XML. Open the PNG with the host's image viewing tool and check lane orientation, pure black-and-white palette, the branch junction and labels, overlapping shapes, clipped text, and edges crossing unrelated shapes. If multiple edges stack at a node boundary, run `python3 scripts/edgeports.py diagram.drawio -o diagram.routed.drawio`, then inspect the result. Do not run it on a deliberately shared decision port; it preserves manually pinned ports.
7. If defects remain, edit the XML, validate, export, and inspect again. Make at most **two automatic visual repair rounds** after the initial draft. Report any remaining defects plainly. If PNG export or image inspection is unavailable, do not silently count the missing check as successful.
8. Show the preview and editable `.drawio` to the user. Apply up to **five user-feedback rounds** in the current creation cycle. For each round, change only affected cells where practical, then validate and preview again. Keep the round count in the conversation; no bundled script enforces it. After the fifth round, deliver the latest file and describe any remaining requested refinement.

The `.drawio` XML is the editable deliverable. The preview PNG is for review. Do not present an exported PNG as the only editable source.
