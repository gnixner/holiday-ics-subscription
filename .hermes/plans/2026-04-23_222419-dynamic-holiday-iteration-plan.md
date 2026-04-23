# Dynamic Holiday Iteration Plan

## Goal
在不破坏现有订阅稳定性的前提下，迭代扩充节日覆盖范围。优先维护 `.ics` 订阅能力、数据模型、校验与排重逻辑；待订阅侧稳定后，再最小幅度更新前端展示与文案。

## Current Context
- 现有数据模型只支持固定公历日期：`month` + `day`
- 校验逻辑仍是 MVP 版：只处理固定日期、只排除 1/1 和 5/1
- 构建逻辑 `expand_holiday()` 只会展开固定日期
- 现有线上订阅已可用，UID 规则不能随意破坏
- 用户现在希望补充：
  - 动态节日（如母亲节、父亲节）
  - 中国其他法定/重要节日，但要先与 Apple 中国大陆源排重
  - 找靠谱的订阅源作为参考

## Findings From This Audit
### Apple 中国大陆源
参考源：`https://calendars.icloud.com/holidays/cn_zh.ics`
- 已覆盖大量中国语境节日与节气
- 当前数据与其几乎无直接重名冲突
- 但 `国际妇女节` 与 Apple 的 `妇女节` 应视作重复，后续应排除
- Apple 中国大陆源已覆盖：春节、元宵节、清明、端午节、中秋节、国庆节、重阳节、七夕节、冬至、除夕、妇女节、青年节、儿童节、建党节、建军节等
- 不覆盖：母亲节、父亲节、感恩节、情人节、圣诞节、地球日、世界读书日、教师节、植树节、平安夜

### 参考订阅源
1. Apple China holidays
   - `https://calendars.icloud.com/holidays/cn_zh.ics`
   - 用途：排重基准
2. Apple US holidays
   - `https://calendars.icloud.com/holidays/us_en.ics`
   - 已确认包含 Easter / Good Friday / Mother's Day / Father's Day / Thanksgiving / Valentine's Day / Halloween
   - 用途：动态西方节日对照基准
3. Office Holidays China
   - 页面：`https://www.officeholidays.com/subscribe/china`
   - 订阅：`https://www.officeholidays.com/ics/china`
   - 额外选项：`https://www.officeholidays.com/ics-clean/china`、`https://www.officeholidays.com/ics-all/china`
   - 用途：第二参考源，适合对照中国法定与常见纪念日

## Proposed Iterations

### Iteration 1 — Data Model + Validation Hardening
优先级最高，只动订阅侧基础设施。

#### Scope
- 扩展数据模型，支持至少两类规则：
  - `fixed_date`
  - `nth_weekday_of_month`
- 保持旧数据兼容：未声明规则类型的旧数据默认视为固定日期
- 新增 Apple China 排重逻辑（至少对显式已知重复项生效）
- 将“国际妇女节”移除或禁用

#### Likely file changes
- `data/holidays.yaml`
- `scripts/validate_holidays.py`
- `tests/test_holiday_schema.py`
- `tests/test_calendar_outputs.py`
- `tests/test_uid_stability.py`

#### Validation
- 新增规则字段校验
- 固定日期与动态规则互斥校验
- 动态规则参数合法性校验（month / weekday / nth）
- Apple 排重测试

### Iteration 2 — Generator Support for Dynamic Holidays
在模型和校验稳定后，再扩展生成器。

#### Scope
- 将 `expand_holiday()` 改为按 `rule_type` 分发
- 实现：
  - 第 N 个星期几（母亲节、父亲节、感恩节）
- 保持 UID 稳定性：
  - 继续使用 `{holiday_id}-{year}@{domain}`
  - 不因规则类型不同而改 UID 结构

#### First batch additions
- 母亲节
- 父亲节
- 感恩节
- 教师节
- 植树节
- 情人节
- 平安夜
- 排除：国际妇女节

#### Likely file changes
- `scripts/build_ics.py`
- `data/holidays.yaml`
- `tests/test_calendar_outputs.py`
- `tests/test_uid_stability.py`

#### Validation
- 指定年份展开结果正确
- 关键样例日期断言：
  - 母亲节 = 5 月第 2 个星期日
  - 父亲节 = 6 月第 3 个星期日
  - 感恩节 = 11 月第 4 个星期四
- 全量 `.ics` 构建通过

### Iteration 3 — Optional Richer Dynamic Rules
在第 1、2 轮稳定后再做。

#### Candidate scope
- `easter_relative`
  - 复活节
  - 耶稣受难日
- 可选：黑五（相对感恩节）

#### Risk
- 规则复杂度明显上升
- 需要额外测试边界年份

### Iteration 4 — Lunar / China Supplemental Holidays
最后再考虑，避免过早引入复杂度。

#### Candidate scope
- 腊八节
- 小年
- 龙抬头

#### Recommendation
- 不立即引入完整农历算法
- 更稳妥的做法：先用 5 年窗口预计算映射表
- 若要长期自动化，再引入成熟农历库

### Iteration 5 — Frontend Sync
仅在订阅侧稳定后再进行。

#### Scope
- 前端卡片说明补充“动态节日已支持”的文案
- 如果分组数量或节日结构变化明显，再调整首页说明
- 尽量不改交互架构，不动已有氛围设计

## Execution Order
1. 先做 Iteration 1：模型与校验
2. 再做 Iteration 2：动态规则生成 + 第一批新增节日
3. 重新构建与回归测试
4. 视结果再做 Iteration 3
5. 最后再做前端同步

## Files Most Likely To Change First
- `data/holidays.yaml`
- `scripts/validate_holidays.py`
- `scripts/build_ics.py`
- `tests/test_holiday_schema.py`
- `tests/test_calendar_outputs.py`
- `tests/test_uid_stability.py`

## Risks / Tradeoffs
- Apple China 源是排重基准，但网络获取偶有不稳定；实现上不要让构建过程强依赖在线抓取
- 若直接把 Apple 全量节气/传统节日规则硬编码进校验，会过于脆弱；第一步应先处理明确重复项和用户指定的主要节日
- 农历支持不要和动态公历支持一起上，否则回归成本过高
- 前端应最后更新，避免反复改文案和说明

## Immediate Next Step
进入 Iteration 1：
- 先用测试约束新的数据模型与排重行为
- 再修改校验器和构建器
- 先让订阅侧通过，再考虑首页文案同步
