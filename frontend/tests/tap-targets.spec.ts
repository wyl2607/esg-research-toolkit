import { expect, test } from '@playwright/test'

const routes = ['/', '/upload', '/companies', '/design-lab', '/compare'] as const

for (const route of routes) {
  test(`${route} keeps interactive tap targets >= 44x44`, async ({ page }) => {
    await page.goto(route, { waitUntil: 'networkidle' })

    const violations = await page.evaluate(() => {
      const nodes = Array.from(
        document.querySelectorAll<HTMLElement>('button, a[role="button"]')
      ).filter((el) => {
        const style = window.getComputedStyle(el)
        if (style.display === 'none' || style.visibility === 'hidden') return false
        if ((el as HTMLButtonElement).disabled) return false
        return true
      })

      return nodes
        .map((el) => {
          const rect = el.getBoundingClientRect()
          return {
            text: (el.textContent || '').trim().slice(0, 60),
            ariaLabel: el.getAttribute('aria-label'),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          }
        })
        .filter((item) => item.width > 0 || item.height > 0)
        .filter((item) => item.width < 44 || item.height < 44)
    })

    expect(violations).toEqual([])
  })
}
