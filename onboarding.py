# onboarding.py
import streamlit as st
import json
import re
import os
import openai

def render_onboarding():
    st.markdown("### 💡 深度访谈工作坊 (4大Skill原子资产共创)")
    st.caption("AI经纪人将通过结构化对话，精准提取你的核心资产。达到量化标准后，系统将为您生成原子资产、市场估值裁定及母盘简历。")
    st.divider()

    # 1. 核心客户端检查
    if "client" not in st.session_state:
        st.error("❌ 核心客户端未初始化，请检查 app.py 主入口。")
        return

    # 2. 🔌 智能访谈大脑路由器
    st.markdown("##### 🤖 1. 选择你当前的访谈经纪人大脑")
    col_brain1, col_brain2 = st.columns([2, 3])
    with col_brain1:
        interview_model_options = [
            "qwen2.5:14b (本地)", "deepseek-r1:14b (本地)", "llama3.1:8b (本地)",
            "gpt-4o (云端在线)", "deepseek-chat (云端在线)", "gemini-1.5-pro (云端在线)",
            "qwen-max (云端在线)"
        ]
        chosen_brain = st.selectbox(
            "当前对话大模型：", 
            interview_model_options, 
            index=0, 
            key="chosen_interview_brain"
        )
    with col_brain2:
        st.caption("💡 **经纪人换脑建议**：\n"
                   "* 想深度挖掘细节？建议切换到 `deepseek-r1:14b`（内置思考反思，极度敏锐）。\n"
                   "* 想体验高管级对话？推荐 `gpt-4o` 或 `qwen2.5:14b`。")

    # 💡 动态网关路由分流器
    try:
        if "gpt-4o" in chosen_brain:
            key = st.session_state.get("openai_key")
            if not key:
                st.warning("⚠️ 提示：请先在侧边栏配置 OpenAI API Key！")
                st.stop()
            active_client = openai.OpenAI(base_url="https://api.openai.com/v1", api_key=key)
            active_model = "gpt-4o"
        elif "deepseek-chat" in chosen_brain:
            key = st.session_state.get("deepseek_key")
            if not key:
                st.warning("⚠️ 提示：请先在侧边栏配置 DeepSeek Cloud Key！")
                st.stop()
            active_client = openai.OpenAI(base_url="https://api.deepseek.com/v1", api_key=key)
            active_model = "deepseek-chat"
        elif "gemini" in chosen_brain:
            key = st.session_state.get("gemini_key")
            if not key:
                st.warning("⚠️ 提示：请先在侧边栏配置 Gemini API Key！")
                st.stop()
            active_client = openai.OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=key)
            active_model = "gemini-1.5-pro"
        elif "qwen-max" in chosen_brain:
            key = st.session_state.get("qwen_key")
            if not key:
                st.warning("⚠️ 提示：请先在侧边栏配置 Qwen (DashScope) API Key！")
                st.stop()
            active_client = openai.OpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=key)
            active_model = "qwen-max"
        else:
            active_client = st.session_state.client
            active_model = chosen_brain.split(" ")[0]
    except Exception as e:
        st.error(f"❌ 激活模型客户端出错: {str(e)}")
        st.stop()

    # 3. 初始化访谈专属状态机
    if "interview_messages" not in st.session_state:
        st.session_state.interview_messages = [
            {"role": "assistant", "content": "你好！我是你的专属 AI 职业经纪人。为了后续能帮你实现极其精准的「一岗一策」岗位对标与简历重构，我们需要通过对话梳理出你的核心原子资产。\n\n我们可以从你**最骄傲的 3 个项目/工作经历**开始聊聊，或者你也可以直接把现有的旧简历文本粘贴给我，我来帮你拆解！"}
        ]
    
    if "audit_status" not in st.session_state:
        st.session_state.audit_status = {
            "project_count": 0,
            "personality_captured": False,
            "skills_mapped": False,
            "career_planned": False
        }

    # 4. 实时计算量化审计进度盘
    status = st.session_state.audit_status
    proj_score = min(status["project_count"], 3) / 3 * 25
    pers_score = 25 if status["personality_captured"] else 0
    skill_score = 25 if status["skills_mapped"] else 0
    career_score = 25 if status["career_planned"] else 0
    total_progress = int(proj_score + pers_score + skill_score + career_score)

    metrics_placeholder = st.empty()
    with metrics_placeholder.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="📦 核心项目/经历", value=f"{status['project_count']} / 3", delta="🎯 目标 >= 3个" if status['project_count'] < 3 else "✨ 已达标")
        with col2:
            st.metric(label="🧠 性格/软实力", value="🟢 已捕捉" if status['personality_captured'] else "⚪ 待挖掘")
        with col3:
            st.metric(label="🛠️ 技能熟练度", value="🟢 已盘点" if status['skills_mapped'] else "⚪ 待深入")
        with col4:
            st.metric(label="🎯 职业规划/期望", value="🟢 已锚定" if status['career_planned'] else "⚪ 待明确")

        st.progress(total_progress / 100.0, text=f"📊 访谈资产画像完整度：{total_progress}%")
        st.write("")

    # 5. 渲染历史聊天流
    for msg in st.session_state.interview_messages:
        with st.chat_message(msg["role"]):
            clean_content = re.sub(r"\|\|\|.*?\|\|\|", "", msg["content"], flags=re.DOTALL)
            if "<think>" in clean_content:
                think_match = re.search(r"<think>(.*?)</think>", clean_content, flags=re.DOTALL)
                if think_match:
                    with st.expander("💭 观察经纪人的深度思考路线（思考脑）", expanded=False):
                        st.caption(think_match.group(1).strip())
                clean_content = re.sub(r"<think>.*?</think>", "", clean_content, flags=re.DOTALL).strip()
            st.markdown(clean_content)

    # 6. 用户交互输入框
    if user_input := st.chat_input("在此输入你的经历、回答AI的追问，或直接粘贴旧简历文本..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.interview_messages.append({"role": "user", "content": user_input})

        audit_prompt = """你是一位顶尖的职业经纪人，正在对候选人进行深度的结构化职业访谈。
        你的目标是精准采集并量化以下四大核心信息，为后续的岗位筛选 and 简历重构打下完美的“原子资产”基础。

        【采集四大铁律与导标标准】：
        1. 📦 项目/核心经验：至少盘出 3 个独立详尽的项目。
        2. 🧠 性格特质与软实力：识别其沟通、抗压、协作特性。
        3. 🛠️ 技能熟练度：盘出硬核壁垒与实战熟练度。
        4. 🎯 职业规划与期望：明确其未来发展与核心偏好。

        在你回复的【最末尾】，必须另起一行，用 `|||` 包裹当前最新审计结果 JSON（不要对用户解释此 JSON）。
        格式示例：
        你的回复正文...
        |||{"projects": 2, "personality": true, "skills": false, "career": true}|||
        """

        api_messages = [{"role": "system", "content": audit_prompt}]
        for msg in st.session_state.interview_messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        with st.chat_message("assistant"):
            with st.spinner(f"AI 经纪人 ({chosen_brain.split(' ')[0]}) 正在研判资产并构思追问..."):
                try:
                    res = active_client.chat.completions.create(
                        model=active_model,
                        messages=api_messages,
                        temperature=0.4
                    )
                    ai_reply = res.choices[0].message.content
                    
                    display_reply = re.sub(r"\|\|\|.*?\|\|\|", "", ai_reply, flags=re.DOTALL)
                    if "<think>" in display_reply:
                        think_match = re.search(r"<think>(.*?)</think>", display_reply, flags=re.DOTALL)
                        if think_match:
                            with st.expander("💭 观察经纪人的深度思考路线（思考脑）", expanded=False):
                                st.caption(think_match.group(1).strip())
                        display_reply = re.sub(r"<think>.*?</think>", "", display_reply, flags=re.DOTALL).strip()
                    
                    st.markdown(display_reply)
                    st.session_state.interview_messages.append({"role": "assistant", "content": ai_reply})
                    
                    raw_json = ""
                    clean_reply = re.sub(r"<think>.*?</think>", "", ai_reply, flags=re.DOTALL)
                    match = re.search(r"\|\|\|(.*?)\|\|\|", clean_reply, flags=re.DOTALL)
                    if match: raw_json = match.group(1).strip()
                    else:
                        fallback = re.search(r"```json\n?(.*?)\n?```", clean_reply, flags=re.DOTALL)
                        if fallback: raw_json = fallback.group(1).strip()

                    if raw_json:
                        try:
                            clean_json = raw_json.replace("```json", "").replace("```", "").strip()
                            audit_data = json.loads(clean_json)
                            st.session_state.audit_status = {
                                "project_count": int(audit_data.get("projects", 0)),
                                "personality_captured": bool(audit_data.get("personality", False)),
                                "skills_mapped": bool(audit_data.get("skills", False)),
                                "career_planned": bool(audit_data.get("career", False))
                            }
                            st.rerun()
                        except: pass
                    
                except Exception as e:
                    st.error(f"❌ 访谈引擎异常: {str(e)}")

    # 7. 🚪 封档结题出口控制
    st.divider()
    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        if total_progress < 100:
            st.info("💡 提示：当上方 4 大核心资产全部点亮（100%）时，系统将强烈推荐一键封档；若您觉得已足够，也可强制封档。")
        else:
            st.success("🎉 核心资产已达标！系统将依次为您提取原子资产、进行市场身价裁定、并生成标准母盘简历！")
            
    with col_btn2:
        new_candidate_name = st.text_input("👤 归档姓名", value="新候选人档案", label_visibility="collapsed")
        
        if st.button("🔒 一键执行三大核心封档", type="primary" if total_progress == 100 else "secondary", use_container_width=True):
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.interview_messages])
            parsed_profile = {}

            # ==========================================
            # STEP 1: 提取原子资产
            # ==========================================
            with st.spinner("STEP 1/3：正在将零散对话熔炼为『原子资产事实库』..."):
                try:
                    condense_prompt = f"""请阅读以下职业经纪人与候选人的核心访谈历史。将其熔炼为标准的「原子资产事实列表」。
                    【访谈历史】：\n{history_str}
                    【请严格按以下 JSON 格式输出，纯 JSON 字符串返回，勿用 Markdown 包装】：
                    {{
                        "name": "{new_candidate_name}",
                        "type": "根据对话总结的核心定位(如: AI应用产品经理)",
                        "atomic_assets": [
                            "客观事实1 (如: 具备3年独立带0到1高并发FastAPI项目的落地经验)",
                            "客观事实2",
                            "性格与软实力特征"
                        ]
                    }}
                    """
                    res1 = active_client.chat.completions.create(
                        model=active_model,
                        messages=[{"role": "user", "content": condense_prompt}],
                        temperature=0.1
                    )
                    raw_content = re.sub(r"<think>.*?</think>", "", res1.choices[0].message.content, flags=re.DOTALL)
                    raw_json = raw_content.replace("```json", "").replace("```", "").strip()
                    parsed_profile = json.loads(raw_json)
                except Exception as e:
                    st.error(f"❌ STEP 1: 凝练资产失败。错误: {str(e)}")
                    st.stop()

            # ==========================================
            # STEP 2: 铁血猎头市场裁定与搜寻路径指南 (核心修复：对准 search_keywords)
            # ==========================================
            with st.spinner("STEP 2/3：激活铁血猎头人格，正在进行极其冷酷的市场身价裁定与路径规划..."):
                try:
                    verdict_prompt = f"""你是一位有15年经验的资深猎头顾问。请针对候选人的定位与核心经历，做出市场化的冷静且残酷的判决。

                    【候选人定位】：{parsed_profile.get('type', '未知')}
                    【核心原子资产】：{json.dumps(parsed_profile.get('atomic_assets', []), ensure_ascii=False)}
                    【历史访谈细节】：{history_str}

                    请严格返回如下JSON（不含任何Markdown包装，直接返回干净JSON）：
                    {{
                      "paths": [
                        {{
                          "path_name": "核心攻坚路线(例如: 大模型商业化产品经理)",
                          "search_keywords": ["商业化产品经理", "大模型产品经理", "AI 解决方案"],
                          "sustainability_reason": "该路线3年内的行业溢价与可持续性原因",
                          "premium_logic": "该候选人过去的哪项具体原子资产可以在此方向获得溢价"
                        }}
                      ],
                      "market_verdict": {{
                        "sellable_as": "猎头向HR推销此人的一句话极度毒辣、极高溢价的定位",
                        "price_ceiling": "当前市场对该背景愿意匹配的最高段位(如: 25-45K / Senior / Lead)",
                        "hardest_objection": "HR最可能拒绝此人的致命软肋(需要极其客观、不留情面)",
                        "company_stage_fit": ["最容易拿到Offer的企业类型(如: B轮前、中型厂)"],
                        "reachability": {{
                          "startup": "初创公司可触达的具体职级",
                          "mid": "中型企业可触达的具体职级",
                          "large": "头部大厂能碰壁或触达的极限制"
                        }}
                      }}
                    }}
                    """
                    res2 = active_client.chat.completions.create(
                        model=active_model,
                        messages=[{"role": "user", "content": verdict_prompt}],
                        temperature=0.2
                    )
                    raw_content2 = re.sub(r"<think>.*?</think>", "", res2.choices[0].message.content, flags=re.DOTALL)
                    raw_json2 = raw_content2.replace("```json", "").replace("```", "").strip()
                    parsed_verdict = json.loads(raw_json2)

                    # 存储到 Profile 中
                    parsed_profile["suggested_paths"] = parsed_verdict.get("paths", [])
                    parsed_profile["market_verdict"] = parsed_verdict.get("market_verdict", {})
                    
                    # 💡 物理锚定：给默认的 selected_path，在 keywords 里面塞入 search_keywords 作为防御，拉通旧版本
                    if parsed_profile["suggested_paths"]:
                        first_path = parsed_profile["suggested_paths"][0]
                        parsed_profile["selected_path"] = {
                            "path_name": first_path.get("path_name", "默认路线"),
                            "keywords": first_path.get("search_keywords", [])
                        }

                except Exception as e:
                    st.error(f"❌ STEP 2: 市场规划生成失败。错误: {str(e)}")
                    st.stop()

            # ==========================================
            # STEP 3: 生成标准 Markdown 母盘简历
            # ==========================================
            with st.spinner("STEP 3/3：市场锚定完毕，正在为您自动撰写高溢价 Markdown 母盘简历..."):
                try:
                    resume_prompt = f"""请根据候选人的【原子资产】以及刚作出的【市场定位: {parsed_profile.get('market_verdict', {}).get('sellable_as')}】，为其撰写一份可直接投递的【标准版 Markdown 简历】。
                    要求：
                    1. 包含完整结构：【基本信息】、【个人总结】、【核心技能】、【工作/项目经历】(采用STAR法则突出成就)、【教育背景】。
                    2. 未提及的信息用 "[待补充]" 作为占位符。
                    3. 语气要极其专业、高级，直接输出纯 Markdown 文本。
                    """
                    res3 = active_client.chat.completions.create(
                        model=active_model,
                        messages=[
                            {"role": "user", "content": history_str},
                            {"role": "assistant", "content": json.dumps(parsed_profile, ensure_ascii=False)},
                            {"role": "user", "content": resume_prompt}
                        ],
                        temperature=0.3
                    )
                    resume_content = re.sub(r"<think>.*?</think>", "", res3.choices[0].message.content, flags=re.DOTALL)
                    parsed_profile["base_resume"] = resume_content.replace("```markdown", "").replace("```", "").strip()

                except Exception as e:
                    st.error(f"❌ STEP 3: 生成母盘简历失败。错误: {str(e)}")
                    st.stop()

            # ==========================================
            # 数据物理落盘
            # ==========================================
            try:
                profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'profile.json')
                if os.path.exists(profile_path):
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                else:
                    db = {"candidates": []}
                    
                db["candidates"].append(parsed_profile)
                
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(db, f, ensure_ascii=False, indent=4)
                    
                st.session_state.profile = db
                st.session_state.current_user_idx = len(db["candidates"]) - 1
                
                # 清理旧爬虫结果，强迫重新加载新用户的对标
                keys_to_kill = ["scan_results", "has_scanned", "has_just_scanned"]
                for k in keys_to_kill:
                    if k in st.session_state: del st.session_state[k]
                
                st.toast("✨ 核心档案三大件（资产事实/市场估值/简历母盘）已物理存盘！", icon="💾")
                st.balloons()
                st.rerun() 
                
            except Exception as e:
                st.error(f"❌ 文件存盘失败。错误: {str(e)}")