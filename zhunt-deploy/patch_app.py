"""安装脚本的辅助补丁：将 app.py 默认从 Ollama 改为 DeepSeek"""
import re, sys

with open('app.py') as f:
    code = f.read()

old = "st.session_state.client = openai.OpenAI(\n        base_url='http://localhost:11434/v1', \n        api_key='ollama'\n    )"

new = """# 安装补丁：优先使用 config.json 中的 DeepSeek API Key
try:
    import json as _j
    with open('config.json') as _f:
        _cfg = _j.load(_f)
    _key = _cfg.get('deepseek_api_key', '')
    if _key:
        st.session_state.client = openai.OpenAI(base_url='https://api.deepseek.com/v1', api_key=_key)
    else:
        st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
except:
    st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')"""

if old in code:
    code = code.replace(old, new)
    with open('app.py', 'w') as f:
        f.write(code)
    print("✅ app.py patched: DeepSeek is now the default")
else:
    print("⚠️  Pattern not found, checking...")
    # Debug: show what's around line 20
    for i, line in enumerate(code.split('\n')[15:30], 16):
        print(f"  {i}: {line[:100]}")

# Verify
try:
    compile(code, 'app.py', 'exec')
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Line {e.lineno}: {e.msg}")
