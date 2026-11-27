# 竖向系统交互泳道图：常规建图速查

原生、未压缩 `.drawio`：`mxfile > diagram > mxGraphModel > root`；根单元为 `id="0"` 和 `id="1" parent="0"`。外层 pool 的 `parent="1"`，每条系统泳道的 `parent` 为 pool ID，步骤的 `parent` 为所在泳道 ID，连线的 `parent="1"`，并填写 `source`、`target`。每个单元有稳定唯一 ID 和 `mxGeometry`。

## 泳道与布局

- pool 与泳道样式：`swimlane;html=1;horizontal=1;startSize=40;collapsible=0;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;`
- 所有泳道同一 `y` 和 `height`；按参与系统顺序从左到右，严格满足 `next.x = current.x + current.width`，没有列间空隙。pool 标题高 40，子泳道通常从 `y=40` 开始。
- 时间从上到下。节点放在执行动作的泳道内，坐标相对该泳道；留足标签空间和跨泳道连线走廊。

## 节点与连线

- 普通步骤：`rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#000000;fontColor=#000000;`；起止用 `ellipse`，判断用 `rhombus`，仍显式设置上述三种颜色。
- 连线：`edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;fontColor=#000000;endArrow=block;endSize=8;`；有文字再加 `fontColor=#000000`。
- 每条边用 `exitX/exitY/entryX/entryY` 指定端口。直线不加折点：水平边接左右侧且两端绝对 y 相等；竖直边接上下侧且两端绝对 x 相等。椭圆、圆柱的连接点留在边侧中点 `0.5`，另一端按绝对坐标反算端口比例。
- 需要绕障碍时才写 `<Array as="points"><mxPoint x="…" y="…"/></Array>`。两分支判断共用同一出口和第一个折点，并保持相同线型；分支文字靠近分叉。

生成后先运行 `normalize_geometry.py`、`validate.py`、`check_conventions.py`。详细形状和复杂走线规则见 `diagram-types.md`、`xml-authoring.md`。
