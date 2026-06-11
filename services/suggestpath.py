# services/suggestpath.py
import json
import re
from rich.console import Console
from rich.panel import Panel

console = Console()

def suggest_search_paths(client, model, candidate, user_intent=None):
    if user_intent is None:
        user_intent = candidate.get('user_intent', {})
    matrix = user_intent.get('matrix', {})
    atomic_assets = candidate.get('atomic_assets', [])
    candidate_type = candidate.get('type', '未知')

    console.print(f"\n[bold blue]🧠 猎头视角评估中：{candidate_type}...[/bold blue]")

    prompt = f"""
你是一位有15年经验的资深猎头顾问。你每天向企业HR推荐候选人，你的判断直接影响候选人能拿到什么offer。
你不是职业规划老师，不需要鼓励候选人，你需要的是市场化的冷静判断。

【候选人类型】：{candidate_type}
【技能矩阵】：{json.dumps(matrix, ensure_ascii=False)}
【核心资产（原子化经历）】：{json.dumps(atomic_assets, ensure_ascii=False)}
【稳定性偏好】：{user_intent.get('stability_pref', 3)}/5
【增长性偏好】：{user_intent.get('growth_pref', 3)}/5

请严格返回如下JSON，不要包含任何解释文字：
{{
  "paths": [
    {{
      "target_roles": ["角色名"],
      "search_keywords": ["关键词1", "关键词2"],
      "sustainability_reason": "这条路3年后还值得走的原因",
      "premium_logic": "候选人哪个具体经历能在这个方向溢价"
    }}
  ],
  "market_verdict": {{
    "sellable_as": "猎头向HR介绍此人的一句话定位",
    "price_ceiling": "当前市场愿意给的最高段位，例如P7/Senior/Team Lead",
    "hardest_objection": "HR最可能拒绝此人的核心理由，要具体不要模糊",
    "company_stage_fit": ["适合的公司阶段"],
    "reachability": {{
      "startup": "小公司能触达的职级",
      "mid": "中型公司能触达的职级",
      "large": "大厂能触达的职级"
    }}
  }}
}}
"""

    try:
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=120.0
        )
        content = res.choices[0].message.content.strip()

        json_str = re.search(r'\{.*\}', content, re.DOTALL)
        result = json.loads(json_str.group() if json_str else content)

        if result and 'paths' in result:
            for i, path in enumerate(result['paths'], 1):
                role = path.get('target_roles', ['未知'])[0]
                console.print(Panel(
                    f"[bold cyan]方向 {i}: {role}[/bold cyan]\n"
                    f"[dim]🔍 搜索词: {', '.join(path.get('search_keywords', []))}[/dim]\n"
                    f"[green]💎 溢价逻辑: {path.get('premium_logic', 'N/A')}[/green]\n"
                    f"[blue]🛡️ 可持续性: {path.get('sustainability_reason', 'N/A')}[/blue]",
                    expand=False
                ))

            verdict = result.get('market_verdict', {})
            if verdict:
                reachability = verdict.get('reachability', {})
                console.print(Panel(
                    f"[bold yellow]📊 市场裁定[/bold yellow]\n"
                    f"[white]📌 定位: {verdict.get('sellable_as', 'N/A')}[/white]\n"
                    f"[green]💰 段位天花板: {verdict.get('price_ceiling', 'N/A')}[/green]\n"
                    f"[red]⚠️  HR最可能拒绝你的理由: {verdict.get('hardest_objection', 'N/A')}[/red]\n"
                    f"[dim]🏢 适合阶段: {', '.join(verdict.get('company_stage_fit', []))}[/dim]\n"
                    f"[cyan]🎯 可触达职级 → 小公司: {reachability.get('startup')} / "
                    f"中型: {reachability.get('mid')} / "
                    f"大厂: {reachability.get('large')}[/cyan]",
                    expand=False
                ))
            return result
        else:
            console.print("[red]AI 返回格式不符，未能提取到路径。[/red]")
            return None

    except Exception as e:
        console.print(f"[red]❌ 规划服务异常: {str(e)}[/red]")
        return None
