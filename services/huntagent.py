# services/huntagent.py
import json
import os
import sys
import re
import time
import random
from bs4 import BeautifulSoup
from rich.console import Console
from playwright.sync_api import sync_playwright

# 💡 引入高级模糊匹配算法，处理岗位命名差异
try:
    from rapidfuzz import fuzz
except ImportError:
    # 优雅降级：若用户环境未安装 rapidfuzz，采用 Python 标准库 difflib 保证不崩溃
    import difflib
    class MockFuzz:
        @staticmethod
        def partial_ratio(s1, s2):
            matcher = difflib.SequenceMatcher(None, s1.lower(), s2.lower())
            return matcher.real_quick_ratio() * 100
    fuzz = MockFuzz()

current_dir = os.path.dirname(os.path.abspath(__file__))
for p in [current_dir, os.path.dirname(current_dir)]:
    if p not in sys.path: sys.path.append(p)

try:
    from keywords import generate_job_keywords
except ImportError:
    import importlib.util
    def dynamic_import(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    kw_mod = dynamic_import("keywords", os.path.join(current_dir, "keywords.py"))
    generate_job_keywords = kw_mod.generate_job_keywords

console = Console()

# ================= 🚀 多平台侦察兵基类 =================

class BaseScout:
    """所有平台 API 拦截侦察兵的通用基类"""
    def start(self, browser_context):
        pass
    def close(self):
        pass
    def scrape_keyword(self, keyword, city, progress_callback):
        return []

# ================= 🔍 侦察兵 1：猎聘网 (API 接口拦截版) =================

class LiepinScout(BaseScout):
    """猎聘网专属侦察兵：拦截 Mapi 接口数据"""
    def start(self, browser_context):
        self.page = browser_context.new_page()
        self.captured_jobs = []
        # 💡 注册 Response 监听器：拦截猎聘岗位搜索 API 
        # 猎聘 API 搜索通常匹配 api/v1/search/job 或 search/pc-search
        self.page.on("response", self._intercept_response)

    def close(self):
        try: self.page.close()
        except: pass

    def _intercept_response(self, response):
        url = response.url
        if "api/v1/search" in url or "search/pc-search" in url or "search-job" in url:
            try:
                payload = response.json()
                # 兼容多种版本的猎聘接口数据字段
                data = payload.get("data", {})
                job_list = (data.get("jobCardList", []) or data.get("jobList", []) or 
                          data.get("list", []) or data.get("dataList", []))
                if not job_list:
                    sub = data.get("pageData", {}) or data.get("searchResult", {})
                    job_list = (sub.get("jobCardList", []) or sub.get("jobList", []) or 
                              sub.get("list", []) or sub.get("dataList", []))
                for j in job_list:
                    job_data = j.get("job", {}) if "job" in j else j
                    comp_data = j.get("comp", {}) if "comp" in j else j
                    job_id = job_data.get("jobId") or job_data.get("id")
                    title = job_data.get("title") or job_data.get("name")
                    salary = job_data.get("salary") or job_data.get("salaryDesc") or "薪资面议"
                    city_name = job_data.get("city") or job_data.get("cityName") or "未知"
                    # 组合成标准化的岗位数据，提供给后续的老猎头 AI 模块
                    raw_text_block = f"""
                    【渠道：猎聘网】
                    公司名称：{comp_data.get('compName', '匿名企业') or comp_data.get('name', '匿名企业')}
                    职位名称：{title}
                    薪资范畴：{salary}
                    工作地点：{city_name}
                    工作经验：{job_data.get('requireExp', '不限') or job_data.get('requireWorkYears', '不限')}
                    职责简述：{job_data.get('description', '暂无职责简述')}
                    """
                    self.captured_jobs.append({
                        "url": f"https://www.liepin.com/job/{job_id}.shtml" if job_id else url,
                        "title": title or "未知岗位",
                        "raw_text": raw_text_block.strip(),
                        "source": "猎聘网"
                    })
            except Exception as e:
                console.print(f"[dim]⚠️ [猎聘] 拦截解析异常: {url[:60]} - {str(e)}[/dim]")
                pass

    def scrape_keyword(self, keyword, city, progress_callback):
        self.captured_jobs = []
        try:
            progress_callback(f"🌐 [猎聘战线] 正在启动独立沙盒切入城市 [ {city} ]...")
            self.page.goto("https://www.liepin.com/zhaopin/", wait_until="domcontentloaded", timeout=15000)
            time.sleep(1.5)
            # 手动登录状态检测
            current_url = self.page.url
            if "login" in current_url or self.page.locator(".login-container, #login-submit, [class*='login-box']").first.is_visible(timeout=2000):
                progress_callback("🔑 [猎聘战线] 🚨 猎聘网弹出登录窗口！请在弹出的专属浏览器中扫码。完成后系统会自动保存 Cookie 状态继续运行...")
                login_timeout = 180  
                logged_in = False
                for i in range(login_timeout):
                    try:
                        is_login_form_visible = self.page.locator(".login-container, #login-submit, [class*='login-box']").first.is_visible(timeout=500)
                    except:
                        is_login_form_visible = False
                    if not is_login_form_visible and "login" not in self.page.url:
                        logged_in = True
                        progress_callback("🎉 [猎聘战线] 🟢 登录成功，锁定 Cookies 并恢复自动对标...")
                        time.sleep(2)
                        break
                    progress_callback(f"🔑 [猎聘战线] ⏳ 等待您在浏览器中登录... 剩余: {login_timeout - i} 秒")
                    time.sleep(1)
                if not logged_in:
                    return []

            # 模拟输入并回车，触发拦截
            search_input = self.page.locator("input[placeholder*='搜索'], input.search-input, input[name='key']").first
            if search_input.is_visible(timeout=3000):
                search_input.click()
                search_input.fill("")
                progress_callback(f"⌨️ [猎聘战线] 正在输入检索词: [ {keyword} ] ...")
                for char in keyword:
                    self.page.keyboard.type(char)
                    time.sleep(random.uniform(0.01, 0.04))
                self.page.keyboard.press("Enter")
                # 给接口充分的时间接收响应，确保 _intercept_response 执行完毕
                time.sleep(4.0)
        except Exception as e:
            console.print(f"[red]❌ [猎聘] API 拦截异常: {str(e)}[/red]")
        # 📌 DOM 提取兜底
        if not self.captured_jobs:
            try:
                html = self.page.content()
                soup = BeautifulSoup(html, 'html.parser')
                liepin_selectors = [
                    "a[href*='job/']", "[class*='job-card'] a",
                    ".job-title a", "[class*='job-title'] a",
                    "a[href*='job_']", "[class*='job-info'] a",
                    ".sojob-item-main a", "a[class*='job-name']"
                ]
                seen = set()
                for sel in liepin_selectors:
                    for elem in soup.select(sel):
                        title = elem.get_text().strip()
                        href = elem.get("href", "")
                        if title and len(title) >= 3 and title not in seen:
                            seen.add(title)
                            if href and href.startswith("/"):
                                href = "https://www.liepin.com" + href
                            if href and "javascript" not in href:
                                self.captured_jobs.append({
                                    "url": href,
                                    "title": title,
                                    "raw_text": f"【猎聘网】\n城市：{city}\n岗位：{title}".strip(),
                                    "source": "猎聘网"
                                })
                if self.captured_jobs:
                    console.print(f"[green]✅ [猎聘] DOM提取 {len(self.captured_jobs)} 个岗位[/green]")
                else:
                    console.print(f"[yellow]⚠️ [猎聘] DOM提取也未找到岗位[/yellow]")
            except Exception as dom_e:
                console.print(f"[dim]⚠️ [猎聘] DOM提取异常: {str(dom_e)[:80]}[/dim]")
        return self.captured_jobs

# ================= 🔍 侦察兵 2：BOSS直聘 (零重载接口拦截版) =================

class BossScout(BaseScout):
    """BOSS直聘专属侦察兵：拦截 zpData 核心 API"""
    def start(self, browser_context):
        self.page = browser_context.new_page()
        # 💡 抹除 webdriver 检测指纹
        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.current_city = None
        self.captured_jobs = []
        self.city_map = {
            "北京": "101010100", "上海": "101020100", "广州": "101280100", 
            "深圳": "101280600", "杭州": "101210100", "成都": "101270100"
        }
        # 💡 注册 Response 监听器：拦截 BOSS 核心数据包
        self.page.on("response", self._intercept_response)

    def close(self):
        try: self.page.close()
        except: pass

    def _intercept_response(self, response):
        url = response.url
        # 拦截 BOSS 的 joblist 核心接口
        if "joblist.json" in url or "job/list" in url:
            try:
                payload = response.json()
                job_list = payload.get("zpData", {}).get("jobList", [])
                for j in job_list:
                    job_id = j.get("jobId")
                    title = j.get("jobName")
                    comp_name = j.get("brandName")
                    salary = j.get("salaryDesc") or "薪资面议"
                    city_name = j.get("cityName") or "未知"
                    raw_text_block = f"""
                    【渠道：BOSS直聘】
                    公司名称：{comp_name}
                    职位名称：{title}
                    薪资标准：{salary}
                    工作城市：{city_name}
                    学历经历：{j.get('skills', []) or j.get('experienceName', '不限')}
                    职位诱惑：{j.get('jobExperience', '')} / {j.get('postDescription', '暂无详细描述')}
                    """
                    self.captured_jobs.append({
                        "url": f"https://www.zhipin.com/job_detail/{job_id}.html" if job_id else url,
                        "title": title or "未知岗位",
                        "raw_text": raw_text_block.strip(),
                        "source": "BOSS直聘"
                    })
            except Exception as e:
                console.print(f"[dim]⚠️ [Boss] 拦截解析异常: {url[:60]} - {str(e)}[/dim]")
                pass

    def scrape_keyword(self, keyword, city, progress_callback):
        self.captured_jobs = []
        city_code = self.city_map.get(city, "100010000")
        try:
            # 真人零重载路由：避免多余全页刷新
            on_search_page = "zhipin.com/web/geek/job" in self.page.url
            if city != self.current_city or not on_search_page:
                progress_callback(f"🌐 [BOSS战线] 📌 正在切入 [ {city} ] 专属频道...")
                search_url = f"https://www.zhipin.com/web/geek/job?city={city_code}"
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=18000)
                self.current_city = city
                time.sleep(2.0)
            # 安全过盾检查
            is_shield_visible = self.page.locator(".login-box, .verify-wrap, #slide-box, [class*='login-panel']").first.is_visible(timeout=1000)
            if "login" in self.page.url or is_shield_visible:
                progress_callback("🔑 [BOSS战线] 🚨 触发了BOSS安全人机验证！已冷冻挂起，请手动完成滑块解锁或登录...")
                login_timeout = 180  
                logged_in = False
                for i in range(login_timeout):
                    try:
                        is_active_shield = self.page.locator(".login-box, .verify-wrap, #slide-box, [class*='login-panel']").first.is_visible(timeout=500)
                    except:
                        is_active_shield = False
                    if not is_active_shield and "login" not in self.page.url:
                        logged_in = True
                        progress_callback("🎉 [BOSS战线] 🟢 过盾成功，已安全恢复全自动打捞...")
                        time.sleep(2)
                        break
                    time.sleep(1)
                if not logged_in:
                    return []

            # 模拟键盘输入（Vue/React 零失真操作）
            search_input = self.page.locator("input[placeholder*='搜索职位'], input[name='query']").first
            if search_input.is_visible(timeout=3000):
                search_input.click()
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
                self.page.keyboard.press("Meta+A")
                self.page.keyboard.press("Backspace")
                time.sleep(0.1)
                for char in keyword:
                    self.page.keyboard.type(char)
                    time.sleep(random.uniform(0.03, 0.1))
                self.page.keyboard.press("Enter")
                # 给予足够的 XHR 加载与拦截延迟
                time.sleep(4.0)

        except Exception as e:
            console.print(f"[red]❌ [BOSS直聘] 抓取异常: {str(e)}[/red]")
        return self.captured_jobs

