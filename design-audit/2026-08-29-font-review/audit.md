# 页面字体审查

日期：2026-08-29

## 结论

当前字体方案可用、清晰，但不是最符合当前业界主流的跨平台中文金融产品方案。综合评价约 7/10。

- 中文：7/10。macOS 与 Windows 的首选字体合理，但 Linux 实际回退到 WenQuanYi Zen Hei，跨平台气质不一致。
- 英文：6/10。字体栈以中文字体优先，英文缩写和代码未优先使用平台 UI 拉丁字体。
- 数字：8/10。关键指标已启用 `tabular-nums`，但没有覆盖全部金融数字，图表字体栈也与 DOM 文本分离。

## 审查步骤

1. 风险收益页：整体健康。正文 15px / 1.55 易读，指标数字层级清楚；中文标题与英文、证券代码的字面和字重略不一致。
2. 技术状态页：可用但需优化。MA20、MA60、MACD、RSI 等缩写更集中地暴露了中文优先字体栈造成的混排不统一。

## 证据

- 页面 CSS 字体栈：`frontend/src/styles/tokens.css:2`
- 页面基础排版：`frontend/src/styles/app.css:3`
- 标题负字距与非标准字重：`frontend/src/styles/app.css:49`、`frontend/src/styles/app.css:96`
- 金融数字的等宽数字设置：`frontend/src/styles/app.css:107`、`frontend/src/styles/app.css:149`、`frontend/src/styles/app.css:173`
- 图表独立字体栈：`frontend/src/styles/chartTheme.ts:1`
- 当前 Chromium 实际字体：中文 WenQuanYi Zen Hei；英文和数字 DejaVu Sans。标题中的中文与英文/数字甚至使用了不同的实际字重。
- `frontend/public/fonts/wqy-microhei.woff2` 存在，但页面没有 `@font-face`，当前没有被加载。

## 主要问题

### 高优先级

1. 字体顺序不是当前主流的“平台 UI 字体优先”。当前把 PingFang SC、微软雅黑等中文字体放在最前，英文和数字也可能被中文字体接管。主流设计系统更常先使用系统 UI 字体，再为中文补充语言字体。
2. Linux 回退不可控。CSS 指定 WenQuanYi Micro Hei，但当前环境实际使用 WenQuanYi Zen Hei；结果与 macOS、Windows 的视觉差异较大。
3. `650`、`750`、`800` 依赖可变字体或对应实例。当前回退字体没有完整字重，浏览器会选最近字重或合成，导致中文和英文粗细不一致。
4. DOM 与 ECharts 维护两套字体栈。图表字体栈缺少平台 UI 字体，后续只改 CSS token 也不会同步图表。

### 中优先级

1. 中文品牌名和混排主标题使用较强负字距，中文笔画显得略挤；中文建议保持正常字距，只对纯英文大标题做轻微收紧。
2. 12px 的图表刻度、页脚和辅助标签处在桌面 UI 可读性的下限。当前尚可，但在低质量屏幕或缩放环境下风险较高。
3. `tabular-nums` 只覆盖部分指标和表格；日期、证券代码、图表数值及所有数据摘要应统一走数字 token。

## 推荐方案

默认推荐采用“系统 UI 拉丁字体优先，中文按平台回退”的栈：

```css
--font-ui:
  -apple-system, BlinkMacSystemFont,
  "Segoe UI Variable", "Segoe UI", Roboto, "Helvetica Neue", Arial,
  "PingFang SC", "Hiragino Sans GB",
  "Microsoft YaHei UI", "Microsoft YaHei",
  "Noto Sans CJK SC", "Noto Sans SC", sans-serif;
```

同时：

- 字重收敛到 `400 / 600 / 700`；除非明确加载可变字体，不再使用 `650 / 750 / 800`。
- 数据类文本统一使用 `font-variant-numeric: tabular-nums lining-nums`。
- CSS 与 ECharts 共用同一份字体常量。
- 中文标题移除或显著减小负字距。
- 若产品要求 macOS、Windows、Linux 截图完全一致，则改为自托管 Noto Sans SC 或 Source Han Sans SC 的所需字重，并按字符集切片；否则系统字体方案更符合主流，也更省加载成本。

## 官方基准

- Ant Design：优先平台默认字体，并提供跨平台回退字体。
- Apple HIG：优先系统字体、减少混用字样，并避免小字号的细字重。
- Microsoft：英文 UI 推荐 Segoe UI Variable，简体中文推荐 Microsoft YaHei UI；常用字重为 Regular / Semibold / Bold。
- MDN：`tabular-nums` 用于让数字等宽，适合表格与金融数据对齐。

## 证据限制

本次验证覆盖 1440×1000 的 Chromium/Linux 桌面环境、风险收益页与技术状态页。没有在 macOS Safari、Windows Edge、浏览器 125%/150% 缩放或系统大字体模式下做实机对比，因此不能声称所有平台字体一致或完全满足无障碍要求。
