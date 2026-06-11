import re
from playwright.sync_api import sync_playwright
from rich.console import Console
import time

console = Console()

# 过滤掉非招聘相关的垃圾链接
EXCLUDE_DOMAINS = ['zhihu.com', 'csdn.net', 'baidu.com', 'google.com', 'youtube.com', 'github.com']

def search_google(keywords, max_results=5, proxy_server=None):
    urls = []
    # 优化搜索词：使用更通用的招聘关键词
    query = f'"{keywords}" (jobs OR hiring OR career)'
    
    with sync_playwright() as p:
        # 增加反检测参数
        launch_args = {'headless': True, 'args': ['--disable-blink-features=AutomationControlled']}
        if proxy_server:
            launch_args['proxy'] = {'server': proxy_server}
            
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            with console.status(f"[bold blue]🔍 正在 Google 侦察: {keywords}..."):
                # 1. 访问搜索页，使用 domcontentloaded 避免等待所有资源加载
                page.goto(f"https://www.google.com/search?num=100&q={query}", wait_until="domcontentloaded", timeout=30000)
                
                # 2. 自动处理 Cookie 同意弹窗 (这是导致超时的常见原因)
                try:
                    consent = page.locator('button:has-text("Accept all"), button:has-text("I agree")').first
                    consent.click(timeout=3000)
                    console.print("[dim]🍪 已处理 Cookie 弹窗[/dim]")
                    page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass

                # 3. 检测是否被 Google 拦截 (人机验证)
                body_text = page.text_content('body')
                if "unusual traffic" in body_text or "security check" in body_text:
                    console.print("[red]⚠️ Google 触发了安全验证 (CAPTCHA)。[/red]")
                    console.print("[yellow]建议：检查代理是否失效，或等待 5 分钟后重试。[/yellow]")
                    return urls

                # 4. 等待结果加载 (使用更宽泛的选择器)
                try:
                    page.wait_for_selector('div.g, div[data-sok], #search', timeout=15000)
                except:
                    console.print("[yellow]⏳ 搜索结果加载较慢，尝试直接提取...[/yellow]")

                # 5. 提取链接 (解析 Google 的重定向 /url?q=...)
                links = page.query_selector_all('a[href^="/url?q="], a[href^="https://"]')
                
                for link in links:
                    href = link.get_attribute('href')
                    if not href: continue
                    
                    # 清洗 Google 重定向链接
                    if '/url?q=' in href:
                        href = href.split('/url?q=')[1].split('&')[0]
                    
                    # 过滤有效链接
                    if href.startswith('http') and not any(domain in href for domain in EXCLUDE_DOMAINS):
                        urls.append(href)
                        if len(urls) >= max_results:
                            break
                            
        except Exception as e:
            console.print(f"[red]搜索异常: {e}[/red]")
        finally:
            browser.close()
            
    return list(set(urls))