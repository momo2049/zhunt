# services/intent_parser.py
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt

console = Console()

def parse_detailed_skills():
    console.print("\n[bold magenta]🏗️  构建 AI 转型技能矩阵 (Skill Matrix)[/bold magenta]")
    console.print("[dim]分级标准：0-无, 1-基础/了解, 2-熟练/生产应用, 3-专家/底层优化[/dim]\n")
    
    # 结构化技能树
    skill_tree = {
        "核心后端 (稳定性基石)": ["并发模型与异步编程", "分布式架构设计", "高性能数据库/缓存调优"],
        "AI 工程化 (转型杠杆)": ["RAG 系统工程实现", "向量数据库 (Vector DB)", "大模型推理加速/部署"],
        "增长性资产 (可持续性)": ["工程化架构演进能力", "技术方案决策权重", "业务领域深度建模"]
    }

    matrix = {}
    for branch, skills in skill_tree.items():
        console.print(f"[bold cyan]🌿 分支: {branch}[/bold cyan]")
        for skill in skills:
            level = IntPrompt.ask(f"  └─ {skill} 的熟练度 (0-3)", default=1)
            matrix[skill] = {
                "level": level,
                "category": branch
            }
    
    console.print("\n[bold yellow]🛡️  职业风险与可持续性偏好[/bold yellow]")
    stability = IntPrompt.ask("您对“岗位稳定性”的重视程度？(1-接受初创冒险 5-追求极稳基石)", default=4)
    growth = IntPrompt.ask("您对“技术前瞻性”的追求程度？(1-成熟技术 5-前沿探索)", default=4)
    
    return {
        "matrix": matrix, 
        "stability_pref": stability,
        "growth_pref": growth
    }