# ================= 🔍 侦察兵 3：AI 官网 (Moka & 飞书 API 直接监听) =================

class AIOfficialSiteScout(BaseScout):
    """AI领域企业官网直招哨兵 (直接截取 Moka / 飞书招聘 JSON API数据)"""
    def start(self, browser_context):
        self.context = browser_context
        # 物理对齐企业真实托管系统底层 URL
        self.target_companies = [
            {"name": "月之暗面 (Moonshot AI)", "url": "https://app.mokahr.com/apply/moonshot/148506#/jobs", "type": "moka"},
            {"name": "智谱 AI (Zhipu AI)", "url": "https://app.mokahr.com/social-recruitment/zphz/148983?locale=zh-CN#/jobs", "type": "moka"},
            {"name": "深度求索 (DeepSeek)", "url": "https://app.mokahr.com/social-recruitment/high-flyer/140576#/", "type": "moka"},
            {"name": "MiniMax", "url": "https://vrfi1sk8a0.jobs.feishu.cn/index/", "type": "feishu"},
            {"name": "百川智能 (Baichuan AI)", "url": "https://cq6qe6bvfr6.jobs.feishu.cn/baichuanzhaopin", "type": "feishu"},
            {"name": "生数科技", "url": "https://shengshu.jobs.feishu.cn/index/position/list?location=CT_11", "type": "feishu"}
        ]

    def scrape_keyword(self, keyword, city, progress_callback):
        results = []
        progress_callback("🌐 [AI官网战线] 正在启动静默沙盒，劫持各大 AI 实验室底层招聘接口...")
        for comp in self.target_companies:
            progress_callback(f"🔎 [AI官网战线] 正在穿透动态端口: {comp['name']} ...")
            temp_page = self.context.new_page()
            captured_api_jobs = []
            # 💡 工厂函数：正确捕获当前迭代的 comp 和列表变量（修掉闭包变量陷阱）
            def make_on_response(c, jobs_list):
                def on_response(response):
                    url = response.url
                    try:
                        # A. MokaHR API 拦截
                        if "api/v1/jobs" in url or "social-recruitment/api" in url:
                            payload = response.json()
                            jobs = payload.get("data", {}).get("jobs", []) or payload.get("jobs", [])
                            for j in (jobs or []):
                                if j is None:
                                    continue
                                title = j.get("title") or j.get("name")
                                city_name = j.get("location") or j.get("city", {}).get("name") or "未知"
                                summary = j.get("summary") or j.get("description", "")
                                jobs_list.append({
                                    "title": title,
                                    "raw_text": f"【官网Moka | {c['name']}】\n公司：{c['name']}\n岗位：{title}\n地点：{city_name}\n详情：{summary}".strip(),
                                    "url": c["url"],
                                    "source": c["name"]
                                })
                        # B. 飞书招聘 API 拦截
                        elif "search/job/posts" in url or "position/list" in url:
                            payload = response.json()
                            job_list = payload.get("data", {}).get("job_post_list", []) or payload.get("posts", [])
                            for j in (job_list or []):
                                if j is None:
                                    continue
                                title = j.get("title")
                                city_name = j.get("city_info", {}).get("name") or j.get("city", "未知")
                                summary = j.get("description", "")
                                jobs_list.append({
                                    "title": title,
                                    "raw_text": f"【官网飞书 | {c['name']}】\n公司：{c['name']}\n岗位：{title}\n地点：{city_name}\n详情：{summary}".strip(),
                                    "url": c["url"],
                                    "source": c["name"]
                                })
                    except Exception as e:
                        console.print(f"[dim]⚠️ [AI官网] API拦截解析异常 ({c['name']}): {str(e)[:80]}[/dim]")
                return on_response

            temp_page.on("response", make_on_response(comp, captured_api_jobs))
            try:
                temp_page.goto(comp["url"], wait_until="domcontentloaded", timeout=12000)
                # 等待 SPA 异步请求完成
                try:
                    temp_page.wait_for_load_state("networkidle", timeout=8000)
                except:
                    pass
                time.sleep(4.0)
                # 📌 方法2：从渲染后的 DOM 直接提取岗位（API 拦截的兜底方案）
                try:
                    html = temp_page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    # 尝试多种常见 CSS 选择器匹配岗位卡片
                    dom_selectors = [
                        ".job-list-item a[href*='job']", "a[class*='job-title']",
                        "[class*='job-list'] [class*='item'] a", "[class*='position-list'] [class*='name']",
                        ".post-title a", "[class*='position'] [class*='title'] a",
                        "a[href*='position']", "a[href*='job']",
                    ]
                    seen_titles = set()
                    for sel in dom_selectors:
                        for elem in soup.select(sel):
                            title = elem.get_text().strip()
                            href = elem.get("href", "")
                            if title and len(title) >= 3 and title not in seen_titles:
                                seen_titles.add(title)
                                if href and not href.startswith("http") or href.startswith("/"):
                                    href = href.split("?")[0]
                                    if href.startswith("/"):
                                        base_url = comp["url"].split("/index")[0] if "/index" in comp["url"] else comp["url"].rstrip("/")
                                        href = base_url + href
                                    else:
                                        href = comp["url"].split("/apply")[0] + "/apply" + href if "/apply" in comp["url"] else href
                                # 只保留有真实详情链接的岗位，防止跳转回列表页
                                if href and "javascript" not in href and href != comp["url"]:
                                    captured_api_jobs.append({
                                        "title": title,
                                        "raw_text": f"【官网 | {comp['name']}】\n公司：{comp['name']}\n岗位：{title}\n地点：全国\nURL：{href}".strip(),
                                        "url": href,
                                        "source": comp["name"]
                                    })
                except Exception as dom_e:
                    console.print(f"[dim]⚠️ [AI官网] DOM提取异常 ({comp['name']}): {str(dom_e)[:80]}[/dim]")
                # 对捕获的岗位做模糊匹配过滤
                console.print(f"[dim]📊 [AI官网] {comp['name']}: API+DOM 共捕获 {len(captured_api_jobs)} 个岗位[/dim]")
                for api_job in captured_api_jobs:
                    if not api_job.get("title"):
                        continue
                    match_score = fuzz.partial_ratio(keyword.lower(), api_job["title"].lower())
                    if match_score > 70:
                        results.append(api_job)
            except Exception as e:
                console.print(f"[yellow]⚠️ [AI官网] 扫描 {comp['name']} 失败: {str(e)}[/yellow]")
            finally:
                try: temp_page.close()
                except: pass
        if not results:
            progress_callback("⚠️ [AI官网战线] 所有公司均未捕获到匹配岗位，可能页面结构有变")
        return results

