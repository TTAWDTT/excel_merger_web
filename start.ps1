# 启动 Django 开发服务器
Write-Host "正在启动 Excel 合并工具..." -ForegroundColor Green

# 检查是否需要迁移
$migrationNeeded = $false
if (-not (Test-Path "db.sqlite3")) {
    $migrationNeeded = $true
}

if ($migrationNeeded) {
    Write-Host "首次运行,正在初始化数据库..." -ForegroundColor Yellow
    python manage.py makemigrations
    python manage.py migrate
    Write-Host "数据库初始化完成!" -ForegroundColor Green
    Write-Host ""
}

Write-Host "启动开发服务器..." -ForegroundColor Cyan
Write-Host "访问地址: http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host ""

python manage.py runserver
