# Tushare 缓存完整性修复方案 V2

状态：**已实施并验证**  
记录日期：2026-08-29  
目标问题：高优先级发现 DF-01——部分行情响应可能被错误标记为完整缓存。

实施结果：逐日事实缓存、严格迁移、Provider 响应校验、原子刷新和离线/真实数据测试均已落地；`REVIEW_FINDINGS.md` 中 DF-01 已复审为修复。

## 1. 背景与当前缺陷

当前实现已解决首尾截断的部分场景，但仍使用返回行情的 `MIN(trade_date)` 和 `MAX(trade_date)` 表示连续覆盖，因此存在三个未解决问题：

1. 返回 8 月 3 日和 5 日但缺少 4 日时，3–5 日仍会被标记为完整。
2. `refresh=True` 可删除首尾日期之间原本有效的内部缓存行，再把不完整结果标记为完整。
3. 旧缓存迁移同样使用 `MIN/MAX` 重建覆盖范围，可能把不连续缓存合并为完整区间。

必须停止从价格行首尾推断完整性，改为证明请求范围内每一天的状态。

## 2. 已锁定决策

- SQLite 缓存仍是第一数据层，Tushare Pro 是唯一外部数据源。
- 采用严格迁移：保留全部价格行，但旧覆盖元数据必须重新验证。
- 采用完整性优先：历史日期未全部确认时，不向分析和结论模块返回成功结果。
- 不再允许带 `PARTIAL_RANGE` 的部分行情进入分析流程。
- 完整且已经验证的旧缓存可以在 Tushare 故障时通过 `STALE_CACHE` 返回。
- 本次只解决缓存完整性及必要的 provider 接口，不处理其他评审发现。

## 3. Tushare 依据与实测证据

### 官方接口语义

- `trade_cal` 返回每个日历日期及 `is_open`，用于区分交易日和休市日：<https://tushare.pro/wctapi/documents/26.md>
- A 股 `daily` 每次最多 6000 行；官方明确说明停牌期间不提供行情：<https://tushare.pro/wctapi/documents/27.md>
- ETF `fund_daily` 每次最多 5000 行：<https://tushare.pro/wctapi/documents/127.md>
- ETF `fund_adj` 每次最多 2000 行：<https://tushare.pro/wctapi/documents/199.md>
- 股票 `suspend_d` 可以解释开市日无行情的停牌场景：<https://tushare.pro/wctapi/documents/214.md>

因此日线和复权因子统一按最多 366 个自然日分段，远低于接口行数限制。

### 2026-08-29 只读实测

使用项目已配置的 Tushare Token：

- `512480.SH`，范围 2025-08-26 至 2026-08-25：
  - 交易日历开市日：242
  - `fund_daily`：242
  - `fund_adj`：242
  - 本地 Tushare 缓存：242
  - 四组日期完全一致，没有内部缺口。
- `000029.SZ` 在 2020-03-12：
  - 交易日历显示开市。
  - `daily` 返回 0 行。
  - `suspend_d` 返回 1 行停牌记录。
- Tushare `trade_cal(exchange="BSE")` 当前返回空；2025–2026 年 SSE 与 SZSE 日历逐日一致。因此 BJ 证券暂时复用 SSE 日历，并通过测试固定该映射。

这些结果证明：开市日没有行情既可能是数据缺失，也可能是合法停牌，必须进一步确认，不能依靠价格日期首尾判断。

## 4. 新的缓存事实模型

保留现有 `price_bars`，新增两个事实表：

```sql
CREATE TABLE market_calendar (
    exchange TEXT NOT NULL,
    cal_date TEXT NOT NULL,
    is_open INTEGER NOT NULL CHECK (is_open IN (0, 1)),
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (exchange, cal_date)
);

CREATE TABLE no_bar_dates (
    dataset TEXT NOT NULL,
    code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    PRIMARY KEY (dataset, code, trade_date)
);
```

每个日期按以下规则解释：

- `price_bars` 有记录：`bar`，行情存在。
- `market_calendar.is_open = 0`：`market_closed`，交易所休市。
- 日期早于证券 `list_date`：`not_listed`，不要求行情。
- 历史开市日经过单日查询仍为空：写入 `no_bar_dates`。
- 其他日期：未确认，缓存不能判定完整。

`sync_ranges` 不再作为事实来源。可以保留旧表以便迁移兼容，但任何完整性判断都不得读取它。

## 5. Provider 内部接口

扩展 `MarketDataProvider`：

```python
def get_trade_calendar(
    exchange: str,
    start: date,
    end: date,
) -> dict[date, bool]: ...

def get_listing_date(code: str) -> date | None: ...

def get_daily(code: str, start: date, end: date) -> list[PriceBar]: ...
```

约束：

- SH 映射到 `SSE`，SZ 映射到 `SZSE`，BJ 暂时映射到 `SSE`。
- `get_daily` 必须拒绝错误代码、重复日期、区间外日期和缺失复权因子的响应。
- 区间外响应必须是 `ProviderError`，不能过滤后当作空结果。
- `suspend_d` 只用于股票缺口的原因补充和批量优化，不是完整性判断的必要依赖。
- ETF 以及不能由停牌表解释的股票缺口，统一使用历史单日行情查询确认。

## 6. 获取流程

### 6.1 缓存检查

