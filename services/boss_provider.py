from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class BossSearchProvider:
    def __init__(self, console):
        self.console = console

    def search(self, keyword, limit=5):
        url = f"https://www.zhipin.com/web/geek/job?query={quote(keyword)}&page=1"
        results = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                html = page.content()
            finally:
                browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        links = soup.select('a[href*="/job_detail/"]')
        seen = set()

        for link in links:
            href = link.get('href', '').strip()
            if not href:
                continue
            full_url = href if href.startswith('http') else f"https://www.zhipin.com{href}"
            if full_url in seen:
                continue
            seen.add(full_url)

            card = link
            title = (
                link.get('title')
                or link.get_text(' ', strip=True)
                or '未知岗位'
            )
            company = '未知公司'

            company_node = card.select_one('.company-name') or card.select_one('[class*="company"]')
            if company_node:
                company = company_node.get_text(' ', strip=True) or company

            results.append({
                'title': title[:120],
                'company': company[:80],
                'url': full_url,
                'source': 'boss',
                'keyword': keyword,
            })
            if len(results) >= limit:
                break

        return results
