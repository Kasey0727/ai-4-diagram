# 交付与预览

## 预览卡片必须指向运行中的服务

对话里的预览卡片来自当前沙箱里真实跑起来的静态服务，不是文件路径。顺序是：选端口 → 起服务 → 验证可达 → 输出卡片。

```bash
# 1. 在输出目录起静态服务（5555/6666/7777/8888 里选一个空闲端口）
cd <输出目录>
python3 -m http.server 7777 --bind 0.0.0.0
```

服务要以后台方式持续运行，回复结束后不能停。启动后先自检：

```bash
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 5 http://127.0.0.1:7777/
```

返回 `200` 才继续。然后在最终回复末尾输出卡片，`route` 用 URL 编码后的文件名：

```
​```wakeapp-app-preview
{"port":7777,"route":"/登录鉴权流程.html","title":"登录鉴权流程"}
​```
```

端口被占用时换下一个，不要 kill 别人的进程。

## 文件本身怎么给

用户要源文件时，用平台的预览链接，不要手写本地绝对路径：

```
https://xteam.jd.com/content-preview?sessionSpaceId=$XTEAM_SESSION_SPACE_ID&type={read|download}&ref={文件引用}&path={文件名}
```

- `.html` → `type=read`（浏览器内直接渲染）
- `.drawio` → `type=download`（浏览器无法渲染，作为文件下载）
- `ref` 填文件在会话内的相对路径，`ref` 与 `path` 都要 URL 编码，`path` 放最后一段文件名

`$XTEAM_SESSION_SPACE_ID` 由沙箱注入，不要自己猜。

## 两个链接都要给

HTML 链接让用户直接在浏览器里看图，`.drawio` 链接让用户拿去编辑。只给其中一个，用户下一句就会问「另一个呢」。

## 内网环境

`--engine drawio` 依赖 `viewer.diagrams.net` 的 CDN。内网或受限网络下画布会白屏，此时必须用默认的 `--engine svg`。判断方法：

```bash
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 10 https://viewer.diagrams.net/js/viewer-static.min.js
```

不是 `200` 就不要用 drawio 引擎。
