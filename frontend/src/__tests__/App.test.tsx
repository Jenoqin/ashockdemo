import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from '../App'

describe('App', () => {
  it('renders the research product identity and disclaimer', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: '量研手记' })).toBeInTheDocument()
    expect(screen.getByText('仅供个人研究学习，不构成投资建议')).toBeInTheDocument()
  })
})
