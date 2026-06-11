"""安装脚本的辅助补丁：将 app.py 默认从 Ollama 改为 DeepSeek"""
import sys

with open("app.py") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("st.session_state.client = openai.OpenAI("):
        j = i
        depth = stripped.count("(") - stripped.count(")")
        while j < len(lines) - 1 and depth > 0:
            j += 1
            depth += lines[j].count("(") - lines[j].count(")")
        
        indent = " " * (len(lines[i]) - len(lines[i].lstrip()))
        new_lines = [
            f"{indent}try:\n",
            f"{indent}    import json as _j\n",
            f"{indent}    with open('config.json') as _f:\n",
            f"{indent}        _cfg = _j.load(_f)\n",
            f"{indent}    _key = _cfg.get('deepseek_api_key', '')\n",
            f"{indent}    if _key:\n",
            f"{indent}        st.session_state.client = openai.OpenAI(base_url='https://api.deepseek.com/v1', api_key=_key)\n",
            f"{indent}    else:\n",
            f"{indent}        st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')\n",
            f"{indent}except:\n",
            f"{indent}    st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')\n",
        ]
        lines[i:j+1] = new_lines
        break

with open("app.py", "w") as f:
    f.writelines(lines)

try:
    compile("".join(lines), "app.py", "exec")
    print("✅ app.py patched: DeepSeek is now the default\n✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Line {e.lineno}: {e.msg}")
    sys.exit(1)
