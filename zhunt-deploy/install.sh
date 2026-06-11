#!/bin/bash
# ZenHunter 猎头助手 · Mac 一键安装脚本
# 打开终端 → 粘贴以下命令运行：
#   curl -sL https://raw.githubusercontent.com/你的用户名/zhunt/main/zhunt-deploy/install.sh | bash

set -e

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║        ZenHunter 猎头助手 · Mac 安装         ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  全程自动安装，大约需要 5-10 分钟             ║"
echo "║  期间请保持网络畅通，不要关闭此窗口           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── 1. 检查 Python ────────────────────────────────
echo -e "${YELLOW}🔍 检查 Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}📦 安装 Python...${NC}"
    if command -v brew &> /dev/null; then
        brew install python@3.11
    else
        echo "请先安装 Homebrew: https://brew.sh"
        echo "或从 https://www.python.org/downloads/ 下载 Python 3.11+"
        exit 1
    fi
fi

PY_VER=$(python3 --version)
echo -e "${GREEN}✅ $PY_VER${NC}"

# ── 2. 下载代码 ────────────────────────────────────
ZHUNT_DIR="$HOME/ZenHunter"
echo -e "${YELLOW}📥 下载猎头助手...${NC}"
# ⚠️ 请将下面的 URL 改为你的 GitHub 仓库地址
REPO_URL="https://github.com/momo2049/zhunt.git"

if [ -d "$ZHUNT_DIR" ]; then
    echo -e "${YELLOW}📁 目录已存在，更新中...${NC}"
    cd "$ZHUNT_DIR" && git pull
else
    git clone "$REPO_URL" "$ZHUNT_DIR"
    cd "$ZHUNT_DIR"
fi

echo -e "${GREEN}✅ 代码下载完成${NC}"

# ── 3. 配置 DeepSeek API Key ──────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          配置 DeepSeek API Key               ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║  猎头助手默认使用 DeepSeek 云端 AI           ║${NC}"
echo -e "${CYAN}║  需要先在 deepseek.com 注册并获取 API Key    ║${NC}"
echo -e "${CYAN}║  ¥5 充值足够评估几千次岗位                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

read -p "请输入 DeepSeek API Key (回车跳过，后续可在侧边栏填写): " API_KEY

cat > config.json << EOF
{
    "deepseek_api_key": "${API_KEY:-}",
    "deepseek_model": "deepseek-chat",
    "first_run": true
}
EOF
echo -e "${GREEN}✅ 配置已保存${NC}"

# ── 4. 补丁：默认使用 DeepSeek ────────────────────
echo -e "${YELLOW}🔧 自动适配 DeepSeek...${NC}"
python3 zhunt-deploy/patch_app.py 2>/dev/null || python3 << 'PATCH'
with open('app.py') as f:
    code = f.read()
old = "st.session_state.client = openai.OpenAI(\n        base_url='http://localhost:11434/v1', \n        api_key='ollama'\n    )"
new = """try:
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
    print("✅ app.py patched")
PATCH
echo -e "${GREEN}✅ 补丁完成${NC}"

# ── 5. 创建虚拟环境 + 安装依赖 ────────────────────
echo -e "${YELLOW}🐍 创建 Python 虚拟环境...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install streamlit openai playwright beautifulsoup4 rich rapidfuzz -q

echo -e "${GREEN}✅ 依赖安装完成${NC}"

# ── 6. 安装 Playwright Chromium ──────────────────
echo -e "${YELLOW}🌐 安装浏览器内核（约 2 分钟）...${NC}"
python3 -m playwright install chromium 2>&1 | tail -1
echo -e "${GREEN}✅ 浏览器内核安装完成${NC}"

# ── 7. 创建桌面快捷方式 ──────────────────────────
echo -e "${YELLOW}📌 创建启动脚本...${NC}"
cat > "$HOME/Desktop/ZenHunter.command" << EOF
#!/bin/bash
cd "$ZHUNT_DIR"
source venv/bin/activate
streamlit run app.py --server.headless true --browser.gatherUsageStats false &
sleep 3
open http://localhost:8501
EOF
chmod +x "$HOME/Desktop/ZenHunter.command"
echo -e "${GREEN}✅ 桌面快捷方式已创建: ZenHunter.command${NC}"

# ── 8. 启动 ──────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          安装完成！即将启动...               ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  首次启动时会自动打开浏览器                   ║${NC}"
echo -e "${GREEN}║  以后双击桌面 ZenHunter.command 即可启动      ║${NC}"
echo -e "${GREEN}║  猎聘/BOSS 首次使用需扫码登录                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}⏳ 正在启动...${NC}"
cd "$ZHUNT_DIR"
source venv/bin/activate
streamlit run app.py --server.headless true --browser.gatherUsageStats false &
sleep 3
open http://localhost:8501
echo -e "${GREEN}✅ 浏览器已打开${NC}"
