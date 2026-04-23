# 客户端订阅验收

本文件用于手动验证公开订阅地址在主流日历客户端中的可用性。

## 当前线上地址

- 入口页：
  - https://gnixner.github.io/holiday-ics-subscription/
- 全部：
  - https://gnixner.github.io/holiday-ics-subscription/all.ics
- 环保与社会议题：
  - https://gnixner.github.io/holiday-ics-subscription/environment.ics
- 文化与阅读：
  - https://gnixner.github.io/holiday-ics-subscription/culture-reading.ics
- 常见节庆：
  - https://gnixner.github.io/holiday-ics-subscription/festivals.ics

## 验收目标

确认以下几点：
- 可以成功添加订阅
- 全天事件显示正确
- 不出现元旦、国际劳动节
- 关键样本节日存在
- 重复刷新后不出现明显重复事件

## 关键样本节日

验收时至少检查：
- 地球日
- 世界读书日
- 圣诞节
- 世界环境日
- 万圣节

## 必须排除样本

验收时确认不存在：
- 元旦
- 国际劳动节

## Apple Calendar

### 建议步骤
1. 打开 Calendar
2. 选择 `File -> New Calendar Subscription`
3. 粘贴 `all.ics` 地址
4. 完成订阅

### 验收点
- [ ] 能成功添加
- [ ] 日历名称合理
- [ ] 地球日显示在 4/22
- [ ] 世界读书日显示在 4/23
- [ ] 圣诞节显示在 12/25
- [ ] 无元旦
- [ ] 无国际劳动节
- [ ] 刷新后无重复事件

## Google Calendar

### 建议步骤
1. 打开 Google Calendar 网页版
2. 通过 URL 添加日历
3. 粘贴 `all.ics` 地址
4. 等待拉取

### 验收点
- [ ] 能成功添加
- [ ] 关键样本节日存在
- [ ] 日期没有偏移
- [ ] 无元旦
- [ ] 无国际劳动节
- [ ] 重复同步后无明显重复

## Outlook / 兼容客户端

### 建议步骤
1. 打开 Outlook
2. 使用“从 Internet 订阅日历”或同类入口
3. 粘贴 `all.ics` 地址

### 验收点
- [ ] 能成功添加
- [ ] 全日事件显示正常
- [ ] 关键样本节日存在
- [ ] 无冲突节日混入

## 记录建议

每完成一个客户端，就在 `CLIENT_COMPATIBILITY_REPORT.md` 中记录：
- 客户端名称
- 日期
- 是否通过
- 发现的问题
