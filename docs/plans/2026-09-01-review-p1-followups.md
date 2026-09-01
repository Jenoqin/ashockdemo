# Review P1 后续任务恢复清单

日期：2026-09-01
基线提交：`9e6a224`（`chore: standardize backend runtime with uv`）
状态：P0 和 4 个 P1 均已完成。

## 1. 文档用途

本文用于在上下文丢失、会话中断或更换执行者后恢复任务。开始工作时以当前代码为准重新验证，不要仅依赖本文中的历史行号。

本轮 Review 原始结论共包含 5 项：

- P0：同步 FastAPI API 在不兼容运行环境中挂起；已完成依赖锁定、运行时预检和 uvloop 启动基线。
- P1：平盘行情产生非有限分析值，导致 JSON 序列化失败；已完成。
- P1：手动刷新回退旧缓存时仍虚假报告成功；已完成。
- P1：前端手动刷新存在跨标的、跨区间竞态；已完成。
- P1：回测 API 缺少服务端参数约束；已完成。

## 2. 当前验证基线

基线提交已验证：

- 后端锁文件检查通过。
- 默认 `asyncio` 和 `uvloop` 同步 FastAPI 路由预检通过。
- 后端 `108 passed`。
- 前端 `17 passed`。
- 前端生产构建通过；仅有大于 500 kB 的 chunk 提示，不属于本清单范围。

受限沙箱可能禁止默认 asyncio 所需的跨线程 socket 唤醒并返回 `EPERM`。这属于宿主能力限制；应在标准宿主权限下执行完整后端门禁。日常启动由 `start.sh` 显式使用 uvloop。

本次提交最终验证：后端锁文件检查通过；标准宿主环境默认 asyncio 和 uvloop 预检均通过；后端 `169 passed`；前端 `21 passed`；前端 lint 和生产构建通过，仅保留既有大 chunk 提示。

## 3. 推荐执行顺序

1. `RF-01`：统一分析输出的有限值门禁。已完成。
2. `RF-02`：让手动刷新准确返回成功、降级和告警状态。已完成。
3. `RF-03`：消除前端刷新竞态，并补充异步竞态测试。已完成。
4. `RF-04`：为回测请求增加服务端参数约束。已完成。

每完成一项，应更新本文状态和验证记录。建议每项形成一个独立提交，避免正确性修复相互耦合。

## 4. RF-01：分析结果非有限值门禁

状态：`已完成`
优先级：`P1`
主要文件：

- `backend/src/quantlab/services/analytics.py`
- `backend/src/quantlab/models.py`
- `backend/tests/test_analytics.py`
- `backend/tests/test_api.py`

### 问题

60 日平盘行情的滚动波动率为零，滚动夏普计算会产生 `-inf`。当前 `optional_values()` 只通过 `pd.isna()` 过滤 NaN，不会过滤正负无穷。FastAPI 最终进行严格 JSON 序列化时会报：

```text
Out of range float values are not JSON compliant: -inf
```

基线复现中，80 条平盘数据产生 20 个非有限 `rolling_sharpe`。

### 实现要求

- 建立统一的有限浮点值转换逻辑：NaN、`+inf` 和 `-inf` 均转换为 `None`。
- 至少覆盖所有 `AnalysisSeries` 数组和 `PerformanceMetrics` 浮点字段。
- 滚动夏普应在分母为零或非有限时直接产生缺失值，不依赖最终序列化阶段兜底。
- 检查 beta、correlation、excess return、回撤和技术指标路径，保证 API 输出不包含任何非有限浮点数。
- 不要把非有限值静默改成 `0`，因为零具有业务含义。

### 验收标准

- 60 日及更长平盘行情请求返回 HTTP 200。
- 平盘行情中的不可计算指标返回 JSON `null`。
- 对完整分析响应执行严格 JSON 序列化成功。
- 新增服务层测试和至少一个 API 回归测试。
- 正常波动行情的现有指标结果不发生非预期变化。

### 完成记录

- 在模型层新增统一的有限浮点转换类型，`PerformanceMetrics` 浮点字段和 `AnalysisSeries` 数值数组会将 NaN、`+inf`、`-inf` 规范化为 `None`。
- 滚动夏普在年化波动率为零或非有限时直接产生缺失值；滚动收益、滚动波动率也先过滤非有限值。
- beta、correlation、excess return、回撤和全部技术指标序列统一经过有限值转换；常量序列不再计算无定义的相关系数。
- 新增 80 条平盘行情服务层回归测试和 90 日平盘行情 API 回归测试，覆盖 JSON `null` 与严格 JSON 序列化。
- 验证：`uv lock --check`；标准宿主环境 asyncio/uvloop 预检均通过；后端 `114 passed`；前端 `17 passed`；生产构建通过（保留既有大 chunk 提示）。

