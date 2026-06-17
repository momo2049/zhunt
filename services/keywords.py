# services/keywords.py

# 同义词 + 英文变体扩展表
KEYWORD_SYNONYMS = {
    # AI工程化
    "AI工程化":     ["AI Engineer", "LLM Engineer", "AI应用开发"],
    "大模型":       ["LLM", "大语言模型", "Foundation Model", "GenAI"],
    "RAG":          ["RAG系统", "检索增强生成", "知识库问答"],
    "向量数据库":   ["Vector DB", "Milvus", "Weaviate", "向量检索"],
    "模型部署":     ["Model Serving", "vLLM", "推理加速", "MLOps"],
    # 后端
    "后端开发":     ["Backend Engineer", "服务端开发", "Java开发", "Python后端"],
    "高并发":       ["High Concurrency", "分布式系统", "微服务架构"],
    "分布式":       ["Distributed Systems", "分布式架构", "微服务"],
    # 数据
    "数据分析":     ["Data Analyst", "数据科学", "BI分析", "Data Science"],
    "数据工程":     ["Data Engineer", "ETL", "数据管道", "Spark"],
    # 法务/合规
    "法务":         ["Legal Counsel", "合规", "法律顾问", "Corporate Legal"],
    "合规":         ["Compliance", "RegTech", "风控合规", "Legal Compliance"],
    "风控":         ["Risk Management", "风险管理", "反洗钱", "AML"],
    # 金融/商务/销售类（覆盖金融+AI交叉领域的岗位）
    "金融AI":       ["金融科技", "AI金融", "金融智能化", "FinTech"],
    "AI销售":       ["AI商务", "人工智能销售", "大模型销售", "AI商业化", "AI业务拓展"],
    "金融销售":     ["金融科技销售", "金融行业销售", "机构销售", "大客户销售"],
    "解决方案销售":  ["售前", "技术方案销售", "解决方案顾问", "售前工程师"],
    "客户成功":     ["客户运营", "KA", "大客户服务", "CSM"],
    "金融科技":     ["FinTech", "科技金融", "金融数字化"],
    "销售经理":     ["大客户经理", "商务经理", "BD经理", "销售主管"],
    "客户成功经理":  ["CSM", "客户服务经理", "客户运营经理", "客户成功专家"],
    "生态合作":     ["渠道合作", "生态BD", "商务合作", "战略合作"],
    "行业BD":      ["商务拓展", "行业拓展", "业务发展", "BD"],
    "AI产品":      ["AI产品经理", "人工智能产品", "大模型产品", "AI应用产品"],
    "AI运营":      ["AI运营", "大模型运营", "人工智能运营"],
    # English synonyms for HK platforms
    "金融AI解决方案销售": ["AI Solution Sales", "FinTech Sales", "AI Business Development"],
    "客户成功经理":     ["Customer Success Manager", "Client Success Manager"],
    "金融科技销售":     ["FinTech Sales", "Financial Technology Sales"],
    "销售经理":        ["Sales Manager", "BD Manager", "Business Development"],
    "客户成功":        ["Customer Success", "Client Success", "Account Management"],
    "解决方案销售":     ["Solution Sales", "Solution Consultant", "Pre-Sales"],
    "金融行业BD":      ["Financial BD", "FinTech BD", "Business Development Finance"],
    "生态合作":        ["Partnership Manager", "Channel Partnership", "Ecosystem BD"],
    "金融科技":        ["FinTech", "Financial Technology"],
    "AI销售":         ["AI Sales", "Artificial Intelligence Sales"],
    "商务经理":        ["Business Manager", "Commercial Manager"],
    "机构合作":        ["Institutional Partnership", "Institutional BD"],

}

SEARCH_SUFFIXES = ["招聘", "job", "岗位 2026"]

def extract_tech_keywords(raw_keywords):
    if not raw_keywords:
        return []
    if isinstance(raw_keywords, list):
        keys = raw_keywords
    else:
        keys = [k.strip() for k in str(raw_keywords).split(',')]
    return [k for k in keys if k]

def decompose_cn_job_keyword(keywords):
    """将中文复合职位关键词拆解为更短的高召回子关键词
    
    例如: "金融AI解决方案销售" → ["AI解决方案销售","解决方案销售","金融AI解决方案"]
    例如: "金融行业客户成功经理" → ["行业客户成功经理","客户成功经理","金融行业客户成功"]
    """
    # 常见行业/领域前缀（长词在前优先匹配）
    prefixes = ["金融科技", "人工智能", "大模型", "金融", "AI", "科技",
                "互联网", "数字", "智能", "机构", "行业", "企业"]
    
    # 常见职位角色后缀
    role_suffixes = ["销售", "经理", "专家", "顾问", "BD", "运营", "产品",
                     "总监", "负责人", "主管", "工程师", "助理"]
    
    result = set()
    
    for kw in keywords:
        if not kw:
            continue
        result.add(kw)
        
        # 找出所有匹配的前缀，按长度降序（长前缀优先匹配）
        matched = [p for p in prefixes if p in kw]
        matched.sort(key=len, reverse=True)
        
        for p in matched:
            idx = kw.index(p)
            
            # 从前缀开始的子串（去掉了前缀前面的内容）
            sub = kw[idx:]
            if sub != kw and len(sub) >= 2:
                result.add(sub)
            
            # 前缀之后的部分
            after = kw[idx + len(p):]
            if after and len(after) >= 2:
                result.add(after)
        
        # 按角色后缀拆分: 去掉后缀得到基础词
        for suffix in role_suffixes:
            if kw.endswith(suffix) and len(kw) > len(suffix) + 1:
                base = kw[:-len(suffix)]
                result.add(base)
                
                # 对基础词再做前缀拆分，然后重新拼上后缀
                for p in matched:
                    if p in base:
                        idx = base.index(p)
                        after = base[idx + len(p):]
                        if after and len(after) >= 2:
                            result.add(after + suffix)
    
    # 过滤: 只保留长度 2~12 的有意义关键词
    # 过滤过短或过长的关键词
    short_whitelist = {"BD", "KA", "售前"}
    result = {r for r in result
              if r in short_whitelist or (3 <= len(r) <= 12)}
    
    return list(result)

def generate_job_keywords(raw_keywords):
    base_keys = extract_tech_keywords(raw_keywords)
    expanded = set(base_keys)

    for key in base_keys:
        if key in KEYWORD_SYNONYMS:
            expanded.update(KEYWORD_SYNONYMS[key])
        for table_key, synonyms in KEYWORD_SYNONYMS.items():
            if table_key in key or key in table_key:
                expanded.update(synonyms)

    # 🔑 复合词拆解：将长词拆为更短的高召回子词
    decomposed = decompose_cn_job_keyword(list(expanded))
    expanded.update(decomposed)

    # 限制总关键词数量，避免扫街任务过多
    MAX_KEYWORDS = 15
    sorted_kws = sorted(expanded, key=len, reverse=True)
    expanded = set(sorted_kws[:MAX_KEYWORDS])

    suffixed = set()
    for kw in expanded:
        suffixed.add(kw)
        suffixed.add(f"{kw} {SEARCH_SUFFIXES[0]}")

    return list(suffixed)
