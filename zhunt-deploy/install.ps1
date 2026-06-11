<#
    ZenHunter 猎头助手 · Windows 一键安装脚本
    使用方式：右键 → 用 PowerShell 运行
    或：powershell -c "irm https://raw.githubusercontent.com/你的用户名/zhunt/main/zhunt-deploy/install.ps1 | iex"
#>

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "ZenHunter 猎头助手 - 正在安装..."

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        ZenHunter 猎头助手 · Windows 安装     ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  全程自动安装，大约需要 5-10 分钟             ║" -ForegroundColor Cyan
Write-Host "║  期间请保持网络畅通，不要关闭此窗口           ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── 1. 检查 Python ────────────────────────────────
Write-Host "🔍 检查 Python..." -ForegroundColor Yellow
$python = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "📦 正在通过 Microsoft Store 安装 Python..." -ForegroundColor Yellow
    try {
        winget install -e --id Python.Python.3.11 --accept-source-agreements --silent
        refreshenv
        $python = Get-Command "python" -ErrorAction SilentlyContinue
    } catch {
        Write-Host "❌ 安装失败，请手动从 python.org 下载 Python 3.11+" -ForegroundColor Red
        Read-Host "按回车退出"
        exit 1
    }
}

$pyVer = python --version 2>&1
Write-Host "✅ $pyVer" -ForegroundColor Green

# ── 2. 下载代码 ────────────────────────────────────
$zhuntDir = Join-Path $env:USERPROFILE "ZenHunter"
Write-Host "📥 下载猎头助手..." -ForegroundColor Yellow
# ⚠️ 请将下面的 URL 改为你的 GitHub 仓库地址
$repoUrl = "https://github.com/momo2049/zhunt.git"

if (Test-Path $zhuntDir) {
    Write-Host "📁 目录已存在，更新中..." -ForegroundColor Yellow
    Set-Location $zhuntDir
    git pull
} else {
    git clone $repoUrl $zhuntDir
    Set-Location $zhuntDir
}

Write-Host "✅ 代码下载完成" -ForegroundColor Green

# ── 3. 配置 DeepSeek API Key ──────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          配置 DeepSeek API Key               ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  猎头助手默认使用 DeepSeek 云端 AI           ║" -ForegroundColor Cyan
Write-Host "║  需要先在 deepseek.com 注册并获取 API Key    ║" -ForegroundColor Cyan
Write-Host "║  ¥5 充值足够评估几千次岗位                   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$apiKey = Read-Host "请输入 DeepSeek API Key (直接回车跳过，后续可在侧边栏填写)"

$config = @{
    deepseek_api_key = $apiKey
    deepseek_model = "deepseek-chat"
    first_run = $true
    user_name = ""
} | ConvertTo-Json

$config | Out-File -FilePath (Join-Path $zhuntDir "config.json") -Encoding utf8
Write-Host "✅ 配置已保存" -ForegroundColor Green

# ── 4. 补丁：默认使用 DeepSeek ────────────────────
Write-Host "🔧 自动适配 DeepSeek..." -ForegroundColor Yellow
$appPy = Join-Path $zhuntDir "app.py"
$appContent = Get-Content $appPy -Raw

$oldCode = "st.session_state.client = openai.OpenAI(`n        base_url='http://localhost:11434/v1', `n        api_key='ollama'`n    )"
$newCode = @"try:
    import json as _j
    with open('config.json') as _f:
        _cfg = _j.load(_f)
    _key = _cfg.get('deepseek_api_key', '')
    if _key:
        st.session_state.client = openai.OpenAI(base_url='https://api.deepseek.com/v1', api_key=_key)
    else:
        st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
except:
    st.session_state.client = openai.OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
"@

# PowerShell regex replace
$appContent = $appContent -replace [regex]::Escape($oldCode), $newCode
Set-Content -Path $appPy -Value $appContent -NoNewline
Write-Host "✅ 补丁完成" -ForegroundColor Green

# ── 5. 虚拟环境 + 安装依赖 ────────────────────────
Write-Host "🐍 创建 Python 虚拟环境..." -ForegroundColor Yellow
$venvDir = Join-Path $zhuntDir "venv"
if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
}
$pip = Join-Path $venvDir "Scripts" "pip"
& $pip install --upgrade pip -q
& $pip install streamlit openai playwright beautifulsoup4 rich rapidfuzz -q
Write-Host "✅ 依赖安装完成" -ForegroundColor Green

# ── 6. 安装 Playwright Chromium ──────────────────
Write-Host "🌐 安装浏览器内核（约 2 分钟）..." -ForegroundColor Yellow
$playwright = Join-Path $venvDir "Scripts" "playwright"
& $playwright install chromium 2>&1 | Out-Null
Write-Host "✅ 浏览器内核安装完成" -ForegroundColor Green

# ── 7. 创建桌面快捷方式 ──────────────────────────
Write-Host "📌 创建桌面快捷方式..." -ForegroundColor Yellow
$desktopPath = [Environment]::GetFolderPath("Desktop")
$streamlitRun = Join-Path $venvDir "Scripts" "streamlit.exe"
$runArgs = "run $appPy --server.headless true --browser.gatherUsageStats false"

$shortcutPath = Join-Path $desktopPath "ZenHunter.lnk"
$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $streamlitRun
$shortcut.Arguments = $runArgs
$shortcut.WorkingDirectory = $zhuntDir
$shortcut.Description = "ZenHunter 猎头助手"
$shortcut.Save()
Write-Host "✅ 桌面快捷方式已创建" -ForegroundColor Green

# ── 8. 启动 ──────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          安装完成！即将启动...               ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  首次启动时会自动打开浏览器                   ║" -ForegroundColor Green
Write-Host "║  以后双击桌面 ZenHunter 图标即可              ║" -ForegroundColor Green
Write-Host "║  猎聘/BOSS 首次使用需扫码登录                 ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "⏳ 正在启动，请稍候..." -ForegroundColor Yellow

Start-Process -FilePath $streamlitRun -ArgumentList $runArgs -WorkingDirectory $zhuntDir
Start-Sleep -Seconds 3
Start-Process "http://localhost:8501"

Write-Host "✅ 已启动！浏览器已打开" -ForegroundColor Green
Read-Host "按回车键关闭此窗口"
