from playwright.sync_api import sync_playwright

def fetch_boss_jobs(keyword="后端工程师"):
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            storage_state="boss_state.json"
        )

        page = context.new_page()

        url = f"https://www.zhipin.com/web/geek/job?query={keyword}"
        page.goto(url)

        page.wait_for_timeout(5000)

        # 滚动加载
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(2000)

        # 抓岗位卡片
        cards = page.query_selector_all("a.job-card-left")

        for c in cards:
            title = c.inner_text()
            link = c.get_attribute("href")

            if link:
                jobs.append({
                    "title": title,
                    "url": "https://www.zhipin.com" + link
                })

        browser.close()

    return jobs