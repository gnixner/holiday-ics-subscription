# 非中国大陆法定节日 ICS 订阅 MVP

这是一个独立的小项目，用结构化 YAML 数据源生成 **4 份可订阅的 ICS 日历文件**，专门补充 **中国大陆法定节假日之外** 的国际纪念日、文化/阅读主题日和常见国际节庆。

## MVP 边界

本版本已冻结为：
- 只包含 **27 个节日**
- **不包含** 中国大陆法定节假日
- **不包含** 元旦、国际劳动节
- **不包含** 农历节日和移动节日
- `SUMMARY` 固定使用**纯中文**
- 不启用次分类
- 默认生成未来 **5 年** 的事件

## 项目结构

```text
holiday-ics-subscription/
  data/
    holidays.yaml
  scripts/
    validate_holidays.py
    build_ics.py
  dist/
    all.ics
    environment.ics
    culture-reading.ics
    festivals.ics
    index.html
  tests/
    test_holiday_schema.py
    test_uid_stability.py
    test_calendar_outputs.py
  .github/workflows/
    publish-ics.yml
  DEPLOYMENT.md
```

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## 本地使用

### 1. 校验数据

```bash
python scripts/validate_holidays.py
```

### 2. 本地生成

```bash
python scripts/build_ics.py
```

### 3. 带发布参数生成

```bash
python scripts/build_ics.py \
  --domain calendar.example.com \
  --base-url https://calendar.example.com \
  --start-year 2026 \
  --years 5 \
  --dist-dir dist
```

### 4. 运行测试

```bash
pytest -q
```

## CLI 参数

`build_ics.py` 支持：
- `--start-year`
- `--years`
- `--domain`
- `--base-url`
- `--dist-dir`
- `--data-file`

其中：
- `--domain` 用于生成 UID
- `--base-url` 用于生成 `index.html` 中的订阅链接

## 生成结果

构建后会产出：

- `dist/all.ics`
- `dist/environment.ics`
- `dist/culture-reading.ics`
- `dist/festivals.ics`
- `dist/index.html`（仅当传入 `--base-url` 时生成）

## 默认实现常量

当前默认值：
- `CALENDAR_DOMAIN=calendar.local`
- `DEFAULT_YEARS=5`
- `PRODID=-//Other Holidays ICS//ZH//EN`

> 注意：`calendar.local` 目前只是开发占位值。正式发布前应改成最终稳定域名；一旦外部用户开始订阅，不应轻易改动 UID 规则。

## GitHub Pages 发布

当前已经附带一个适用于**独立仓库**的 GitHub Pages 工作流：

- `.github/workflows/publish-ics.yml`

如果把当前目录作为独立仓库根目录，推送到 `main` 后即可自动：
- 安装依赖
- 校验数据
- 生成 ICS 文件
- 生成订阅入口页
- 发布到 GitHub Pages

更多说明见：
- `DEPLOYMENT.md`

## 发布 URL 形态

正式部署后建议保持稳定路径，例如：

```text
/all.ics
/environment.ics
/culture-reading.ics
/festivals.ics
```

## 已知限制

当前 MVP **不支持**：
- 中国大陆法定节假日
- 农历节日
- 复活节、母亲节、感恩节等移动节日
- 多语言 `SUMMARY`
- 动态 API / CalDAV / 用户自定义组合

## 验证重点

当前测试会验证：
- 数据文件可解析且条目数为 27
- 元旦与国际劳动节不会混入
- UID 稳定
- 4 个 ICS 文件能生成
- 可生成 `index.html` 作为订阅入口页
- `all.ics` 中包含地球日、世界读书日、圣诞节

## 发布前仍需最终确认

正式对外发布前，还应再确认：
- 最终使用的 UID 域名
- 静态托管方式
- 对外公开 URL
- 客户端兼容性实测记录