# ================= 🔍 侦察兵 4：AI 极客垂类招聘社区 =================

class AIVerticalScout(BaseScout):
    """AI极客、程序员黄金垂类招聘社区侦察兵 (直取 V2EX Jobs 节点)"""
    def start(self, browser_context):
        self.page = browser_context.new_page()

    def close(self):
        try: self.page.close()
        except: pass

    def scrape_keyword(self, keyword, city, progress_callback):
        results = []
        progress_callback(f"🌐 [AI极客垂类战线] 正在深度检索 V2EX 程序员招聘专区...")
        try:
            self.page.goto("https://www.v2ex.com/go/jobs", wait_until="domcontentloaded", timeout=15000)
            time.sleep(2.0)
            html_content = self.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            topic_cells = soup.select("table td.cell, .box .cell")
            target_links = []
            for cell in topic_cells:
                title_link = cell.select_one(".topic-link")
                if title_link:
                    title_text = title_link.get_text().strip()
                    url = title_link.get("href", "")
                    if url and not url.startswith("http"):
                        url = "https://www.v2ex.com" + url
                    # 💡 使用 fuzz 局部比对，过滤出含有 AI / 远程 / 技术关键词的主题
                    title_score = fuzz.partial_ratio(keyword.lower(), title_text.lower())
                    if title_score > 70 or "ai" in title_text.lower() or "大模型" in title_text:
                        if city == "全国" or city in title_text or "远程" in title_text or "不限" in title_text:
                            target_links.append({"title": title_text, "url": url})
            # 穿透前 3 个主题提取正文
            for item in target_links[:3]:
                progress_callback(f"🔎 [AI极客垂类战线] 正在深度抓取帖子详情: [ {item['title'][:15]}... ]")
                try:
                    self.page.goto(item["url"], wait_until="domcontentloaded", timeout=10000)
                    time.sleep(1.5)
                    topic_content = self.page.locator(".topic_content").first
                    if topic_content.is_visible(timeout=2000):
                        raw_text = topic_content.inner_text().strip()
                        if len(raw_text) > 40:
                            results.append({
                                "url": item["url"],
                                "raw_text": f"【V2EX 社区招聘】\n标题：{item['title']}\n详情：{raw_text}",
                                "source": "V2EX 社区"
                            })
                except Exception as inner_e:
                    pass
        except Exception as e:
            console.print(f"[red]❌ [AI垂类招聘战线] 抓取异常: {str(e)}[/red]")
        return results

