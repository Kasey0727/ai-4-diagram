# 项目修改记录

本文件记录项目级修改。时间统一使用 `Asia/Shanghai`（UTC+08:00），格式为 `YYYY-MM-DD HH:mm`。

## 后续维护约定

1. 每次功能修改或更新，都在本文件新增一条记录，写明时间、修改项和验证结果。
2. 修改与对应的 `PROGRESS.md` 记录放在同一次 Git 提交中。提交信息采用 Angular 风格：`<type>(<scope>): <subject>`，例如 `feat(skill): support vertical swimlanes`、`fix(diagram): align decision branches`、`docs: update progress log`。常用类型包括 `feat`、`fix`、`docs`、`refactor`、`test`、`chore`。
3. 项目关联 GitHub 后，每次提交都推送到对应远程仓库；记录中填入提交哈希。若远程仓库或推送权限暂不可用，明确记录未推送状态，不把本地提交视为已提交到 GitHub。

## 修改记录

| 时间 | 类型 | 修改项与验证 | 提交 |
| --- | --- | --- | --- |
| 2026-11-19 20:14 | `chore` | 在根目录 `.gitignore` 排除 `upstream-drawio-skill/`，并从暂存区移除该嵌套仓库条目；使用 `git check-ignore` 与暂存区检查验证。 | 待首次提交：尚未配置 GitHub remote。 |
| 2026-11-19 20:08 | `docs` | 新增全局修改记录及后续提交约定；核对根目录 Git 状态。 | 待首次提交：本地 `main` 尚无提交，尚未配置 GitHub remote。 |

## 历史补录

以下内容依据当前工作区和此前的任务记录补录。原始改动时间与提交哈希未逐项保存，因此不补写虚构的精确时间。

| 补录日期 | 修改项 |
| --- | --- |
| 2026-11-19 | 引入上游 `drawio-skill` 作为参考，制作订单库存流程图的早期 Demo 与上游效果对比。 |
| 2026-11-19 | 从上游抽取自然语言生图能力，形成独立的 `text2drawio-skill`，包含原生 `.drawio` 编写规范、结构校验、PNG 导出和自检流程。 |
| 2026-11-19 | 将 Skill 默认泳道改为竖向列、配色改为黑白灰，并统一条件分支的出口和正交线样式；新增 `check_conventions.py`，生成竖向灰度样例并更新对比页。 |
| 2026-11-19 | 删除不再使用的早期 `system-interaction-diagram` 原型目录；保留其历史图用于对比。 |
