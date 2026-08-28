# Design QA Archive — 一页研究手记（2026-08-20）

> **状态：历史快照，不代表当前界面。** 本记录对应提交 `8569733` 的旧版“一页研究手记”设计验收。此后项目重构为“风险收益课 / 技术状态课”双页面，并修改了数据加载、资产资料和图表结构；当前版本尚未执行新的截图级视觉回归。下面的本机截图路径和测试数量仅保留为当时的审计记录，在其他环境中不可复现。

当前功能、运行方式和已知限制以 [README.md](README.md) 为准。

## Comparison target

- Source visual truth: `C:\Users\User\.codex\generated_images\01a01cc9-45bf-7fd0-8eff-44e562d8fa76\exec-7507de69-a968-41af-9aea-372940ec7dec.png`
- Browser-rendered implementation: `C:\Users\User\.codex\visualizations\2026\08\20\01a01cc9-45bf-7fd0-8eff-44e562d8fa76\design-qa-redesign\implementation-desktop-final.png`
- Local URL: `http://127.0.0.1:5173/`
- State: `512480.SH`, `1年`, lesson `先看整体斜率`, AI notice closed, evidence open, advanced drawer closed.

## Normalization

- Source pixels: `1487 × 1058`.
- Implementation pixels: `1425 × 1013`.
- CSS viewport: `1440 × 1024`.
- Browser device pixel ratio: `1.0000000149011612` (evaluated as 1x).
- The source was resized proportionally to `1425 × 1013` for equal-density comparison; no crop or browser chrome was introduced.
- Full-view comparison: `C:\Users\User\.codex\visualizations\2026\08\20\01a01cc9-45bf-7fd0-8eff-44e562d8fa76\design-qa-redesign\comparison-final-full.png`.
- Focused comparison: `C:\Users\User\.codex\visualizations\2026\08\20\01a01cc9-45bf-7fd0-8eff-44e562d8fa76\design-qa-redesign\comparison-final-focused.png`.

## Findings

- No actionable P0, P1, or P2 differences remain.
- Typography: the editorial serif verdict, compact sans-serif UI text, weights, wrapping and hierarchy match the selected visual intent. The implementation uses system Song-style fallbacks rather than a downloaded web font to keep the local app dependency-free.
- Spacing and layout: the left verdict column, dominant chart, reading-order strip and evidence band preserve the source proportions and visual sequence. Advanced material stays below the primary reading flow.
- Colors and tokens: off-white paper, near-black text, vermilion accent, green trend, amber risk and red loss treatments map cleanly to the source without gradients or presentation-card shadows.
- Image and icon fidelity: the target has no raster image assets. Chart annotations are real ECharts data layers, and interface icons use the existing Phosphor icon library; there are no placeholder images, custom SVG illustrations or CSS-art substitutes.
- Copy and content: the screen leads with one plain-language conclusion, then three data-backed statements, then chart evidence. Dynamic values use the live analysis response and retain the learning-only disclaimer.
- Accessibility and responsiveness: semantic headings, tabs, expanded state, labels, focus rings and reduced-motion handling are present. At `390 × 844`, the screen has no horizontal overflow and preserves the conclusion-first hierarchy.

## Comparison history

| Pass | Severity | Finding | Fix | Post-fix evidence |
| --- | --- | --- | --- | --- |
| Desktop pass 1 | — | The first implementation already matched the selected editorial composition with no actionable desktop P0/P1/P2 mismatch. | No desktop visual fix required. | `implementation-desktop-pass1.png`, `comparison-final-full.png` |
| Mobile pass 1 | P2 | Asset name wrapped to two lines because code and type competed for width in the header. | Hide secondary code/type labels below `600px`, keeping the asset name on one line. | `implementation-mobile-final.png` |

## Interaction and runtime checks

- AI explanation button opens and closes its reserved explanatory state.
- The three reading steps switch selected tab state and update the chart emphasis.
- Range controls retain pressed state and remain connected to the existing research loader.
- Search, refresh, evidence disclosure, advanced indicator disclosure and advanced content disclosure remain available.
- Browser console errors and warnings in the final pass: none.
- Mobile viewport: `390 × 844`; horizontal overflow: none.
- Automated tests: 8 passed.
- Production build: passed.
- Lint: passed with one pre-existing `useResearch.ts` exhaustive-deps warning.

## Follow-up polish

- P3: the compact search field remains visible in the desktop header to preserve an existing core action, while the source visual shows only the date. Its low visual weight does not compete with the verdict or chart.
- P3: the ECharts bundle still produces the existing large-chunk build warning; this does not affect visual fidelity or current interaction behavior.

## Final result

passed