# ================= 🔍 侦察兵 5：香港招聘平台 (JobsDB / CTgoodjobs / Indeed) =================

class HKJobScout(BaseScout):
    """香港招聘平台侦察兵"""
    def __init__(self):
        super().__init__()
        self.platforms = [
            {"name": "JobsDB HK", "url": "https://hk.jobsdb.com/hk/search-jobs/{}",
             "selectors": ["a[href*='/job/']", "a[href*='jobsdb']", "h3[class*='title'] a"],
             "domain": "https://hk.jobsdb.com"},
            {"name": "CTgoodjobs", "url": "https://www.ctgoodjobs.hk/search/?keywords={}",
             "selectors": ["a[href*='/job/']", "a[class*='job-title']", "a[href*='ctgoodjobs']"],
             "domain": "https://www.ctgoodjobs.hk"},
            {"name": "Indeed HK", "url": "https://hk.indeed.com/jobs?q={}",
             "selectors": ["a[href*='/rc/']", "h2 a[href*='clk']", "a.jcs-JobTitle"],
             "domain": "https://hk.indeed.com"},
        ]

    def start(self, browser_context):
        self.context = browser_context

    def scrape_keyword(self, keyword, city, progress_callback):
        results = []
        import urllib.parse
        for p in self.platforms:
            try:
                search_url = p["url"].format(urllib.parse.quote(keyword))
                page = self.context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                progress_callback(f"\ud83c\udf0d [{p['name']}] 搜索: {keyword[:20]}")
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(2.0)
                console.print(f"[dim]\ud83d\udccd [{p['name']}] URL: {search_url[:80]} | Title: {page.title()[:60]}[/dim]")
                html = page.content()
                console.print(f"[dim]  HTML 长度: {len(html)} 字符[/dim]")
                soup = BeautifulSoup(html, 'html.parser')
                seen = set()
                for sel in p["selectors"]:
                    matches = soup.select(sel)
                    if matches:
                        console.print(f"[dim]    \ud83d\udd0d 选择器 '{sel}' 命中 {len(matches)} 个[/dim]")
                    for elem in matches:
                        title = elem.get_text().strip()
                        href = elem.get("href", "")
                        if title and len(title) >= 3 and title not in seen:
                            seen.add(title)
                            if href and not href.startswith("http"):
                                href = p["domain"] + href
                            results.append({
                                "url": href,
                                "title": title,
                                "raw_text": f"【{p['name']}】\n城市：香港\n岗位：{title}".strip(),
                                "source": p["name"]
                            })
                page.close()
            except Exception as e:
                console.print(f"[red]\u274c [{p['name']}] 抓取异常: {str(e)}[/red]")
        if results:
            console.print(f"[green]\u2705 香港平台共捕获 {len(results)} 个岗位[/green]")
        else:
            console.print(f"[yellow]\u26a0\ufe0f 香港平台未捕获任何岗位，请检查终端日志[/yellow]")
        return results


