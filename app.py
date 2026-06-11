# app.py
import streamlit as st
import json
import os
import sys
import re
import time
import openai

# --- 核心拉通：把当前目录 and services 目录都加入系统路径 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
services_dir = os.path.join(current_dir, 'services')

if current_dir not in sys.path:
    sys.path.append(current_dir)
if services_dir not in sys.path:
    sys.path.append(services_dir)

from onboarding import render_onboarding
from services.huntagent import HunterAgent

# ── 1. 基础页面配置与初始化 ──────────────────────────────────────
st.set_page_config(page_title="ZenHunter Lab", layout="wide")

# 初始化默认本地客户端
if "client" not in st.session_state:
    st.session_state.client = openai.OpenAI(
        base_url='http://localhost:11434/v1', 
        api_key='ollama'
    )
client = st.session_state.client

if 'current_user_idx' not in st.session_state:
    st.session_state.current_user_idx = 0

if "last_user_idx" not in st.session_state:
    st.session_state.last_user_idx = st.session_state.current_user_idx

if "scan_results" not in st.session_state:
    st.session_state.scan_results = []

# ── 2. 侧边栏档案选择与云端密钥管理 ──────────────────────────────────
with st.sidebar:
    st.title("👨‍💻 职业经纪人面板")
    
    # 💡 云端大模型 API Key 配置舱
    with st.expander("🌐 云端商业模型密匙舱 (无本地硬件时启用)", expanded=False):
        st.caption("电脑带不动 14B 模型？可在此配置在线 Token。支持随用随填：")
        openai_key = st.text_input("OpenAI API Key:", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        deepseek_key = st.text_input("DeepSeek Cloud Key:", type="password", value=os.getenv("DEEPSEEK_API_KEY", ""))
        gemini_key = st.text_input("Gemini API Key:", type="password", value=os.getenv("GEMINI_API_KEY", ""))
        qwen_key = st.text_input("Qwen Cloud Key (DashScope):", type="password", value=os.getenv("QWEN_API_KEY", ""))
        
        st.divider()
        st.caption("📧 邮箱报告配置（可选）：")
        st.session_state["smtp_host"] = st.text_input("SMTP 服务器", value="smtp.qq.com", help="QQ邮箱: smtp.qq.com, 163: smtp.163.com")
        st.session_state["smtp_port"] = st.text_input("SMTP 端口", value="465")
        st.session_state["smtp_user"] = st.text_input("邮箱账号", placeholder="your@qq.com")
        st.session_state["smtp_pass"] = st.text_input("SMTP 授权码", type="password", help="QQ邮箱需开启SMTP服务获取授权码，不是登录密码")
        st.session_state["report_email"] = st.text_input("接收报告的邮箱", placeholder="接收报告的邮箱地址")
        
        # 存入 Session 状态机供 Tab 2 动态抓取
        st.session_state["openai_key"] = openai_key
        st.session_state["deepseek_key"] = deepseek_key
        st.session_state["gemini_key"] = gemini_key
        st.session_state["qwen_key"] = qwen_key

    st.divider()
    
    # 动态加载本地 profile.json 档案库
    if "profile" not in st.session_state:
        if os.path.exists('profile.json'):
            try:
                with open('profile.json', 'r', encoding='utf-8') as f:
                    st.session_state.profile = json.load(f)
            except:
                st.session_state.profile = {"candidates": []}
        else:
            st.session_state.profile = {"candidates": []}
    
    candidates = st.session_state.profile.get('candidates', [])
    
    st.markdown("### 🗂️ 候选人历史档案检索")
    if candidates:
        if st.session_state.current_user_idx >= len(candidates):
            st.session_state.current_user_idx = 0
            
        sel_idx = st.selectbox(
            "选择当前要对标的操作档案：", 
            range(len(candidates)),
            index=st.session_state.current_user_idx,
            format_func=lambda i: candidates[i].get('name', f"档案 {i}")
        )
        st.session_state.current_user_idx = sel_idx
        curr_candidate = candidates[sel_idx]
        
        # 🛡️ 换人时重载历史留存岗位并清除过往重构缓存，防止跨档案污染
        if st.session_state.current_user_idx != st.session_state.last_user_idx:
            st.session_state.scan_results = curr_candidate.get('scouted_jobs', [])
            st.session_state.last_user_idx = st.session_state.current_user_idx
            st.session_state.has_just_scanned = False
            
        if not st.session_state.scan_results and "scouted_jobs" in curr_candidate:
            st.session_state.scan_results = curr_candidate.get('scouted_jobs', [])
        
        # 侧边栏快捷资产缩略看板
        st.divider()
        st.success(f"⚡ 已加载: {curr_candidate.get('type', '未知定位')}")
        with st.expander("🔍 档案中锁定的原子资产事实"):
            for asset in curr_candidate.get('atomic_assets', []):
                st.caption(f"• {asset}")
    else:
        curr_candidate = None
        st.info("💡 尚未录入任何操作档案，请先前往「💡 深度访谈」通过4大Skill模块与AI经纪人共创。")

# ── 3. 主界面多签页控制流 ──────────────────────────────────────────
tab0, tab1, tab2 = st.tabs(["💡 深度访谈 (4大Skill共创)", "🔍 市场对标/一键扫街", "📝 终极简历工坊(全文重构)"])

# --- Tab 0: 访谈工作坊 ---
with tab0:
    render_onboarding()

# --- Tab 1: 全自动扫街对标 (融合高规格生涯规划判决书) ---
with tab1:
    if curr_candidate:
        # ==========================================
        # 🏆 AI 铁血猎头生涯裁定与战略报告 (核心新增)
        # ==========================================
        market_verdict = curr_candidate.get('market_verdict', {})
        suggested_paths = curr_candidate.get('suggested_paths', [])
        
        if market_verdict or suggested_paths:
            st.markdown("#### 🏆 AI 铁血猎头生涯估值与战略大屏")
            
            # 首屏一句话溢价定位
            sellable_as = market_verdict.get('sellable_as', '暂无一句话市场包装定位')
            st.info(f"🕵️ **猎头高溢价推销定位**：\n「 {sellable_as} 」")
            
            col_v1, col_v2 = st.columns([1, 1])
            with col_v1:
                # 市场客观估值
                st.metric(
                    label="💰 当前市场身价/段位天花板",
                    value=market_verdict.get('price_ceiling', '估值计算中'),
                    help="AI 根据当前市场上万个同类型技术岗位的 XHR 薪酬统计得出的客观溢价评估"
                )
                fit_stages = ", ".join(market_verdict.get('company_stage_fit', []))
                st.markdown(f"🏢 **最易斩获 Offer 的公司阶段**：`{fit_stages if fit_stages else '未限定'}`")
            
            with col_v2:
                # 🛑 拒信防守话术警告
                st.warning(f"🛑 **HR最可能致命拒绝你的理由**：\n*{market_verdict.get('hardest_objection', '暂无致命硬伤研判')}*")
            
            # 触达能力矩阵
            reachability = market_verdict.get('reachability', {})
            if reachability:
                with st.expander("📊 查看不同体量企业的可触达职级矩阵 (点击展开)", expanded=False):
                    col_r1, col_r2, col_r3 = st.columns(3)
                    with col_r1:
                        st.markdown(f"**🌱 初创公司极限**\n`{reachability.get('startup', 'N/A')}`")
                    with col_r2:
                        st.markdown(f"**🚀 中型独角兽极限**\n`{reachability.get('mid', 'N/A')}`")
                    with col_r3:
                        st.markdown(f"**🏢 头部大厂极限**\n`{reachability.get('large', 'N/A')}`")

            st.divider()

        # ==========================================
        # 🎯 战略攻坚战役路线选择器 (彻底解决 keywords 不对齐报错问题)
        # ==========================================
        st.markdown(f"### 🛰️ 全网活水追踪：正在扫描候选人 `{curr_candidate.get('name', '默认档案')}`")
        
        active_keywords = []
        if suggested_paths:
            # 动态选择攻坚方向
            path_names = [p.get('path_name', '未方向路径') for p in suggested_paths]
            selected_path_name = st.selectbox(
                "🎯 **选择当前执行对标的战略攻坚路线：**",
                options=path_names,
                index=0,
                help="系统将根据选定路线的专属关键词启动全自动多平台扫网！"
            )
            
            # 锁定选定的路线数据
            active_path_data = next(p for p in suggested_paths if p.get('path_name') == selected_path_name)
            
            # 展示溢价研判与可持续性理由
            col_p1, col_v2 = st.columns(2)
            with col_p1:
                st.success(f"💎 **本路线溢价逻辑**：{active_path_data.get('premium_logic', 'N/A')}")
            with col_v2:
                st.info(f"🛡️ **3年后可持续性研判**：{active_path_data.get('sustainability_reason', 'N/A')}")
            
            active_keywords = active_path_data.get('search_keywords', [])
        else:
            # 降级：如果旧版本没有多路线规划，兼容读取旧的 selected_path
            selected_path_data = curr_candidate.get('selected_path', {})
            active_keywords = selected_path_data.get('keywords', []) or selected_path_data.get('search_keywords', [])
            if selected_path_data:
                st.info(f"📌 当前操作路径：`{selected_path_data.get('path_name', '默认路径')}`")
        
        # 将当前路线动态打包装入 legacy_path_result 扔给爬虫
        legacy_path_result = {
            "paths": [{
                "path_name": "当前攻坚方向",
                "search_keywords": active_keywords
            }]
        }
        
        # 展示当前要扫描的关键词，消除黑盒感
        st.write(f"🔍 **本路线激活的爬虫扫描关键词组**：`{', '.join(active_keywords) if active_keywords else '无可用词'}`")

        # 城市过滤
        col_city, _ = st.columns([2, 2])
        with col_city:
            selected_cities = st.multiselect(
                "📍 **目标核心城市范围限定：**",
                options=["北京", "上海", "深圳", "广州", "杭州", "成都"],
                default=["北京", "上海", "深圳"]
            )
        
        st.write("")
        # 一键启动按钮
        if st.button("🚀 启动全网活水扫街 (基于已有档案资产)", type="primary", use_container_width=True):
            status_placeholder = st.empty()
            
            # 🛠️ 核心修复：防御性拦截，如果完全没拿到关键词，做拦截处理
            if not active_keywords:
                st.error("❌ 错误：当前档案缺少目标搜索关键词！请在下方输入框中手动规划或前往 Tab 0 重新访谈归档。")
            else:
                agent = HunterAgent(client, "qwen2.5:14b", curr_candidate, legacy_path_result, target_cities=selected_cities)
                
                with st.spinner("卫星雷达正在扫描检索，并实时利用AI审判目标JD与你原子资产的匹配度..."):
                    final_results = agent.run_scout_loop(progress_callback=status_placeholder.info)
                    
                    # 数据物理存盘
                    st.session_state.scan_results = final_results
                    candidates[st.session_state.current_user_idx]['scouted_jobs'] = final_results
                    st.session_state.has_just_scanned = True 
                    
                    with open('profile.json', 'w', encoding='utf-8') as f:
                        json.dump(st.session_state.profile, f, ensure_ascii=False, indent=4)
                    
                status_placeholder.empty()
                if st.session_state.scan_results:
                    st.balloons()
                    # 📧 报告下载/发送
                    from services.report import generate_report_html
                    _report_html = generate_report_html(
                        st.session_state.scan_results,
                        candidate_name=curr_candidate.get("name", ""),
                    )
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.download_button(
                            label="📥 下载岗位匹配报告",
                            data=_report_html,
                            file_name=f"猎头报告_{curr_candidate.get('name','')}_{time.strftime('%Y%m%d')}.html",
                            mime="text/html",
                            use_container_width=True,
                            key="download_report"
                        )
                    with col_r2:
                        if st.button("📧 发送报告到邮箱", use_container_width=True, key="send_report_btn"):
                            try:
                                from services.report import send_report_via_email
                                smtp_cfg = {
                                    "host": st.session_state.get("smtp_host", "smtp.qq.com"),
                                    "port": st.session_state.get("smtp_port", "465"),
                                    "username": st.session_state.get("smtp_user", ""),
                                    "password": st.session_state.get("smtp_pass", ""),
                                    "from_email": st.session_state.get("smtp_user", ""),
                                    "to_email": st.session_state.get("report_email", ""),
                                }
                                send_report_via_email(_report_html, smtp_cfg)
                                st.success("✅ 报告已发送到邮箱！")
                            except Exception as e:
                                st.error(f"❌ 发送失败: {str(e)[:100]}")
                else:
                    st.warning("⚠️ 全网活水捕获完成，但受限于城市过滤或反爬风控，暂无高度契合岗位。")

        # 渲染捕获岗位
        if st.session_state.scan_results:
            st.divider()
            
            # 🏙 城市筛选器（从已有结果中动态提取城市列表）
            all_cities = sorted(set(job.get('city', '未知') for job in st.session_state.scan_results))
            filter_cities = st.multiselect(
                "📍 按城市筛选结果",
                options=all_cities,
                default=all_cities,
                key="city_filter"
            )
            
            sort_strategy = st.radio(
                "📊 **追踪控制台视图策略调整（本地留存库无感切表，不重跑爬虫）**",
                options=["🎯 按资产匹配度得分降序", "💰 按岗位薪资上限（高薪优先）降序"],
                horizontal=True
            )
            
            display_list = list(st.session_state.scan_results)
            # 城市筛选
            if filter_cities:
                display_list = [j for j in display_list if j.get('city', '未知') in filter_cities]
            if sort_strategy == "🎯 按资产匹配度得分降序":
                display_list = sorted(display_list, key=lambda x: x.get('score', 0), reverse=True)
            else:
                display_list = sorted(display_list, key=lambda x: x.get('salary_max', 0), reverse=True)
            
            for job in display_list:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.metric(label="🎯 资产匹配度", value=f"{job.get('score', 0)}分")
                        st.caption(f"📍 {job.get('city', '未知')} | 💰 {job.get('salary_text', '面议')}")
                        st.caption(f"🏷️ 渠道: `{job.get('source', '未知')}`")
                    with col2:
                        st.markdown(f"🔗 **独立目标岗位详情**: [{job['title']}]({job['url']})")
                        st.write(f"🕵️ **经纪人毒辣研判**: {job['reason']}")
                        
        elif not st.session_state.scan_results and not st.session_state.get('has_just_scanned', False):
            st.info("💡 历史库中暂无留存岗位，请点击上方「启动全网活水扫街」按钮开启自动打捞。")
            
    else:
        st.warning("📭 卫星雷达扫描仓目前为空，无可用档案资产！")

# --- Tab 2: 📝 终极简历工坊 (一岗一策全文智能重构) ---
with tab2:
    st.markdown("### 📝 终极简历工坊：一岗一策直接生成可投递简历")
    if curr_candidate:
        base_resume = curr_candidate.get('base_resume', '')
        
        if not base_resume:
            st.warning("⚠️ 当前档案内未检测到「基础母盘简历」！")
            st.info("提示：因为您使用的是旧档案或手工录入的档案。强烈建议您前往第一个页签「💡 深度访谈」通过一键封档重新生成包含简历母盘的最新档案。")
        else:
            with st.expander("📄 查看已生成的标准母盘简历 (点击展开)", expanded=False):
                st.markdown(base_resume)
                
        scouted_jobs = st.session_state.scan_results
        
        if not scouted_jobs:
            st.warning("📭 当前没有任何留存的扫街岗位资产！")
            st.info("请先前往「🔍 市场对标/一键扫街」标签页启动活水扫街。打捞出岗位后，此处将自动激活专属重构控制面板。")
        else:
            st.markdown("针对猎头系统打捞留存的特定坑位，提取你的 **标准简历底座** 开展全文一岗一策高溢价重编。")
            st.divider()
            
            # 1. 动态岗位选择器
            selected_job_idx = st.selectbox(
                "🎯 1. 选择你当前想要对其投递的目标坑位：",
                range(len(scouted_jobs)),
                format_func=lambda i: f"【{scouted_jobs[i].get('score', 0)}分 | {scouted_jobs[i].get('city', '未知')}】{scouted_jobs[i].get('title', '未知岗位')}"
            )
            target_job = scouted_jobs[selected_job_idx]
            
            # 展示岗位研判事实
            with st.chat_message("assistant"):
                st.markdown(f"🔗 **选定岗位直达**: [{target_job['title']}]({target_job['url']})")
                st.markdown(f"🕵️ **老猎头对该岗位的破局点痛点研判**: {target_job['reason']}")
            
            st.write("")
            
            # 2. 🔌 智能云地路由控制板
            st.markdown("##### 🤖 2. 配置全文重构大脑")
            col_mod1, col_mod2 = st.columns([2, 3])
            with col_mod1:
                model_options = [
                    "qwen2.5:14b (本地)", "deepseek-r1:14b (本地)", "llama3.1:8b (本地)",
                    "gpt-4o (云端在线)", "deepseek-chat (云端在线)", "gemini-1.5-pro (云端在线)",
                    "qwen-max (云端在线)"
                ]
                chosen_model = st.selectbox("当前选用的大模型大脑：", model_options, index=0)
            with col_mod2:
                st.caption("💡 **重构大脑推荐**：\n"
                           "* **本地党**：首选 `qwen2.5:14b`（其中文大厂格式极其饱满端庄）。\n"
                           "* **云端党**：首选 `gpt-4o` 或 `deepseek-chat`（针对高管、跨国、金融科技背景的语义包装极度丝滑）。")
            
            # 3. 🧠 混合动力路由请求引擎（执行全文重写重构）
            if st.button(f"🚀 启动全文高阶简历重构", type="primary", use_container_width=True):
                if not base_resume:
                    st.error("❌ 错误：检测不到任何母盘底稿，AI 无法凭空重构，请去 Tab 0 访谈一键归档。")
                else:
                    with st.spinner(f"📡 正在拉取「标准母盘简历」，结合目标JD的隐性痛点，为您重新熔炼全文..."):
                        try:
                            # ── 核心智能网关分流器 ──
                            if "gpt-4o" in chosen_model:
                                key = st.session_state.get("openai_key")
                                if not key:
                                    st.error("🔑 错误：检测到您未在左侧栏「云端商业模型密匙舱」中填写 OpenAI API Key！")
                                    st.stop()
                                run_client = openai.OpenAI(base_url="https://api.openai.com/v1", api_key=key)
                                run_model = "gpt-4o"
                            
                            elif "deepseek-chat" in chosen_model:
                                key = st.session_state.get("deepseek_key")
                                if not key:
                                    st.error("🔑 错误：检测到您未在左侧栏「云端商业模型密匙舱」中填写 DeepSeek Cloud Key！")
                                    st.stop()
                                run_client = openai.OpenAI(base_url="https://api.deepseek.com/v1", api_key=key)
                                run_model = "deepseek-chat"
                                
                            elif "gemini" in chosen_model:
                                key = st.session_state.get("gemini_key")
                                if not key:
                                    st.error("🔑 错误：检测到您未在左侧栏「云端商业模型密匙舱」中填写 Gemini API Key！")
                                    st.stop()
                                run_client = openai.OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=key)
                                run_model = "gemini-1.5-pro"

                            elif "qwen-max" in chosen_model:
                                key = st.session_state.get("qwen_key")
                                if not key:
                                    st.error("🔑 错误：检测到您未在左侧栏填写 Qwen (DashScope) API Key！")
                                    st.stop()
                                run_client = openai.OpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=key)
                                run_model = "qwen-max"
                                
                            else:
                                run_client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
                                run_model = chosen_model.split(" ")[0] 
                            
                            # 构建极其强悍、高保真、用于直接重塑全文的高级 Prompt 
                            # 岗位原始 JD 长度决定 prompt 策略
                            jd_text = target_job.get('raw_text', '')
                            if len(jd_text) < 100:
                                # DOM 提取的岗位（无 JD 详情），让 LLM 基于标题推断
                                refined_prompt = f"""你是一位猎头简历专家。候选人想去投递以下岗位，但只知道岗位名称，没有完整 JD。

【候选人当前简历】：
{base_resume}

【目标岗位名称】：{target_job['title']}
【目标公司】：{target_job.get('source', '')}
【猎头研判】：{target_job.get('reason', '')}

请做三件事：
1. 基于岗位名称【{target_job['title']}】，推断这个岗位最可能要求什么技能和经验
2. 重写「个人总结」，让 HR 扫一眼就觉得「这人就是干这个的」
3. 调整「核心技能」顺序，把和目标岗位最相关的技能放最前面

完整输出修改后的 Markdown 简历，不要省略任何项目经历。"""
                            else:
                                # 有完整 JD 的岗位，基于 JD 精准调整
                                refined_prompt = f"""你是一位猎头简历专家。以下是候选人简历和目标岗位 JD：

【候选人当前简历】：
{base_resume}

【目标岗位】：{target_job['title']}
【JD描述】：{jd_text}
【猎头研判】：{target_job.get('reason', '')}

请基于 JD 做精准调整：
1. 从 JD 中提取 3-5 个关键词/要求，在简历中强化对应经验
2. 重写「个人总结」，直接匹配岗位需求
3. 「核心技能」保留 JD 中最看重的技能，调整描述方式对齐 JD 用语
4. 工作经历中，把和目标岗位最相关的项目/职责往前放、详细写
5. 语义不变的前提下，把 JD 里出现的专业术语融入简历描述

完整输出修改后的 Markdown 简历，不要省略。"""
                            res = run_client.chat.completions.create(
                                model=run_model,
                                messages=[
                                    {"role": "system", "content": "你是一个严谨高端的职业经纪人专家。请直接输出定制重组后的完整 Markdown 简历全文。"},
                                    {"role": "user", "content": refined_prompt}
                                ],
                                temperature=0.3
                            )
                            
                            storage_key = f"full_resume_{target_job['title']}_{run_model}"
                            clean_md = res.choices[0].message.content
                            clean_md = re.sub(r"<think>.*?</think>", "", clean_md, flags=re.DOTALL)
                            clean_md = clean_md.replace("```markdown", "").replace("```", "").strip()
                            st.session_state[storage_key] = clean_md
                            
                        except Exception as e:
                            st.error(f"❌ 运行失败！该大模型网关发生网络拒绝或超时异常，请确认您的密钥是否有效或本地 Ollama 是否开启。错误详情: {str(e)}")
            
            # 4. 📊 跨维度定制成果展示与极速 MD 导出大盘
            st.write("")
            st.markdown("##### 📄 3. 定制化简历全文成品库与一键导出")
            
            check_keys = ["qwen2.5:14b", "deepseek-r1:14b", "llama3.1:8b", "gpt-4o", "deepseek-chat", "gemini-1.5-pro", "qwen-max"]
            available_reports = {}
            for m in check_keys:
                k = f"full_resume_{target_job['title']}_{m}"
                if k in st.session_state:
                    available_reports[m] = st.session_state[k]
            
            if not available_reports:
                st.info("💡 暂无针对该岗位的全文重塑版本。请在上方选择你感兴趣的重构大脑，并点击「启动全文高阶简历重构」按钮。")
            else:
                report_tabs = st.tabs([f"📄 {m} 专属全文定制" for m in available_reports.keys()])
                for idx, (m, content) in enumerate(available_reports.items()):
                    with report_tabs[idx]:
                        st.success(f"✨ 以下是 【{m}】 重构出的针对 【{target_job['title']}】 定向熔炼改写版简历：")
                        
                        st.download_button(
                            label=f"📥 导出该版本为 Markdown 文档 (.md)",
                            data=content,
                            file_name=f"【定点重构】{curr_candidate.get('name')}_对标_{target_job['title'][:6]}.md",
                            mime="text/markdown",
                            use_container_width=True,
                            key=f"dl_btn_{idx}_{target_job['title']}_{m}"
                        )
                        st.markdown("---")
                        st.markdown(content)
                        st.info("💡 提示：云端模型与本地推理模型风格各有千秋，您可以博采众长、拆分拼装。")
    else:
        st.warning("请先建立或选择一个候选人档案。")