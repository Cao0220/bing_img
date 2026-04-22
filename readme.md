Bing_img
========

用于抓取 Bing 每日图片元数据、同步图片到 WebDAV，并维护历史图片索引。

## 脚本职责
- `bing.py`
  - 抓取当天各地区 Bing 首页图片元数据。
  - 写入 `YYYY/MM/DD/YYYY-MM-DD.json`。
  - 自动增量更新 `history.md`（按前一天去重、幂等追加）。
- `dl-img.py`
  - 按元数据计算需要上传的图片。
  - 下载缺失图片并上传到 WebDAV。
  - 上传成功后清理本地缓存图片。

## 目录结构
- 元数据文件：`YYYY/MM/DD/YYYY-MM-DD.json`
- 本地图片缓存：`YYYY/MM/DD/{index}.jpg`
- 历史索引：`history.md`
- WebDAV 图片路径：`remote_root/YYYY/MM-DD_index.jpg`

## 配置文件
`config.yaml` 需包含：
- `local.root`
- `webdav.base_url`
- `webdav.username`
- `webdav.password`
- `webdav.remote_root`
- `download.sleep_min_seconds`
- `download.sleep_max_seconds`

示例结构：

```yaml
local:
  root: /root/bing_img

webdav:
  base_url: https://example.com/dav
  username: your-username
  password: your-password
  remote_root: /images

download:
  sleep_min_seconds: 1.0
  sleep_max_seconds: 2.0
```

## 日常流程
1. 抓取当天元数据并同步历史索引：
   `python3 bing.py`
2. 上传缺失图片到 WebDAV：
   `python3 dl-img.py`

## dl-img.py 参数说明
默认行为（无参数）：处理最近 15 个自然日（含今天）。

常用命令：
- 最近 15 天（默认）：
  `python3 dl-img.py`
- 全量扫描（从最早到最新元数据）：
  `python3 dl-img.py --all`
- 仅处理单日：
  `python3 dl-img.py --date 2026-04-20`
- 处理日期区间：
  `python3 dl-img.py --from 2026-04-01 --to 2026-04-20`
- 仅查看执行计划（不下载/不上传/不删除）：
  `python3 dl-img.py --dry-run`

参数规则：
- `--date` 与 `--from/--to` 都会覆盖默认 15 天窗口。
- `--all` 与 `--date/--from/--to` 互斥，同时使用会报错退出。

## history.md 维护规则
- `history.md` 由 `bing.py` 自动维护，不需要手工编辑。
- 每个日期段格式：
  - 日期行：`YYYY-MM-DD`
  - 分隔线：`----------------`
  - 图片行：`![YYYY-MM-DD-index](https://www.bing.com/..._UHD.jpg)`
- 去重逻辑：同一天中与前一天重复的图片不会重复写入。
- 幂等性：重复运行 `bing.py` 不会重复追加已存在日期。

## 行为说明
- `dl-img.py` 会自动把旧目录 `YYYY-MM-DD` 迁移到 `YYYY/MM/DD`（可重复执行，幂等）。
- 远端文件已存在时，不重复上传，并清理本地同名缓存。
- 上传失败时会保留本地缓存，便于后续重试。

## 常见问题
- 报错 `Missing config keys`：检查 `config.yaml` 是否缺字段。
- 无上传动作：先用 `python3 dl-img.py --dry-run` 查看计划，再确认日期范围与元数据是否存在。
- 历史未更新：确认当日 JSON 已生成，再运行 `python3 bing.py`。

## 历史图片
- 见 `history.md`