# ================= 🧠 核心猎头调度中枢 =================

class HunterAgent:
    def __init__(self, client, model, candidate, path_result, target_cities=None):
        self.client = client
        self.model = model
        self.candidate = candidate
        self.path_result = path_result
        self.target_cities = target_cities if target_cities else ["北京"]  
        self.missions = self._generate_missions()
        self.db_dir = os.path.join(os.path.dirname(current_dir), "data")
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_path = os.path.join(self.db_dir, "scouted_jobs.json")
        # 💡 创建本地化专属配置持久沙盒，保障一次登录，万次免登
        self.user_data_dir = os.path.join(self.db_dir, "browser_user_data")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.scouts = [
            LiepinScout(),
            BossScout(),
            AIOfficialSiteScout(),
            AIVerticalScout(),
            HKJobScout()
        ]

    def _generate_missions(self):
        missions = []
        # 💡 修复：优先使用用户在 UI 选定的攻坚路径（path_result），再降级到 profile
        raw_keywords = []
        # 第一优先级：path_result（用户在 app.py 选择的路线）
        if self.path_result and 'paths' in self.path_result:
            for p in self.path_result['paths']:
                raw_keywords.extend(p.get('search_keywords', []))
        # 第二优先级：profile 中的 suggested_paths（多条路线合并）
        if not raw_keywords:
            suggested_paths = self.candidate.get('suggested_paths', [])
            if suggested_paths:
                for p in suggested_paths:
                    raw_keywords.extend(p.get('search_keywords', []))
        # 第三优先级：兼容旧版 selected_path（支持 keywords 和 search_keywords 两种 key）
        if not raw_keywords and 'selected_path' in self.candidate:
            sel = self.candidate['selected_path']
            raw_keywords.extend(sel.get('keywords', []) or sel.get('search_keywords', []))
        # 终极降级：硬编码默认词
        if not raw_keywords:
            raw_keywords = ["AI工程化", "大模型后端"]
        expanded_keys = generate_job_keywords(raw_keywords)
        noise_suffixes = ["招聘", "岗位", "职位", "求职", "分布", "方向", "大厂"]
        blacklist_roles = ["专员", "助理", "实习生", "兼职", "校招", "应届", "猎头", "人事", "hr"]
        seen = set()
        for key in expanded_keys:
            if not key: continue
            cleaned_key = key
            for suffix in noise_suffixes:
                cleaned_key = cleaned_key.replace(suffix, "")
            cleaned_key = cleaned_key.strip()
            if any(b in cleaned_key.lower() for b in blacklist_roles): continue
            if cleaned_key and len(cleaned_key) >= 2 and cleaned_key not in seen:
                seen.add(cleaned_key)
                missions.append({"keyword": cleaned_key})
        return missions

    def _parse_salary_info(self, text):
        match_k = re.search(r'(\d+)-(\d+)[kK]', text)
        if match_k:
            return int(match_k.group(2)), match_k.group(0)
        match_w = re.search(r'(\d+)-(\d+)万', text)
        if match_w:
            return int(match_w.group(2)) * 12, match_w.group(0)
        return 0, "薪资面议"

    def _ai_evaluate_match(self, jd_text):
        assets = self.candidate.get('atomic_assets', [])
        assets_str = "\n".join([f"- {a}" for a in assets])
        if not assets_str.strip():
            return {"is_low_quality_or_misplaced": False, "reject_reason": "None", "score": 60, "reason": "无原子资产，默认给予基础分"}
        bt = chr(96) * 3
        prompt = f"""你是一位从业15年的铁血资深行业老猎头。请根据求职者【原子资产】，对以下【招聘JD】进行严苛的匹配度与【社招含金量/风险避坑】审计。
        【求职者核心原子资产】：
        {assets_str}
        【招聘JD及页面原始文本】：
        {jd_text}
        ---
        🔍 猎头专业审计指引：
        1. 【校招/初阶错配判定】：出现"面向2025/2026届"、"接受应届生"、"助理/实习生"直接判定错配。
        2. 【虚假/僵尸岗研判】：发布时间极旧或职责空泛判定为僵尸岗。
        3. 【高流动性/炮灰岗研判】：强调极端抗压、一个人干一个团队的活判定为大坑。

        必须以合法的 JSON 格式返回结果，严禁包含任何 Markdown 代码块标记（如 {bt}json），结构必须如下：
        {{
          "is_low_quality_or_misplaced": true,
          "reject_reason": "原因说明",
          "score": 85,
          "reason": "匹配点评"
        }}
        """
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            content = res.choices[0].message.content.strip()
            if bt in content: content = re.search(r'\{.*\}', content, re.DOTALL).group()
            return json.loads(content)
        except Exception as e:
            console.print(f"[yellow]⚠️ AI 评估解析失败: {str(e)[:100]}[/yellow]")
            return {"is_low_quality_or_misplaced": False, "reject_reason": "None", "score": 50, "reason": "AI 解析失败，默认保留"}

    def _save_to_local_database(self, jobs):
        existing_jobs = {}
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    old_list = json.load(f)
                    existing_jobs = {j['url']: j for j in old_list}
            except Exception as e:
                console.print(f"[dim]⚠️ 读取 scouted_jobs.json 异常: {str(e)[:80]}[/dim]")
                pass
        for j in jobs:
            # 只保存有完整 JD 描述的岗位（DOM 提取的无 JD 岗位不存库）
            if len(j.get('raw_text', '')) < 100:
                continue
            if j['url'] not in existing_jobs:
                existing_jobs[j['url']] = {
                    "url": j['url'],
                    "title": j['title'],
                    "score": j['score'],
                    "reason": j['reason'],
                    "city": j.get('city', '未知'),
                    "salary_text": j.get('salary_text', '面议'),
                    "salary_max": j.get('salary_max', 0),
                    "raw_text": j.get('raw_text', ''),
                    "scouted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "👀 待投递",
                    "source": j.get("source", "未知渠道")
                }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(list(existing_jobs.values()), f, ensure_ascii=False, indent=2)

    def run_scout_loop(self, progress_callback=None):
        if not self.missions:
            console.print("[red]❌ 没有扫街任务，检查 _generate_missions[/red]")
            if progress_callback:
                progress_callback("❌ 未生成任何扫街任务，请检查档案中的关键词配置")
            return []
        final_graded_jobs = []
        total_missions = len(self.missions)
        console.print(f"[cyan]🚀 开始全网扫街: {total_missions} 个任务, {len(self.scouts)} 个侦察兵, 城市: {self.target_cities}[/cyan]")
        metrics = {"total_scanned_jds": 0, "rejected_count": 0, "kept_count": 0}
        if total_missions == 0: return []
        start_time = time.time()
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                timeout=60000
            )
            # 为各个 Scout 传入 context
            for scout in self.scouts:
                scout.start(context)
            try:
                for idx, mission in enumerate(self.missions, 1):
                    key = mission['keyword']
                    elapsed_seconds = time.time() - start_time
                    eta_str = f"{int((elapsed_seconds / (idx - 1)) * (total_missions - idx + 1))}秒" if idx > 1 else "计算中..."
                    bar = '█' * int(15 * idx // total_missions) + '░' * (15 - int(15 * idx // total_missions))
                    def dashboard_logger(step_detail):
                        if progress_callback:
                            progress_callback(
                                f"📊 **社招全网扫街持久化监控大屏** \n"
                                f"进度: `[{bar}] {int((idx/total_missions)*100)}%` ({idx}/{total_missions})\n"
                                f"⏱️ 预估剩余时间: `{eta_str}` | 当前扫荡岗位词: [ **{key}** ]\n"
                                f"📍 目标限定城市: `{', '.join(self.target_cities) if self.target_cities else '未限定'}`\n"
                                f"📈 实时战报: 已审计 `{metrics['total_scanned_jds']}` | 🛑 拦截(含异地错配) `{metrics['rejected_count']}` | 💎 留存优质岗 `{metrics['kept_count']}`\n\n"
                                f"➔ 🔍 *状态细节: {step_detail}*"
                            )

                    captured_jobs = []
                    for scout in self.scouts:
                        if isinstance(scout, (AIOfficialSiteScout, AIVerticalScout, HKJobScout)):
                            # 官网与极客社区等无硬性区域前置，由其内部拦截器模糊判断
                            captured_jobs.extend(scout.scrape_keyword(key, "全国", dashboard_logger))
                        else:
                            for city in self.target_cities:
                                captured_jobs.extend(scout.scrape_keyword(key, city, dashboard_logger))
                    console.print(f"[dim]📊 关键词 '{key}' 各渠道共捕获 {len(captured_jobs)} 个原始岗位[/dim]")
                    if progress_callback:
                        progress_callback(f"📊 关键词 [{key}] 捕获 {len(captured_jobs)} 个原始岗位，正在进行 AI 匹配度审计...")
                    for j_idx, job in enumerate(captured_jobs, 1):
                        metrics['total_scanned_jds'] += 1
                        card_text = job['raw_text']
                        # 城市后置硬过滤：官网来源和 V2EX 不走城市过滤，猎聘/Boss 走严格的
                        if self.target_cities and ("官网" not in card_text and "V2EX" not in card_text and "猎聘" not in card_text and "BOSS" not in card_text):
                            if not any(city in card_text for city in self.target_cities):
                                metrics['rejected_count'] += 1
                                continue 
                        detected_city = "未知"
                        for city in ["北京", "上海", "深圳", "广州", "杭州", "成都", "香港"]:
                            if city in card_text:
                                detected_city = city
                                break
                        if detected_city == "未知" and self.target_cities:
                            detected_city = self.target_cities[0]
                        salary_max, salary_text = self._parse_salary_info(card_text)
                        # 📌 短文本岗位：用关键词匹配快速筛选（不进 AI 评估，省时间）
                        #    留存岗位等循环结束后再补 JD + 重评分
                        if len(card_text) < 100:
                            _title = (job.get("title", "") or "").lower()
                            _industry_kw = ["ai", "人工智能", "大模型", "金融", "金融科技",
                                            "科技", "智能", "数字化", "云", "saas", "软件",
                                            "技术", "数据", "算法"]
                            _role_kw = ["销售", "客户成功", "bd", "商务", "解决方案",
                                        "产品", "运营", "经理", "专家", "总监"]
                            _has_industry = any(k in _title for k in _industry_kw)
                            _has_role = any(k in _title for k in _role_kw)
                            if _has_industry and _has_role:
                                evaluation = {"is_low_quality_or_misplaced": False, "score": 58,
                                              "reason": "AI/金融方向相关岗位"}
                            elif _has_role:
                                evaluation = {"is_low_quality_or_misplaced": False, "score": 50,
                                              "reason": "岗位名称相关，行业方向待确认"}
                            else:
                                evaluation = {"is_low_quality_or_misplaced": True, "score": 20,
                                              "reason": f"岗位不匹配（{_title[:20]}）"}
                        else:
                            evaluation = self._ai_evaluate_match(card_text)
                        if evaluation.get('is_low_quality_or_misplaced', False):
                            metrics['rejected_count'] += 1
                            continue
                        if evaluation.get('score', 0) >= 55:
                            metrics['kept_count'] += 1
                            raw_title = job.get("title", "") or card_text.split(chr(92)+"n")[0][:30].strip()
                            final_graded_jobs.append({
                                "url": job['url'],
                                "title": raw_title if raw_title else f"{key} 相关岗位",
                                "score": evaluation['score'],
                                "reason": evaluation['reason'],
                                "city": detected_city,          
                                "salary_text": salary_text,    
                                "salary_max": salary_max,      
                                "raw_text": card_text,
                                "source": job.get("source", "未知渠道")
                            })

                # 🔍 补全短文本岗位的 JD 详情并重新 AI 评分
                _to_enrich = [j for j in final_graded_jobs if len(j.get('raw_text', '')) < 100]
                _to_reeval = []
                if _to_enrich:
                    console.print(f"[cyan]🔍 正在补全 {len(_to_enrich)} 个短文本岗位的 JD 详情...[/cyan]")
                    if progress_callback:
                        progress_callback(f"🔍 补全 JD 详情: 0/{len(_to_enrich)}")
                    for _idx, _ej in enumerate(_to_enrich, 1):
                        try:
                            _dp = context.new_page()
                            _dp.goto(_ej['url'], wait_until="domcontentloaded", timeout=15000)
                            time.sleep(1.5)
                            _pt = _dp.locator("body").inner_text(timeout=3000)
                            if len(_pt) > len(_ej.get('raw_text', '')):
                                _ej['raw_text'] = _pt[:3000]
                                _to_reeval.append(_ej)
                            _dp.close()
                        except:
                            pass
                        if progress_callback and _idx % 10 == 0:
                            progress_callback(f"🔍 补全 JD 详情: {_idx}/{len(_to_enrich)}")
                # 重新 AI 评分：所有补完 JD 的岗位统一走 AI，覆盖关键词分数
                _to_reeval = [j for j in final_graded_jobs 
                             if len(j.get('raw_text', '')) >= 100]
                if _to_reeval:
                    _m = getattr(self, 'model', '?')
                    console.print(f"[cyan]🤖 AI 评估: 模型={_m}, 岗位数={len(_to_reeval)}[/cyan]")
                    if progress_callback:
                        progress_callback(f"🤖 AI 评估 ({_m}): 0/{len(_to_reeval)}")
                    for _idx, _ej in enumerate(_to_reeval, 1):
                        _reval = self._ai_evaluate_match(_ej['raw_text'])
                        _ej['score'] = _reval.get('score', _ej['score'])
                        _ej['reason'] = _reval.get('reason', _ej['reason'])
                        if progress_callback and _idx % 5 == 0:
                            progress_callback(f"🤖 AI 复评: {_idx}/{len(_to_reeval)}")
                    # 二次过滤
                    before = len(final_graded_jobs)
                    final_graded_jobs = [j for j in final_graded_jobs if j.get('score', 0) >= 55]
                    after = len(final_graded_jobs)
                    metrics['kept_count'] = after
                    if before != after:
                        console.print(f"[yellow]⚠️ 二次过滤移除了 {before - after} 个低分岗位[/yellow]")
                
                console.print(f"[cyan]📈 扫街完成: 审计 {metrics['total_scanned_jds']} | 拦截 {metrics['rejected_count']} | 留存 {metrics['kept_count']}[/cyan]")
            finally:
                for scout in self.scouts:
                    scout.close()
                context.close()
        self._save_to_local_database(final_graded_jobs)
        return final_graded_jobs
