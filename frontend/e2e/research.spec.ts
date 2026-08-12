import { test, expect } from '@playwright/test'

test.describe('Research Workflow', () => {
  test('search, research and backtest flow', async ({ page }) => {
    // Navigate to app
    await page.goto('/')
    
    // Default instrument should load
    await expect(page.getByText('半导体ETF')).toBeVisible()

    // Use search box
    const searchInput = page.getByPlaceholder('搜索 6 位代码/拼音')
    await searchInput.fill('510300')
    await page.getByRole('button', { name: '搜索' }).click()
    
    // Wait for research to finish
    await expect(page.getByText('沪深300ETF')).toBeVisible()
    
    // Verify market chart is present
    await expect(page.getByTestId('market-chart')).toBeVisible()
    
    // Verify asset profile is present
    await expect(page.getByText('跟踪指数')).toBeVisible()
    await expect(page.getByText('演示指数')).toBeVisible() // From DemoProvider

    // Run backtest
    const runBtn = page.getByRole('button', { name: '运行回测' })
    await runBtn.click()

    // Wait for backtest results to appear
    await expect(page.getByText('策略年化')).toBeVisible()
    await expect(page.getByText('交易记录')).toBeVisible()
  })
})