1. 标准化证券代码并取得证券级 single-flight 锁。
2. 读取上市日期、交易日历、价格行和 `no_bar_dates`。
3. 请求范围内的历史日期全部可解释时，直接返回缓存，不调用 Tushare。
4. 当前开市日只有实际存在行情时才算完整；空结果不永久确认。
5. 未来日期不请求 Tushare，不参与历史完整性判断，并返回 `FUTURE_RANGE_TRUNCATED`。

### 6.2 缺口补齐

1. 缓存缺失的交易日历按交易所和年份从 `trade_cal` 获取并缓存。
2. 将未确认历史日期按最多 366 天分段。
3. 批量获取日线和复权因子并执行 schema、代码、范围、日期唯一性及价格质量检查。
4. 批次返回后，与开市日期集合比较。
5. 对缺失的开市日执行单日查询：
   - 返回行情：加入待提交价格。
   - 成功返回空：写入待提交 `no_bar`；股票存在停牌记录时原因设为 `suspended`，否则为 `provider_confirmed_empty`。
   - 请求失败或响应异常：保持未确认。
6. 请求范围全部验证完成后，在一个 SQLite 事务中提交交易日历、价格和 `no_bar` 状态。

### 6.3 不完整与失败行为

- 任何历史日期仍未确认时，不返回部分成功结果。
- 若请求前存在完整、已验证缓存，保持缓存不变并返回 `STALE_CACHE`。
- 若没有完整缓存，抛出 `DataUnavailableError`。
- Provider 失败不得写入行情、日历、`no_bar` 或覆盖元数据。
- Provider cooldown 只由真实请求失败触发，合法空日不触发。

## 7. 刷新语义

`refresh=True` 必须先在内存中完成整个请求范围的验证，然后再提交：

- 返回行情的日期：更新对应价格行并删除同日 `no_bar`。
- 单日确认无行情的日期：删除该日旧价格并写入 `no_bar`。
- 未确认日期：不删除或修改任何旧数据。
- 整个请求未验证完成：不提交任何刷新结果；完整旧缓存按 `STALE_CACHE` 返回，否则报错。

禁止继续调用“删除首尾日期之间所有价格”的 `replace_range(observed_start, observed_end, bars)`。

## 8. 迁移方案

引入覆盖策略版本，例如：

```text
tushare-calendar-v2
```

迁移步骤：

1. 创建 `market_calendar` 和 `no_bar_dates`。
2. 保留所有 `price_bars`，包括历史 Tushare 和已停用 provider 的数据。
3. 删除或停用 Tushare 的旧 `sync_ranges`；不得使用 `MIN/MAX` 重建。
4. 数据库初始化期间不访问网络。
5. 首次真实请求复用已有价格行，只获取交易日历并复查无法解释的开市日。
6. 重验完成后，后续完整缓存可以在未配置 Token 或 Tushare 故障时使用。

## 9. 公共行为

- API JSON 结构保持不变。
- 保留 `STALE_CACHE`。
- 新增 `FUTURE_RANGE_TRUNCATED` 警告。
- `PARTIAL_RANGE` 不再作为成功响应进入分析层。
- 缓存来源仍显示 `Tushare Pro`，`cache_hit` 表示是否完全由已验证 SQLite 缓存提供。

## 10. 测试计划

必须新增以下离线测试：

1. 批量结果有 8 月 3 日和 5 日、缺少 4 日：必须单独复查 4 日。
2. 内部缺口单日复查返回行情：补齐后才能判完整。
3. 内部缺口单日复查为空：记录 `no_bar` 后才能判完整。
4. 单日复查失败：不得返回部分结果或写入完成状态。
5. 部分刷新缺少中间日：不得删除原缓存中间行。
6. Provider 返回区间外日期、错误代码或重复日期：拒绝并保持缓存不变。
7. 迁移时存在两个不连续价格区间：不得合并为连续覆盖。
8. 周末、节假日和上市前日期：正确解释且不调用行情接口。
9. 股票停牌：开市日无行情但可由 `suspend_d`/单日空结果确认。
10. ETF 历史空日：通过单日查询确认。
11. 当前开市日空响应：保持可重试。
12. 完整缓存且没有 Token：不得调用 Tushare。
13. Tushare 故障且只有部分缓存：返回数据不可用。
14. Tushare 故障且有完整验证缓存：返回 `STALE_CACHE`。
15. 并发相同请求仍只执行一次 Tushare 获取。

保留可选的真实数据 smoke test：比较 `512480.SH` 一年期 `trade_cal`、`fund_daily` 和 `fund_adj` 日期集合；默认测试套件仍完全离线。

## 11. 完成标准

- 内部缺失交易日不能再被首尾日期隐藏。
- 不完整刷新不能删除有效缓存。
- 旧缓存价格行全部保留，旧连续覆盖不再被信任。
- 未确认历史区间不能进入指标分析或结论生成。
- 完整验证缓存始终优先于 Tushare，并支持离线使用。
- 新增测试、现有非 HTTP 后端测试和前端测试全部通过。

## 12. 恢复执行顺序

后续恢复时按以下顺序实施：

1. 先扩展 fake provider 和失败测试，覆盖内部缺口、刷新及迁移。
2. 增加新缓存表和逐日完整性查询。
3. 扩展 Tushare provider 的交易日历与上市日期能力。
4. 重写 `MarketDataService` 的缓存检查、分段获取、单日复查和原子提交。
5. 实施严格迁移并验证现有数据库价格行数量不变。
6. 运行离线回归，再运行可选 Tushare smoke test。
7. 重新审查 DF-01，确认状态从“部分修复”变为“已修复”。
