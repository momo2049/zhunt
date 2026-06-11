"""安装脚本的辅助补丁：将 app.py 默认从 Ollama 改为 DeepSeek"""
import sys

OLD_BLOCK = 'if "client" not in st.session_state:\n    st.session_state.client = openai.OpenAI(\n        base_url=\'http://localhost:11434/v1\',\n        api_key=\'ollama\'\n    )'

NEW_BLOCK = 'if "client" not in st.session_state:\n    try:\n        import json as _j\n        with open(\'config.json\') as _f:\n            _cfg = _j.load(_f)\n        _key = _cfg.get(\'deepseek_api_key\', \'\')\n        if _key:\n            st.session_state.client = openai.OpenAI(base_url=\'https://api.deepseek.com/v1\', api_key=_key)\n        else:\n            st.session_state.client = openai.OpenAI(base_url=\'http://localhost:11434/v1\', api_key=\'ollama\')\n    except:\n        st.session_state.client = openai.OpenAI(base_url=\'http://localhost:11434/v1\', api_key=\'ollama\')'

with open('app.py') as f:
    c = f.read()

if OLD_BLOCK in c:
    c = c.replace(OLD_BLOCK, NEW_BLOCK)
    with open('app.py', 'w') as f:
        f.write(c)
    try:
        compile(c, 'app.py', 'exec')
        print("app.py patched: DeepSeek is now the default")
        print("Syntax OK")
    except SyntaxError as e:
        print("Line {}: {}".format(e.lineno, e.msg))
        sys.exit(1)
else:
    print("Pattern not found (already patched or different version)")
