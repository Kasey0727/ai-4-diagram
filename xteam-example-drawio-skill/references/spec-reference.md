# Spec 字段参考

## 顶层字段

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `title` | string | `流程图` | 图标题，同时用于 `.drawio` 的文件名与页面标题 |
| `direction` | `TB` / `LR` | `TB` | 主方向。TB 上到下，LR 左到右 |
| `nodes` | array | 必填 | 至少一个 |
| `edges` | array | `[]` | 可以为空（只画节点） |

## node

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 唯一、非空。边靠它引用 |
| `label` | string | 否 | 节点文字，支持 `\n` 强制换行 |
| `type` | string | 否 | 见下节，默认 `process` |
| `width` | int | 否 | 覆盖默认宽 |
| `height` | int | 否 | 覆盖默认高 |
| `x` / `y` | number | 否 | 覆盖自动排版坐标，少用 |

默认尺寸：`start` / `end` 150×56，`decision` 170×110，`db` 130×90，`note` 170×80，其余 190×64。

## edge

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `from` | string | 是 | 起点 node id |
| `to` | string | 是 | 终点 node id |
| `label` | string | 否 | 连线标签，判断分支必须写 |
| `style` | string | 否 | `default` / `success` / `danger` / `muted` |
| `dashed` | bool | 否 | 回退、重试、旁路连线设为 `true` |

## 排版规则

脚本按「最长路径分层」排版：

- 每个节点落在从入口可达的最深层级上。
- 同层节点沿交叉轴均匀分布并整体居中。
- 层级间距 80，同层节点间距 70。
- 用 DFS 找出的回边不参与分层，否则一个重试环会把整张图往下推一层。

所以 spec 里**不需要**关心坐标，只要把业务语义描述清楚。

## 布局选择建议

- 主线超过 7 步 → 用 `LR`，横向铺开更好读。
- 判定与分支多、有回退环 → 用 `TB`，垂直方向留白更足。
- 只有一个判断两个分支 → 两者都行，`TB` 更常见。

## 最小可用示例

```json
{
  "title": "示例",
  "direction": "TB",
  "nodes": [
    { "id": "a", "label": "开始", "type": "start" },
    { "id": "b", "label": "结束", "type": "end" }
  ],
  "edges": [{ "from": "a", "to": "b" }]
}
```
