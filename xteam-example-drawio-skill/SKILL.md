---
name: drawio-diagram
description: "生成可交互的流程图/架构图画布与可编辑 .drawio 文件。用户要求画流程图、时序图、架构图、状态机、泳道图，或提到 drawio / diagrams.net / 画布 / 图，或使用 /drawio-diagram 时使用。输出两项：工作区内的 .drawio 源文件（可在 draw.io 打开继续编辑），以及同名的 .html 交互画布（可缩放、平移、并直接下载 .drawio）。"
when_to_use: |
  Use when the user wants a flow chart, architecture diagram, state machine, or explicitly mentions drawio / diagrams.net / a canvas, or invokes /drawio-diagram.
  中文适用场景：画流程图、画架构图、画状态机、画业务流程、要一份能继续编辑的 drawio 文件、要在对话里直接看可缩放的图。
  中文触发示例：“画一个登录流程图”“把这段流程画成图”“生成 drawio 文件”“来个架构图”“画个状态机”“这个流程可视化一下”。
  不适用：纯 UI 设计稿或网页原型（用 ui-design）；需要真实前端工程代码（用 ui-design-app）；统计图表（柱状图/折线图/饼图）。
user-invocable: true
allowed-tools: Read Write Edit Glob Grep Bash
---

# Drawio 流程图交付

一次交付同时满足两件事：

1. 工作区里存在 `*.drawio` 源文件 —— 用户下载后能在 draw.io / diagrams.net 里继续编辑。
2. 同一个目录下存在同名 `*.html` —— 可缩放、可拖拽的真实画布，并且画布上的按钮能直接把 `.drawio` 下载下来。

这两件事不是可选项。只在回复里贴 ASCII 图、只给 mermaid 代码、或只给一张静态 PNG，都不算完成。

## 为什么必须两个文件

`.drawio` 是交付物本身，`.html` 是查看入口。对话正文里的 Markdown 会被清洗，直接写 `<iframe>` 或内联脚本不会渲染成可交互画布；XTeam 只对「工作区里的 HTML 文件」提供 iframe 预览。所以画布必须是真实文件，不能是回复正文里的片段。

## 执行流程

### 第 1 步：把需求转成 spec

先把用户描述的流程结构化，不要直接拼 XML。写一个 JSON spec 到临时文件，例如 `./.drawio-spec.json`：

```json
{
  "title": "登录鉴权流程",
  "direction": "TB",
  "nodes": [
    { "id": "start", "label": "用户点击登录", "type": "start" },
    { "id": "check", "label": "校验验证码", "type": "decision" },
    { "id": "ok", "label": "进入首页", "type": "end" }
  ],
  "edges": [
    { "from": "start", "to": "check" },
    { "from": "check", "to": "ok", "label": "通过", "style": "success" }
  ]
}
```

节点类型（`type`）与适用语义：

| type | 形状 | 用在哪里 |
|---|---|---|
| `start` | 圆形 | 流程入口 |
| `end` | 圆形 | 流程终点、结果态 |
| `process` | 圆角矩形 | 一般处理步骤 |
| `subprocess` | 双边矩形 | 子流程、外部系统调用 |
| `decision` | 菱形 | 条件判断，必须带分支标签 |
| `data` | 平行四边形 | 输入输出数据 |
| `db` | 圆柱 | 数据库、存储 |
| `doc` | 文档形 | 单据、流水、凭证 |
| `note` | 便签 | 旁注、待确认项 |

连线样式（`style`）：`default` 灰、`success` 绿、`danger` 红、`muted` 浅灰。回退/重试类连线加 `"dashed": true`。

排版由脚本负责，不要手工算坐标。只有确实需要覆盖时，才给节点加 `"x"` / `"y"`。

### 第 2 步：生成两个文件

```bash
python3 <skill>/scripts/build_drawio.py .drawio-spec.json --out <目标目录>
```

脚本用 `Path(__file__)` 定位模板，用绝对路径调用即可，不需要先 cd。输出一行 JSON，含 `drawio` 与 `html` 两个绝对路径。

生成后删掉临时 spec 文件，不要留在工作区。

### 第 3 步：交付

告诉用户文件位置和标题，然后给预览卡片。画布 HTML 已在工作区，属于静态文件，用应用预览的方式启动服务即可（见 `references/delivery.md`）。

## 渲染引擎怎么选

脚本默认 `--engine svg`：把图直接渲染成内联 SVG，零外部依赖，内网环境也能显示。用户明确要求「和 draw.io 里长得一模一样」时，再改 `--engine drawio`，走 diagrams.net 官方 viewer（依赖外网 CDN，内网会白屏）。

无论哪个引擎，`.drawio` 文件完全一致 —— 引擎只影响画布这一侧的渲染方式。

## 已有 drawio 文件补画布

用户手上已经有 `.drawio`：

```bash
python3 <skill>/scripts/build_drawio.py --wrap path/to/file.drawio --out <目标目录>
```

`--wrap` 会校验文件结构并生成同名 `.html`。注意该模式下的 SVG 渲染只识别常见形状与颜色，遇到泳道、容器、自定义 stencil 这类复杂结构时，改用 `--engine drawio` 才能保证视觉一致。

## 硬性约束

- **不要在回复正文里贴完整 HTML**。文件才是交付物。
- **不要只做一个文件**。`.drawio` 和 `.html` 必须成对出现。
- **不要手写 mxGraphModel XML**。布局和转义容易出错，用脚本。
- 节点 id 必须唯一且非空；每条边的 `from` / `to` 必须指向存在的节点，脚本会校验并报错。
- 生成的图要能被读懂：节点文字控制在 20 个汉字以内，超长会换行挤压形状。
- 菱形（`decision`）的文字空间最小，标签超过 8 个字就改短，或换成 `process`。

## 常见错误

| 现象 | 原因 | 处理 |
|---|---|---|
| 画布是空白页 | 用了 `--engine drawio` 但连不上外网 CDN | 改回默认 `--engine svg` |
| 回退连线穿过节点 | 没标 `dashed`，或方向选错 | 回退类连线用 `dashed` + `muted` |
| 文字溢出形状 | 标签太长 | 缩短文案，或调大该节点的 `width` / `height` |
| `.drawio` 打不开 | XML 被手工改坏 | 重跑脚本，不要手改 XML |

## 下一步

交付后主动问用户：是否需要调整配色、字号、方向（TB/LR），或把某个分支展开成更细的子图。
