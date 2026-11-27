# XTeam 预览与写回

## 文件分工

- Agent 从需求编写原生、未压缩的 `.drawio` XML；可另写 `notes.json`，包含 `assumptions` 与 `questions` 两个字符串数组。
- `scripts/build_preview.py` 验证 XML，导出 SVG，用 `assets/viewer.html.template` 生成固定 HTML。SVG 优先由 draw.io CLI 导出；未安装 CLI 时，由 `scripts/render_svg.py` 在无头 Chromium 中加载 diagrams.net 官方 viewer 并提取 SVG。不要让 agent 临时生成页面代码，也不要把示例的扁平 graph JSON 当作泳道图真相来源。
- HTML 只负责查看 SVG、缩放、打开 draw.io 嵌入编辑器和下载。编辑器通过 draw.io `postMessage` 协议导出最新 XML/SVG；HTML 将两者 POST 给同源服务。
- `scripts/preview_server.py` 每次从 NFS 工作区读取当前 XML，以 SHA-256 版本检测覆盖冲突，校验 XML/SVG，服务端优先用 draw.io CLI、其次用 Chromium 重算 SVG；两者失败才使用浏览器导出的 SVG。随后原子写回 SVG 和 `.drawio`。进程重启后仍以文件为准，不依赖进程记忆。

## 沙箱运行

将输出目录放在 XTeam 的会话工作区持久盘。先运行 `build_preview.py`，确认三个交付文件都已存在。预览与写回必须由同一个 HTTP 服务提供，不能使用只支持 GET 的 `python3 -m http.server`。

```bash
python3 scripts/preview_server.py \
  --directory <会话工作区内的输出目录> \
  --drawio diagram.drawio --port 7777 --bind 0.0.0.0
curl -f http://127.0.0.1:7777/api/diagram
curl -f http://127.0.0.1:7777/diagram.html
```

端口在 5555、6666、7777、8888 中选空闲的一个。服务进程不是持久的；预览卡失效时在同一持久目录重启服务。`embed.diagrams.net` 需要在用户浏览器可访问；若 XTeam 浏览器限制此域名，预览与下载仍可使用，编辑入口需平台放行或改接可用的 draw.io 域名。

XTeam 反馈其 headless shell 路径为 `/opt/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell`，完整版 Chrome 路径为 `/opt/ms-playwright/chromium-1234/chrome-linux64/chrome`。脚本在这两个固定路径中优先选 headless shell；若路径变动，设置 `DRAWIO_CHROMIUM`。XTeam 此次实测中，完整版 Chrome 的 `--dump-dom` 等待 90 秒后超时，headless shell 首次约 10 秒、后续约 3 秒出图；这是该沙箱的观测，不代表所有 Chromium 环境。PNG 自检沿用 `scripts/export_png.py`，在没有 draw.io CLI 时用同一官方 viewer 和 Chromium 截图。首次构建需要沙箱能访问 `viewer.diagrams.net`；生成后的 SVG 预览由本地服务提供。

服务确认可达后，按 XTeam 当前支持的预览卡协议输出 `wakeapp-app-preview` 代码块，`port` 填实际端口、`route` 填 URL 编码的 HTML 路径。平台材料中出现过 `wakerapp-app-preview` 与 `wakeapp-app-preview` 两种拼写，发布前在 XTeam 环境核对实际解析格式。给出 `.drawio` 会话文件下载入口；不要把静态 CDN 链接当作写回 API。

**平台待核对：** 直接改写 NFS 上的会话文件，是否自动更新 XTeam 已登记的会话附件及其下载链接。如果附件是快照，还需调用 XTeam 的文件登记/刷新能力；本技能目前只保证持久工作区文件与同源预览中的内容一致。