## 5. RF-02：手动刷新结果真实性

状态：`已完成`
优先级：`P1`
主要文件：

- `backend/src/quantlab/api/market.py`
- `backend/src/quantlab/services/market_data.py`
- `backend/tests/test_api.py`
- `backend/tests/test_market_data.py`
- `frontend/src/api/types.ts`（若响应契约需要调整）

### 问题

`POST /api/data/{code}/refresh` 丢弃 `market_service.get_daily(..., refresh=True)` 的返回结果，并无条件返回：

```json
{"data":{"refreshed":true},"meta":{}}
```

即使上游刷新失败并回退到完整旧缓存、底层已经给出 `STALE_CACHE`，接口仍报告成功，且丢失告警。

### 实现要求

- 保留并返回行情服务的 `meta`，尤其是 `warnings`、`fetched_at`、`data_end_date`、`cache_hit` 和 `sources`。
- 明确定义 `refreshed` 的含义：只有成功取得并提交新数据时才能为 `true`。
- 若刷新失败但可返回旧缓存，应返回可识别的降级状态和 `STALE_CACHE`，不能伪装成刷新成功。
- 若没有可用缓存且上游失败，沿用稳定、可识别的 API 错误结构。
- 更新 README 或数据流文档中的刷新响应说明，确保文档与接口契约一致。

### 验收标准

- 成功刷新返回 `refreshed: true`，并携带真实 `meta`。
- 上游失败且回退旧缓存时，不返回虚假的成功状态，并保留 `STALE_CACHE`。
- 上游失败且无缓存时返回预期错误状态。
- API 测试覆盖以上三条路径。

### 完成记录

- `MarketDataResult` 显式记录手动刷新是否完成验证和缓存提交，API 不再无条件报告成功。
- 成功刷新返回 `refreshed: true`、`status: "refreshed"`；旧缓存降级返回 `refreshed: false`、`status: "stale_cache"`，并完整透传来源、抓取时间、数据截止日、缓存命中及 `STALE_CACHE`。
- 无缓存且上游失败时不再被路由的宽泛异常捕获覆盖，继续返回稳定的 `DATA_UNAVAILABLE` 错误结构。
- 服务层和 API 测试覆盖成功、完整旧缓存降级、无缓存失败；README 与数据流文档已同步响应契约。

## 6. RF-03：前端手动刷新竞态

状态：`已完成`
优先级：`P1`
依赖：应在 `RF-02` 明确刷新响应契约后处理。
主要文件：

- `frontend/src/hooks/useResearch.ts`
- `frontend/src/api/client.ts`
- `frontend/src/__tests__/App.test.tsx`
- 可新增独立 hook 测试文件

### 问题

常规加载通过 `AbortController` 和递增请求编号防止旧响应覆盖新状态，但 `refresh()` 路径没有取消信号、请求编号或组件卸载保护。

以下时序仍可能污染页面：

1. 用户在证券 A、区间 1Y 上点击刷新。
2. 刷新未完成时切换到证券 B 或区间 1M。
3. B/1M 的常规请求先完成并显示。
4. A/1Y 的旧刷新随后完成，覆盖当前页面。

### 实现要求

- 让常规加载和手动刷新共用同一套请求生命周期保护。
- 新请求开始、标的变化、区间变化或组件卸载时，应取消或失效旧请求。
- 只有当前最新请求可以更新 `bundle`、`status` 和 `error`。
- 将 `AbortSignal` 传递到刷新后的研究请求；如需要，也扩展刷新 API 客户端以接收信号。
- 处理刷新请求与自动加载重叠时的状态语义，避免旧请求把新请求的 `ready/error` 状态覆盖。

### 验收标准

- 刷新中切换标的，旧响应不能覆盖新标的数据。
- 刷新中切换区间，旧响应不能覆盖新区间数据。
- 连续点击刷新时只有最后一次请求可以提交状态。
- 组件卸载后不再更新状态。
- 使用可控 Promise 编写确定性的竞态测试，不依赖真实计时或网络。

### 完成记录

