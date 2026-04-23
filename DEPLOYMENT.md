# 发布说明

这个项目已经具备发布到静态托管的基础能力。当前默认推荐：**GitHub Pages**。

## 1. 发布前必须确认

正式对外发布前，至少确认：
- 最终托管平台
- 最终公开 Base URL
- 最终 UID 域名
- 是否接受 GitHub Pages 默认地址作为首发地址

> 注意：UID 一旦对外发布后，不应轻易修改，否则订阅客户端可能出现重复事件。

## 2. 本地发布前验证

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/validate_holidays.py
python scripts/build_ics.py --domain calendar.example.com --base-url https://calendar.example.com
pytest -q
```

## 3. GitHub Pages 发布方式

如果把当前目录作为独立 GitHub 仓库根目录，可以直接使用：

- `.github/workflows/publish-ics.yml`

该工作流会：
1. 安装依赖
2. 校验节日数据
3. 生成 `.ics` 文件和 `index.html`
4. 发布 `dist/` 到 GitHub Pages

## 4. 首次启用 GitHub Pages

在 GitHub 仓库设置中：
- 打开 **Settings → Pages**
- Source 选择 **GitHub Actions**

然后推送到 `main` 分支即可触发发布。

## 5. 发布产物

GitHub Pages 发布后，默认会公开：

- `/all.ics`
- `/environment.ics`
- `/culture-reading.ics`
- `/festivals.ics`
- `/index.html`

其中 `index.html` 是订阅入口页，会列出每个订阅文件的完整链接。

## 6. 关于 Base URL

工作流当前默认使用：

```text
https://<owner>.github.io/<repo>
```

如果后续改成自定义域名，需要同步更新：
- 工作流中的 `BASE_URL`
- 构建时传入的 `--base-url`
- 构建时传入的 `--domain`

## 7. 推荐首次上线策略

建议先：
1. 用 GitHub Pages 发布第一版
2. 在 Apple Calendar / Google Calendar 中手动订阅验证
3. 确认 URL 和 UID 策略稳定后，再考虑换域名

## 8. 自定义托管

如果不用 GitHub Pages，也可以：
- 本地运行 `python scripts/build_ics.py --domain ... --base-url ...`
- 直接把 `dist/` 上传到 Cloudflare Pages、S3/R2、OSS 等静态托管

核心要求不变：
- URL 稳定
- UID 域名稳定
- 不要频繁改路径
