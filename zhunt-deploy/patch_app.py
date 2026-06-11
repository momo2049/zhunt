# patch_app.py — 将 app.py 默认从 Ollama 改为 DeepSeek
import sys

with open('app.py') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.strip() == 'if "client" not in st.session_state:':
        # 找到 st.session_state.client = openai.OpenAI(...) 的结束括号
        j = i + 1
        depth = 0
        if j < len(lines):
            depth = lines[j].count('(') - lines[j].count(')')
            j += 1
        while j < len(lines) and depth > 0:
            depth += lines[j].count('(') - lines[j].count(')')
            j += 1
        
        indent = '    '
        new_lines = [
            'if "client" not in st.session_state:\n',
            indent + 'try:\n',
            indent + '    import json as _j\n',
            indent + "    with open('config.json') as _f:\n",
            indent + '        _cfg = _j.load(_f)\n',
            indent + "    _key = _cfg.get('deepseek_api_key', '')\n",
            indent + '    if _key:\n',
            indent + "        st.session_state.client = openai.OpenAI(base_url='https://api.deepseek.com/v1', api_key=_key)\n",
            indent + '    else:\n',
            indent + "        st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')\n",
            indent + 'except:\n',
            indent + "    st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')\n",
        ]
        lines[i:j] = new_lines
        break

with open('app.py', 'w') as f:
    f.writelines(lines)

try:
    compile(''.join(lines), 'app.py', 'exec')
    print("app.py patched: DeepSeek is now the default")
    print("Syntax OK")
except SyntaxError as e:
    print("Line {}: {}".format(e.lineno, e.msg))
    sys.exit(1)
