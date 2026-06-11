# services/duck_search.py
from ddgs import DDGS
from rich.console import Console
import time
import random

console = Console()

def search_duck(keywords, max_results=5):
    urls = []

    # 💡 核心防御：在此定义黑名单特征，防止把平台的搜索页、标签页、反爬验证页带入下游
    bad_features = [
        "zpssrseo", "/zhaopin/", "job_detail",  # BOSS直聘 SEO 聚合列表页特征
        "search", "query", "list", "welcome",    # 通用搜索、列表页特征
        "_security_check", "captcha",            # 验证码、人机拦截特征
        "login", "register", "signup"            # 登录注册特征
    ]

    def execute_search(q):
        found = []
        try:
            with DDGS() as ddgs:
                # 优先 API 模式
                try:
                    results = ddgs.text(q, backend="api")
                except:
                    results = ddgs.text(q)

                if results:
                    for res in results:
                        link = res.get('href', '')
                        if link.startswith('http'):
                            # 💡 核心修复：在这里进行拦截过滤，有黑名单特征的链接直接拒绝入库
                            if any(feature in link.lower() for feature in bad_features):
                                continue
                            found.append(link)
        except Exception as e:
            console.print(f"[red]搜索执行异常: {e}[/red]")
        return found

    # 主搜索
    with console.status(f"[bold blue]🦆 搜索中: {keywords}"):
        urls = execute_search(keywords)

    # 简化的 fallback
    if not urls:
        simple_kw = " ".join(keywords.split()[:3])
        console.print(f"[yellow]⚠️ 尝试简化搜索: {simple_kw}[/yellow]")
        urls = execute_search(simple_kw)

    unique_urls = list(set(urls))[:max_results]
    
    if unique_urls:
        for u in unique_urls:
            console.print(f"  [dim]✅ {u[:70]}[/dim]")
    else:
        console.print(f"[yellow]⚠️ 无结果: {keywords}[/yellow]")

    # 随机延迟，防止封禁
    time.sleep(random.uniform(0.5, 1.5))
    return unique_urls