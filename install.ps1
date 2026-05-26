# UTF-8 Encoding
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "             EDMS 项目一键安装/配置脚本" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查运行环境
Write-Host "[1/4] 检查系统开发环境..." -ForegroundColor Yellow

$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) {
    $gitVer = (git --version)
    Write-Host " [OK] Git 已安装: $gitVer" -ForegroundColor Green
} else {
    Write-Warning " [警告] 未检测到 Git，请确保系统已安装 Git 并配置环境变量。"
}

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $nodeVer = (node -v)
    Write-Host " [OK] Node.js 已安装: $nodeVer" -ForegroundColor Green
} else {
    Write-Warning " [警告] 未检测到 Node.js，前端服务运行需要 Node.js (推荐 v18+)。"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $pyVer = (python --version 2>&1)
    Write-Host " [OK] Python 已安装: $pyVer" -ForegroundColor Green
} else {
    Write-Warning " [警告] 未检测到 Python，后端服务运行需要 Python (推荐 3.10+)。"
}
Write-Host ""

# 2. 自动复制配置文件模版 (.env)
Write-Host "[2/4] 初始化配置文件 (.env)..." -ForegroundColor Yellow
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendEnv = Join-Path $scriptDir "sources\backend\.env"
$backendEnvEx = Join-Path $scriptDir "sources\backend\.env.example"
$frontendEnv = Join-Path $scriptDir "sources\frontend\.env"
$frontendEnvEx = Join-Path $scriptDir "sources\frontend\.env.example"

if (Test-Path $backendEnv) {
    Write-Host " [跳过] sources/backend/.env 已存在，无需复制。" -ForegroundColor Gray
} else {
    if (Test-Path $backendEnvEx) {
        Copy-Item $backendEnvEx $backendEnv
        Write-Host " [OK] 已成功复制 sources/backend/.env.example 到 .env" -ForegroundColor Green
    } else {
        Write-Error " [错误] 未找到 sources/backend/.env.example 模版文件。"
    }
}

if (Test-Path $frontendEnv) {
    Write-Host " [跳过] sources/frontend/.env 已存在，无需复制。" -ForegroundColor Gray
} else {
    if (Test-Path $frontendEnvEx) {
        Copy-Item $frontendEnvEx $frontendEnv
        Write-Host " [OK] 已成功复制 sources/frontend/.env.example 到 .env" -ForegroundColor Green
    } else {
        Write-Error " [错误] 未找到 sources/frontend/.env.example 模版文件。"
    }
}
Write-Host ""

# 3. 下载 mkcert.exe (如果不存在)
Write-Host "[3/4] 检查并下载本地 HTTPS 证书工具 mkcert.exe..." -ForegroundColor Yellow
$mkcertPath = Join-Path $scriptDir "mkcert.exe"

if (Test-Path $mkcertPath) {
    Write-Host " [跳过] mkcert.exe 已存在，无需下载。" -ForegroundColor Gray
} else {
    Write-Host "正在从 GitHub 下载 mkcert.exe (版本 v1.4.4)..."
    Write-Host "如果直接下载较慢，将自动尝试国内镜像代理..."
    
    $url = "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-windows-amd64.exe"
    $proxy1 = "https://mirror.ghproxy.com/" + $url
    $proxy2 = "https://ghproxy.cn/" + $url
    
    $downloaded = $false
    
    # 尝试直接下载
    try {
        Write-Host "正在尝试直接从 GitHub 下载..."
        Invoke-WebRequest -Uri $url -OutFile $mkcertPath -TimeoutSec 15 -ErrorAction Stop
        Write-Host " [OK] 从 GitHub 下载成功！" -ForegroundColor Green
        $downloaded = $true
    } catch {
        Write-Host " [提示] 直接下载超时或失败，正在尝试镜像代理 1 (mirror.ghproxy.com)..." -ForegroundColor Cyan
    }
    
    # 尝试镜像 1
    if (-not $downloaded) {
        try {
            Invoke-WebRequest -Uri $proxy1 -OutFile $mkcertPath -TimeoutSec 30 -ErrorAction Stop
            Write-Host " [OK] 镜像 1 下载成功！" -ForegroundColor Green
            $downloaded = $true
        } catch {
            Write-Host " [提示] 镜像 1 失败，正在尝试镜像代理 2 (ghproxy.cn)..." -ForegroundColor Cyan
        }
    }
    
    # 尝试镜像 2
    if (-not $downloaded) {
        try {
            Invoke-WebRequest -Uri $proxy2 -OutFile $mkcertPath -TimeoutSec 30 -ErrorAction Stop
            Write-Host " [OK] 镜像 2 下载成功！" -ForegroundColor Green
            $downloaded = $true
        } catch {
            Write-Error " [错误] 所有下载路径均失败。请手动从 https://github.com/FiloSottile/mkcert/releases 下载 mkcert-v1.4.4-windows-amd64.exe 并重命名为 mkcert.exe 放至项目根目录。"
            exit 1
        }
    }
}
Write-Host ""

# 4. 配置本地 HTTPS 证书根证书 (可选)
Write-Host "[4/4] 配置本地开发 HTTPS 证书服务..." -ForegroundColor Yellow
if (-not (Test-Path $mkcertPath)) {
    Write-Warning " [警告] 未检测到 mkcert.exe，跳过证书配置。"
    exit 1
}

$choice = Read-Host "是否安装本地 HTTPS 根证书，实现 localhost 的浏览器安全 HTTPS 访问？[y/n]"
if ($choice -eq 'y' -or $choice -eq 'Y') {
    Write-Host ""
    Write-Host "正在安装本地根 CA 证书，需要系统管理员或 UAC 权限..." -ForegroundColor Cyan
    Write-Host "请在弹出的安全警告窗口中选择“是 [Yes]”以信任本地开发 CA 证书。" -ForegroundColor Cyan
    Write-Host ""
    
    # 请求 UAC 提升运行 -install
    Start-Process $mkcertPath -ArgumentList "-install" -Verb RunAs -Wait
    
    Write-Host ""
    Write-Host "正在生成本地 localhost 开发证书，包含 [localhost+2.pem] 和 [localhost+2-key.pem]..." -ForegroundColor Cyan
    
    # 在当前目录生成证书
    Set-Location $scriptDir
    & $mkcertPath localhost 127.0.0.1 ::1
    
    Write-Host ""
    Write-Host " [OK] HTTPS 根证书配置成功！" -ForegroundColor Green
    Write-Host " [提示] 后续运行 start_manual.bat 或 frontend_start.bat 时将自动启用安全 HTTPS，地址为 https://localhost:5173。" -ForegroundColor Green
} else {
    Write-Host " [跳过] 已跳过本地 HTTPS 证书安装。项目将默认使用常规 HTTP 模式运行。" -ForegroundColor Gray
}
Write-Host ""

Write-Host "===================================================" -ForegroundColor Green
Write-Host "             EDMS 项目初始化与配置完成！" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host "接下来，您可以通过以下方式运行项目："
Write-Host "  - 双击 start_manual.bat 启动前端与后端服务"
Write-Host ""
Read-Host "按回车键退出..."