- 自动加载和手动刷新统一使用同一个请求执行器、`AbortController`、递增请求编号和挂载状态保护。
- 刷新接口及随后的研究请求共享同一个 `AbortSignal`；证券/区间变化、新刷新或卸载都会中止并失效旧请求。
- 只有当前最新请求可以提交 `bundle`、`status` 和 `error`，被中止或过期的成功/失败结果均被忽略。
- 新增 4 个可控 Promise hook 测试，确定性覆盖切换标的、切换区间、连续刷新和组件卸载；前端测试增至 `21 passed`。

## 7. RF-04：回测 API 服务端参数约束

状态：`已完成`
优先级：`P1`
主要文件：

- `backend/src/quantlab/models.py`
- `backend/src/quantlab/api/backtests.py`
- `backend/src/quantlab/services/backtest.py`
- `backend/tests/test_backtest.py`
- `backend/tests/test_api.py`

### 问题

`BacktestRequest` 当前接受零周期、负周期、负费率、负本金和超过 100% 的滑点。基线复现确认以下请求可以成功构造：

```text
fast_window=0
slow_window=-1
fee_rate=-0.5
slippage_rate=2.0
initial_cash=-100
```

API 目前只额外检查快线小于慢线、日期顺序和行情数量，不能阻止上述非法值进入回测计算。

### 实现要求

- `fast_window`、`slow_window` 必须为正整数，并保持 `fast_window < slow_window`。
- `initial_cash` 必须是有限正数。
- `fee_rate` 和 `slippage_rate` 必须是有限非负数，并设置符合业务语义的明确上限；至少禁止达到或超过 100% 的滑点。
- 日期范围必须保持 `start <= end`。
- 优先在 Pydantic 请求模型中表达字段约束和跨字段校验，让所有调用入口共享同一规则。
- 保持 API 的 422 错误结构稳定，不向调用方暴露内部异常。

### 验收标准

- 零/负周期、快线不小于慢线、负费率、负滑点、过大滑点、非有限数和非正本金全部返回 422。
- 合法边界值有明确测试。
- 服务层直接调用时也不能绕过关键约束。
- 现有正常回测测试继续通过。

### 完成记录

- `BacktestRequest` 在 Pydantic 模型中约束正整数窗口、`fast_window < slow_window`、`start <= end` 和有限正本金。
- 费率限定为 0–10%（含），滑点限定为 0–100%（不含）；负值、越界值和 NaN/无穷均被拒绝。
- 回测服务在计算前重新验证请求，即使通过 `model_construct()` 绕过初次模型校验也无法进入计算。
- FastAPI 请求校验错误统一映射为 HTTP 422 和 `INVALID_BACKTEST_PARAMETERS`；新增非法字段、非有限值、合法边界及服务层绕过测试。

## 8. 完整验证命令

从仓库根目录执行：

```bash
cd backend
uv lock --check
uv run --locked --extra dev python ../scripts/check_async_runtime.py --loop all
uv run --locked --extra dev pytest

cd ../frontend
npm test -- --run
npm run build
```

如果当前受限沙箱禁止默认 asyncio 的跨线程 socket 唤醒，应在标准宿主环境重跑完整后端门禁；不要通过降级 AnyIO 或把阻塞 I/O 放入 `async def` 路由规避。

## 9. 恢复任务检查表

恢复工作时依次执行：

- [ ] 阅读本文并检查 `git status --short --branch`。
- [ ] 确认当前分支和基线提交，检查基线之后是否已有相关修复。
- [ ] 重跑目标问题的最小复现，避免重复修复已解决问题。
- [ ] 一次只处理一个 `RF-*` 任务，并先补失败测试。
- [ ] 运行目标测试，再运行第 8 节的完整门禁。
- [ ] 更新对应任务状态、实现摘要、测试结果和完成提交。
- [ ] 提交前执行 `git diff --check` 并检查无关改动。

## 10. 进度记录

| 任务 | 状态 | 完成提交 | 验证记录 |
|---|---|---|---|
| RF-01 分析结果非有限值门禁 | 已完成 | 本提交 | 80 条平盘数据不可计算指标为 `null`；严格 JSON 成功；后端 114 passed；前端 17 passed；构建通过 |
| RF-02 手动刷新结果真实性 | 已完成 | 本提交 | 成功/旧缓存降级/无缓存失败三条 API 路径通过 |
| RF-03 前端手动刷新竞态 | 已完成 | 本提交 | 4 个可控 Promise 竞态测试通过；前端 21 passed |
| RF-04 回测 API 参数约束 | 已完成 | 本提交 | 模型/API/服务绕过测试通过；后端总计 169 passed |
