# 快速安装脚本
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   Excel 合并工具 - 快速安装向导    " -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "检查 Python 环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python 已安装: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python 未安装,请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host ""
Write-Host "安装 Python 依赖..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "✗ 依赖安装失败" -ForegroundColor Red
    exit 1
}

# 初始化数据库
Write-Host ""
Write-Host "初始化数据库..." -ForegroundColor Yellow
python manage.py makemigrations
python manage.py migrate

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 数据库初始化完成" -ForegroundColor Green
} else {
    Write-Host "✗ 数据库初始化失败" -ForegroundColor Red
    exit 1
}

# 创建管理员
Write-Host ""
Write-Host "是否创建管理员账号? (y/n)" -ForegroundColor Yellow
$createAdmin = Read-Host
if ($createAdmin -eq "y" -or $createAdmin -eq "Y") {
    python manage.py createsuperuser
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "   安装完成!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "运行以下命令启动服务器:" -ForegroundColor Cyan
Write-Host "  .\start.ps1" -ForegroundColor White
Write-Host ""
Write-Host "或直接运行:" -ForegroundColor Cyan
Write-Host "  python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "然后访问: http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host ""
