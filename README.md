# 量研手记（QuantLab）

面向个人学习的 A 股与场内 ETF 本地量化研究应用。当前前端以“风险收益课”和“技术状态课”组织内容，后端提供行情、资产资料、技术分析、缓存和双均线回测 API。

> 仅供个人研究学习，不构成投资建议。系统只分析历史数据，不预测价格、不连接券商，也不执行交易。

## 当前功能

- 搜索并切换 A 股或场内 ETF，默认标的是 `512480.SH`。
- 支持 1 周、1 月、3 月、6 月、1 年、3 年和全部历史区间。
- 风险收益课：区间收益、年化波动、最大回撤、夏普比率，以及对应的解释和学习评分。
- 技术状态课：沿用风险收益课的左侧状态选择、中间图表、右侧解释三栏布局，展示 MA20/MA60、MACD、RSI 14、20 日收益、20 日年化波动、布林带、ATR 和透明规则诊断；三栏下方提供默认折叠的公式与第一性原理指南。
- 数据追溯：响应包含数据源、抓取时间、缓存命中和质量告警。
- 数据服务：行情、交易日历、证券目录和资产资料均优先读取 SQLite 缓存；缺失或过期时再由唯一外部数据源 Tushare Pro 补齐。
- 桌面端界面：最小视口宽度为 1024px，不维护移动端响应式布局；图表提供可展开的数据表。
- 后端提供双均线回测与手动刷新 API；当前前端尚未挂载这两个操作入口。

当前界面使用收盘价折线和指标图，不提供 K 线/成交量视图，也没有可独立开关的指标叠加层。

## 技术栈

- 后端：Python 3.11+、FastAPI、Pydantic、Pandas、NumPy、Tushare Pro、SQLite。
- 前端：React 19、TypeScript 6、Vite 8、ECharts 6。
- 测试：pytest、Vitest、Testing Library、Playwright。

## 环境要求

- Python 3.11 或更高版本。
- Node.js 22.22.2 或更高版本。Vite 本身支持 Node 20.19+，但当前 jsdom 测试依赖要求 Node 22.22.2+。
- npm。
- GNU Make 为可选项；仅使用 `make` 快捷命令时需要。

## 安装

以下命令均从仓库根目录执行：

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install --upgrade pip
backend/.venv/bin/python -m pip install -e "./backend[dev]"

npm --prefix frontend ci
cp .env.example .env
```

若现有缓存不能完整覆盖所请求的区间，需通过 `.env` 配置 `TUSHARE_TOKEN` 或 `TUSHARE_TOKEN_FILE`，由 Tushare Pro 补齐缺口。已有 SQLite 缓存不会被安装或启动流程清除。

## 启动

终端 1：

```bash
cd backend
.venv/bin/uvicorn quantlab.main:app --reload --port 8000
```

终端 2：

```bash
cd frontend
npm run dev
```

打开 `http://127.0.0.1:5173`。Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`，FastAPI 文档位于 `http://127.0.0.1:8000/docs`。

行情请求先检查 SQLite 中 Tushare Pro 对应的缓存区间。完整命中时不访问网络；区间缺失时只向 Tushare Pro 请求缺口。证券目录按完整快照持久化并缓存 24 小时，ETF/股票资料按证券持久化并缓存 10 分钟。缓存过期且上游暂时失败时，服务会返回最近一次成功快照，并在响应 `meta.warnings` 中标记 `STALE_CACHE`。未配置 Token 时，已有完整缓存仍可继续服务，真正的缓存缺口才会返回数据源配置错误。

### Make 快捷命令

安装 GNU Make 后，可从仓库根目录使用：

```bash
make run        # 启动缓存优先、Tushare Pro 补缺的前后端
make test       # 后端与前端单元测试
make test-e2e   # 使用当前缓存/Tushare 配置的 Playwright 流程
make smoke-live # 访问外部数据源的实时 smoke test
```

当前 Playwright 用例仍针对上一版界面，更新前不应作为当前 UI 的验收结果。

## 配置

配置从仓库根目录 `.env` 读取。可用变量见 [.env.example](.env.example)：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `QUANTLAB_DATABASE_PATH` | `./data/quantlab-hfq-v1.db` | Tushare Pro 行情、交易日历、证券目录和资产资料的 SQLite 缓存路径；相对于后端进程工作目录 |
| `QUANTLAB_FRONTEND_ORIGIN` | `http://localhost:5173` | FastAPI 允许的前端 CORS Origin |
| `TUSHARE_TOKEN` | 空 | Tushare Pro Token；缓存缺失时与 Token 文件至少配置一个 |
| `TUSHARE_TOKEN_FILE` | 空 | Token 文件；配置时优先于 `TUSHARE_TOKEN` |
| `TUSHARE_API_URL` | `https://api.waditu.com/dataapi` | Tushare API 地址 |

Token 文件支持纯 Token、dotenv 风格的 `TUSHARE_TOKEN=...`，以及包含 `token`/`TUSHARE_TOKEN` 字段的 JSON。不要提交 `.env` 或 Token 文件。

## 测试与检查

不依赖 Make 的等价命令：

```bash
cd backend
.venv/bin/pytest

cd ../frontend
npm test -- --run
npm run lint
npm run build
```

实时 smoke test 会访问外部服务，不属于离线单元测试：

```bash
cd backend
.venv/bin/python ../scripts/smoke_live_data.py
```

## API 概览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 服务与数据源状态 |
| GET | `/api/instruments/search?q=` | 搜索证券 |
| GET | `/api/instruments/{code}` | 标的基础信息 |
| GET | `/api/instruments/{code}/profile` | 按资产类型返回统一资料 |
| GET | `/api/etf/{code}` | ETF 专用兼容路由 |
| GET | `/api/equity/{code}` | 股票专用兼容路由 |
| GET | `/api/market/{code}/daily?start=&end=` | 标准化日线 OHLCV |
| GET | `/api/analysis/{code}?start=&end=` | 风险收益、技术指标和诊断 |
| POST | `/api/data/{code}/refresh` | 刷新最近行情缓存 |
| POST | `/api/backtests/ma-cross` | 双均线事件回测 |

业务响应通常使用 `{ "data": ..., "meta": ... }` 包装。个别刷新和回测响应的 `meta` 当前为空对象。

## 文档状态

- 本 README 和 [frontend/README.md](frontend/README.md) 描述当前可运行版本。
- `docs/superpowers/specs` 与 `docs/superpowers/plans` 保存最初设计和实施过程，属于历史基线，文中已标明与当前实现的差异。
- [design-qa.md](design-qa.md) 是 2026-08-20 旧版界面的归档验收记录，不代表当前 UI 已完成视觉回归。

## 文档维护约定

- 修改依赖、启动命令、环境变量或 API 时，同步更新本 README 和 `.env.example`。
- 修改前端入口、页面能力或脚本时，同步更新 `frontend/README.md`。
- 视觉重构后重新生成 Design QA；旧验收记录保留为带日期和提交号的历史快照。
- 不把历史计划中的勾选框当作当前进度，当前行为始终以测试、运行代码和上述两份 README 为准。
