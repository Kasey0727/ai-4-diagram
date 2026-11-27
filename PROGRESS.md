# 项目修改记录

本文件记录项目级修改。时间统一使用 `Asia/Shanghai`（UTC+08:00），格式为 `YYYY-MM-DD HH:mm`。

## 后续维护约定

1. 每次功能修改或更新，都在本文件新增一条记录，写明时间、修改项和验证结果。
2. 修改与对应的 `PROGRESS.md` 记录放在同一次 Git 提交中。提交信息采用 Angular 风格：`<type>(<scope>): <subject>`，例如 `feat(skill): support vertical swimlanes`、`fix(diagram): align decision branches`、`docs: update progress log`。常用类型包括 `feat`、`fix`、`docs`、`refactor`、`test`、`chore`。
3. 项目关联 GitHub 后，每次提交都推送到对应远程仓库；记录关联的提交主题或已有哈希，准确哈希以 Git 历史为准。若远程仓库或推送权限暂不可用，明确记录未推送状态，不把本地提交视为已提交到 GitHub。

## 修改记录

| 时间 | 类型 | 修改项与验证 | 提交 |
| --- | --- | --- | --- |
| 2026-11-27 15:38 | `fix` | 根据 XTeam 沙箱反馈，在 Chromium 候选链加入 PATH 和固定路径的 `chrome-headless-shell`，并在该沙箱固定路径中优先于完整版 Chrome；分别诊断渲染超时、进程启动失败、零 DOM 输出和 viewer 未生成 SVG。更新技能与交付说明，不改 HTML 编辑器。候选优先级模拟、错误分支模拟、Python 语法及本机实际 SVG 导出通过；XTeam 指定路径仍需在平台复测。 | `fix(skill): prefer XTeam headless shell for rendering` |
| 2026-11-24 18:07 | `feat` | 为 `text2drawio-skill` 增加无 draw.io CLI 时的渲染降级：官方 diagrams.net viewer + 无头 Chromium 导出 SVG，并为 PNG 自检截图；预览构建与编辑后服务端重算共用该链路。京小贝样例在本机 Chrome 下成功导出并目视检查完整黑白竖向泳道；模拟缺少 CLI 验证 HTML/SVG 构建、PNG 输出及 POST 后服务端重算与文件写回；Python 语法、ZIP 内容及 Git diff 检查通过。XTeam 容器中的 Chromium 路径尚待平台实测。 | `feat(skill): add Chromium rendering fallback` |
| 2026-11-24 16:36 | `feat` | 重构 `text2drawio-skill` 的 XTeam 交付结构：新增固定 HTML/SVG 预览模板与构建脚本、原生 XML/SVG 校验、同源 POST 写回服务、文件版本冲突检测及持久工作区交付说明；保留 agent 编写泳道 XML 与 PNG 自检流程。使用京小贝样例验证 SVG 构建、页面/API HTTP 200、POST 持久写入、旧版本 409、无效 XML 400、JavaScript 语法和 Git diff；浏览器实例不可用，未完成目视点击验证。`quick_validate.py` 因环境缺少 PyYAML 未运行，已单独检查 frontmatter。 | `feat(skill): add XTeam preview and file-backed editing` |
| 2026-11-24 11:25 | `fix` | 取消预览页标题的 flex 扩展，使文件名紧邻标题，空间不足时继续省略文字；保留同文件中已有的未提交文案改动。CSS 规则、JavaScript 语法和 Git diff 检查通过，本地页面 HTTP 返回 200；当前无可用浏览器实例，未完成目视验证。 | `fix(demo): keep title and filename adjacent` |
| 2026-11-23 18:33 | `fix` | 修复京小贝预览 v2 在浏览器缩放后顶部导航栏换行：窄屏保持单行，优先隐藏文件名并将标题缩成省略号，缩放及编辑／下载按钮不换行；极窄宽度允许导航栏横向滚动。响应式规则、JavaScript 语法和 Git diff 检查通过，本地页面 HTTP 返回 200；当前无可用浏览器实例，未完成目视验证。 | `fix(demo): keep preview toolbar on one line` |
| 2026-11-23 18:26 | `fix` | 将京小贝预览 v2 顶部的缩小／百分比／放大／适应按钮组置于导航栏水平中央，标题和编辑／下载按钮保持左右位置；补充窄屏布局。HTML 结构、JavaScript 语法、Git diff 检查通过，本地页面 HTTP 返回 200；当前无可用浏览器实例，未完成目视验证。 | `fix(demo): center preview zoom controls` |
| 2026-11-23 18:20 | `feat` | 京小贝 HTML 预览 v2 隐藏 draw.io 内置保存/退出按钮；顶部返回在检测到编辑变更时提供“应用修改并返回／放弃修改并返回／继续编辑”，顶部下载在编辑模式下获取实时 XML，并同步更新 SVG 预览。验证 JavaScript 语法、Git diff 检查、页面 HTTP 200；模拟放弃、应用、编辑中下载三条路径均通过。当前无可用浏览器实例，未完成实际点击验证。 | `feat(demo): unify editor actions in preview toolbar` |
| 2026-11-23 17:24 | `fix` | 调整京小贝预览 v2：移除全屏按钮和右下角说明，将容器 UI 改为 XTeam 示例的浅灰点阵、细边框与蓝色主按钮；保存后通过 draw.io 嵌入协议导出最新 SVG 并替换预览，退出后可查看修改结果，下载使用最新 XML。HTML 脚本语法、Git diff 检查和模拟的保存→SVG 导出→退出→最新 XML 下载流程通过；当前无可用浏览器实例，未完成实际点击验证。 | `fix(demo): refresh SVG preview after drawio save` |
| 2026-11-23 17:14 | `feat` | 新增京小贝 HTML 预览 v2，参考 XTeam 示例的紧凑工具栏和点阵画布，提供离线 SVG 预览、缩放平移、适应窗口、全屏、下载，并保留现有 draw.io 编辑器入口；旧 HTML 与原生泳道 XML 保留。SVG 仅含 `#000000` / `#FFFFFF` 且 XML 可解析；原图结构和约定检查为 0 错误，HTML 脚本语法通过。本地页面 HTTP 返回 200；当前无可用浏览器实例，未完成页面点击验证。 | `feat(demo): add SVG swimlane preview with editor controls` |
| 2026-11-20 11:11 | `feat` | 新增京小贝权益大卡系统交互测试：四泳道黑白 `.drawio`、PNG、需求原文、独立 HTML 预览及画布数据；旧 HTML 保留。结构与规范检查均为 0 错误，PNG 已目视检查，HTML/PNG/XML/JS 本地 HTTP 均返回 200，JavaScript 语法通过。在线编辑器因当前环境没有可用浏览器实例，未完成点击验证。 | `feat(demo): add Jingxiaobei rights swimlane preview` |
| 2026-11-19 20:47 | `feat` | 将生图规范、默认调色板、自动布局和样例统一为 `#000000` / `#FFFFFF`；规范检查器拒绝其他颜色和缺少显式颜色的节点/边。样例结构校验及规范检查均为 0 错误，旧灰度图被检出 54 项，PNG 已目视检查。 | `feat(skill): enforce pure black-and-white diagrams` |
| 2026-11-19 20:14 | `chore` | 在根目录 `.gitignore` 排除 `upstream-drawio-skill/`，并从暂存区移除该嵌套仓库条目；使用 `git check-ignore` 与暂存区检查验证。 | `f656ea3 feat: init project` |
| 2026-11-19 20:08 | `docs` | 新增全局修改记录及后续提交约定；核对根目录 Git 状态。 | `f656ea3 feat: init project` |

## 历史补录

以下内容依据当前工作区和此前的任务记录补录。原始改动时间与提交哈希未逐项保存，因此不补写虚构的精确时间。

| 补录日期 | 修改项 |
| --- | --- |
| 2026-11-19 | 引入上游 `drawio-skill` 作为参考，制作订单库存流程图的早期 Demo 与上游效果对比。 |
| 2026-11-19 | 从上游抽取自然语言生图能力，形成独立的 `text2drawio-skill`，包含原生 `.drawio` 编写规范、结构校验、PNG 导出和自检流程。 |
| 2026-11-19 | 将 Skill 默认泳道改为竖向列、配色改为黑白灰，并统一条件分支的出口和正交线样式；新增 `check_conventions.py`，生成竖向灰度样例并更新对比页。 |
| 2026-11-19 | 删除不再使用的早期 `system-interaction-diagram` 原型目录；保留其历史图用于对比。 |
