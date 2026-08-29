# QuantLab 前端

量研手记的 React 前端。当前界面包含证券搜索、区间切换、风险收益课、技术状态课和资产资料折叠区。界面仅面向桌面端，最小视口宽度为 1024px，不维护移动端响应式布局；1024–1180px 使用图表优先的紧凑桌面两栏布局。

项目级安装、缓存优先/Tushare Pro 数据配置和 API 说明请先阅读仓库根目录的 [README](../README.md)。

## 环境要求

- Node.js 22.22.2+
- npm
- 本地后端默认监听 `http://127.0.0.1:8000`

## 安装与运行

```bash
npm ci
npm run dev
```

开发服务器默认位于 `http://127.0.0.1:5173`，`vite.config.ts` 会把 `/api` 代理到端口 8000 的后端。

## 脚本

```bash
npm run dev          # 启动 Vite 开发服务器
npm test -- --run    # 单次运行 Vitest 单元测试
npm run lint         # Oxlint
npm run build        # TypeScript 检查和生产构建
npm run preview      # 预览已构建产物
npx playwright test  # Playwright E2E
```

当前 Playwright 用例仍引用上一版搜索和回测界面，在用例更新前不能作为当前 UI 的验收结果。单元测试只扫描 `src/**/*.{test,spec}.{ts,tsx}`，不会包含 `e2e/`。

## 当前页面结构

- `App.tsx`：加载状态与“风险收益课 / 技术状态课”页面切换。
- `hooks/useResearch.ts`：默认标的、日期区间、并发请求取消和搜索状态。
- `components/ResearchWorkspace.tsx`：收益、波动、回撤、夏普和资产资料。
- `components/TechnicalWorkspace.tsx`：趋势、动量、波动状态及指标解释。
- `components/MarketChart.tsx`：风险收益联动图。
- `components/TechnicalChart.tsx`：MA、MACD、RSI、布林带和 ATR 联动图。
- `components/ChartDataTable.tsx`：图表对应的可展开、可访问数据表。
- `api/client.ts`：调用 FastAPI 的类型化客户端。

`BacktestLab.tsx`、刷新客户端和相应 API 仍保留在代码中，但当前没有挂载到 `App.tsx`。
