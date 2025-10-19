# Excel 合并工具 - 使用说明

## 快速开始

### 方式一:使用安装脚本(推荐)

1. 打开 PowerShell,进入项目目录:
   ```powershell
   cd "d:\桌面\excel_work\excel_merger_web"
   ```

2. 运行安装脚本:
   ```powershell
   .\install.ps1
   ```

3. 安装完成后,运行启动脚本:
   ```powershell
   .\start.ps1
   ```

4. 打开浏览器访问: http://127.0.0.1:8000/

### 方式二:手动安装

1. 安装依赖:
   ```powershell
   pip install -r requirements.txt
   ```

2. 初始化数据库:
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```

3. (可选)创建管理员:
   ```powershell
   python manage.py createsuperuser
   ```

4. 启动服务器:
   ```powershell
   python manage.py runserver
   ```

5. 访问 http://127.0.0.1:8000/

## 功能使用

### 1. 创建合并任务

- 点击首页的"开始使用"按钮
- 按照步骤向导配置任务:
  1. 输入任务名称和选择输出格式
  2. 上传需要合并的 Excel 文件
  3. (可选)配置列派生规则
  4. (可选)配置单元格批量操作
  5. 点击"开始处理"

### 2. 查看任务列表

- 点击导航栏的"任务列表"
- 查看所有历史任务及其状态
- 点击任务名称查看详情
- 下载已完成任务的结果文件

### 3. 配置列派生规则

例如根据学号生成班级:

1. 勾选"启用列派生规则"
2. 源列名: `学号`
3. 新列名: `班级`
4. 勾选"启用子串提取"
5. 起始位置: `6`, 结束位置: `10`
6. 添加映射规则:
   - 模式: `0201`, 值: `植保1班`
   - 模式: `0202`, 值: `植保2班`
   - ...

### 4. 配置单元格操作

例如清理手机号格式:

1. 点击"添加操作"
2. 列名: `手机号`
3. 操作类型: `删除前缀`
4. 值: `+86`
5. 可以继续添加多个操作

## 管理后台

访问 http://127.0.0.1:8000/admin/ 可以:

- 查看所有任务
- 管理上传文件
- 编辑列规则和操作
- 批量删除任务

需要先创建管理员账号:
```powershell
python manage.py createsuperuser
```

## 常见问题

### Q: 如何停止服务器?
A: 在运行服务器的终端窗口按 `Ctrl+C`

### Q: 端口被占用怎么办?
A: 使用其他端口启动:
```powershell
python manage.py runserver 8001
```

### Q: 修改代码后需要重启吗?
A: Django 开发服务器会自动重载,无需手动重启

### Q: 上传文件保存在哪里?
A: `media/uploads/` 目录

### Q: 结果文件保存在哪里?
A: `media/results/` 目录

### Q: 如何清理旧文件?
A: 可以直接删除 `media/` 目录下的文件,或在管理后台删除任务

### Q: 数据库文件在哪?
A: `db.sqlite3` 文件,可以删除后重新初始化

## 技术支持

如遇问题,请检查:
1. Python 版本是否 ≥ 3.8
2. 依赖是否正确安装
3. 数据库是否正确初始化
4. 查看终端错误信息

## 下一步

- 自定义样式(修改 `merger/static/css/style.css`)
- 添加更多功能(修改 `merger/models.py` 和 `merger/views.py`)
- 部署到生产环境(配置 Nginx + Gunicorn)

祝使用愉快! 🎉
