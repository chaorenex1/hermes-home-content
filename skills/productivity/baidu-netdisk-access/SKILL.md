---
name: baidu-netdisk-access
description: "Use when managing Baidu Netdisk without the client."
version: 1.0.0
author: Masia
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [baidu, netdisk, cloud-storage, mcp, cli]
    related_skills: [browser-login-cookie-import, windows-tool-installation]
---

# 百度网盘：不装客户端管理文件

## When to use

- 要在不安装百度网盘客户端的前提下浏览、整理、上传、下载、分享网盘文件。
- 要把网盘接进 Hermes 或其他 agent，让自然语言或脚本直接操作。

## 先选路

| 目的 | 路线 | 关键代价 |
|---|---|---|
| 浏览、改名、移动、删除、分享 | 网页版 `pan.baidu.com/disk/main` | 零安装；约 >2 GB 下载强制客户端，>4 GB 上传失败 |
| agent 全盘操作 | 官方 MCP（SSE） | 需 30 天 Access Token；本地文件上传仅 stdio 版 |
| 命令行全盘操作 | BaiduPCS-Go | 需 BDUSS/STOKEN；第三方客户端，有风控风险 |
| 自建应用/程序化 | 开放平台 API | 第三方应用被限制在 `/apps/{appname}` |
| 挂载成盘符 | OpenList/AList + WebDAV | 需 refresh token；同样非官方 |

先问清目的再选，不要默认装 CLI。只整理文件时网页版就够。

## 官方 MCP（agent 首选）

- 端点 `https://mcp-pan.baidu.com/sse`：classic SSE，本机探测返回 `200 text/event-stream`；`/mcp` 是 404。
- 取 token（需用户本人登录，agent 不代登）：

```text
https://openapi.baidu.com/oauth/2.0/authorize?response_type=token&client_id=QHOuRXiepJBMjtk0esLhrPoNlQyYd0mF&redirect_uri=oob&scope=basic,netdisk&qrcode=1
```

  授权后从跳转地址的 fragment 取 `access_token`，`expires_in=2592000`（30 天），过期重授权。
- Hermes 接入：`hermes mcp add baidu-netdisk --url <sse-url> --auth header`（交互式，需 TTY），header 名 `Authorization`，值 `Bearer <token>`；条目里显式写 `transport: sse`，不要依赖自动回退。
- 工具面：`file_list`、`file_doc_list`、`file_image_list`、`file_video_list`、`file_meta`、`make_dir`、`file_copy`、`file_move`、`file_rename`、`file_del`、`file_keyword_search`、`file_semantics_search`、`file_sharelink_set`、`user_info`、`get_quota`、`file_upload_by_url`、文本上传。本地文件上传（`file_upload_stdio`）只在 stdio 模式存在。
- 证据口径：端点可达已实测；完整 token 流程按官方文档，未端到端跑过（缺 token）。别把它写成已验证。

## CLI：BaiduPCS-Go

- 安装、PATH、登录方式见 `windows-tool-installation` 技能（其中的 toolchain-recipes 参考）；cookie 从浏览器取的流程见 `browser-login-cookie-import`。
- 关键坑：STOKEN 必须取 `.pan.baidu.com` 的。用 `.passport.baidu.com` 的 STOKEN 时 `who`/`quota` 正常，但 `ls /` 返回 `-6 请重新登录`。
- 常用命令：`who`、`quota`、`ls /`、`cd`、`tree`、`download <远程> -saveto <本地>`、`upload <本地> <远端>`、`share set <路径> -p <码>`、`config set -savedir <目录>`。
- 验证口径：登录后用 `who` + `quota` + 一次 `ls /` 计数，不要用配置文件判断。
- 风险直说：非官方客户端，违反用户协议，可能被限速或封号；BDUSS 明文落在配置目录，别同步别外发。

## 开放平台 API 的边界

第三方应用调用 `filemanager`、`meta`、`move`、`download` 只能访问 `/apps/{appname}` 目录，管不了全盘；bypy 同样只能操作 `/apps/bypy`，且处于维护模式。需要全盘就用官方 MCP 或 CLI，别拿开放平台 API 当全盘方案。

## 硬限制

- 所有路线都受会员限速，网页版大文件下载会强制客户端。承诺速度前先看账号等级。
- 官方 MCP 与网页版不改变限速，只改变操作方式。
