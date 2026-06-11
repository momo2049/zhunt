import time
import random
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def human_simulate_search(keyword, target_experience_text="3-5年"):
    """
    完全模拟人类在电脑前的操作：
    打开浏览器 -> 输入关键词 -> 点击经验筛选 -> 滚动获取真实社招岗位
    """
    results = []
    
    with sync_playwright() as p:
        # 1. 启动一个真实的可见浏览器（Headless=False 才能伪装成真人，并允许你手动处理可能的首次风控）
        # 💡 提示：可以指定 user_data_dir 来复用你本地 Chrome 已经登录好的猎聘 Cookie 状态
        browser = p.chromium.launch(
            headless=False, 
            args=["--disable-blink-features=AutomationControlled"] # 抹除 Playwright 自动化特征
        )
        
        # 创建一个更像真实浏览器的上下文
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        page = context.new_page()
        
        try:
            # 2. 轰炸基础搜索页（此时没有带任何污染参数）
            print(f"🚀 正在打开猎聘基础搜索页...")
            page.goto("https://www.liepin.com/zhaopin/", wait_until="networkidle")
            time.sleep(random.uniform(1.5, 2.5)) # 随机延迟，模拟人类观察
            
            # 3. 模拟人类肉眼寻找输入框，清空并键入关键词
            search_input = page.locator("input[placeholder*='搜索'], input.search-input, input[name='key']").first
            if search_input.is_visible():
                search_input.click()
                search_input.fill("") # 先清空
                # 模拟真人逐字敲击键盘
                for char in keyword:
                    page.keyboard.type(char)
                    time.sleep(random.uniform(0.05, 0.15))
            
            # 4. 模拟鼠标点击搜索按钮
            search_btn = page.locator("button:has-text('搜索'), .search-btn, .btn-search").first
            search_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 5. 🛠️ 降维打击校招：模拟人类点击“工作经验”筛选菜单
            # 猎聘的筛选栏通常有“工作年限”字样
            exp_filter = page.locator("text=工作年限, text=工作经验").first
            if exp_filter.is_visible():
                exp_filter.click()
                time.sleep(1)
                # 选择你指定的经验，比如 "3-5年" 或 "5-10年"
                target_option = page.locator(f"text={target_experience_text}").first
                if target_option.is_visible():
                    target_option.click()
                    print(f"🎯 已自动在界面上勾选【{target_experience_text}】经验筛选...")
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)

            # 6. 此时页面已经由猎聘官方 JS 注入了合法的 skId / fkId 并刷新了真实社招数据
            # 模拟人类滚屏看职位的动作，让懒加载的岗位卡片全部吐出来
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 400);")
                time.sleep(random.uniform(0.4, 0.8))
                
            # 7. 提取页面当前的完整 DOM 进行解析
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 猎聘的岗位列表卡片通常包含在特定的 job-list 或 card 样式中
            # 我们直接抓取所有可能包含职位详情的链接和文本块
            job_cards = soup.select("div[class*='job-card'], div[class*='job-list-item'], a[href*='/job/']")
            
            for card in job_cards:
                # 提取岗位详情的真正跳转链接
                a_tag = card if card.name == 'a' else card.find("a", href=True)
                if not a_tag:
                    continue
                url = a_tag.get("href", "")
                if "/job/" in url:
                    if not url.startswith("http"):
                        url = "https://www.liepin.com" + url
                    
                    # 抓取当前卡片里的可视文本作为初筛文本
                    card_text = card.get_text(separator="\n").strip()
                    
                    if url not in [r['url'] for r in results] and len(card_text) > 50:
                        results.append({
                            "url": url,
                            "raw_text": card_text
                        })
                        
        except Exception as e:
            print(f"❌ 自动化模拟交互发生错误: {str(e)}")
        finally:
            browser.close()
            
    return results