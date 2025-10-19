# Excel 合并工具 Web 版

基于 Django 的 Excel 文件合并与处理工具,提供友好的图形化界面。

## 功能特性

- 📁 **批量合并** - 支持上传多个 Excel 文件并合并
- 🔄 **智能对齐** - 自动识别相同列名进行智能对齐
- ➕ **列派生** - 根据列特征自动生成新列
- ✏️ **批量操作** - 对单元格进行批量修改
- 💾 **多格式支持** - 支持输出 XLS 和 XLSX 格式
- 🖼️ **图片保留** - 保留 Excel 中的嵌入图片

## 快速开始

### 1. 安装依赖

```powershell
cd excel_merger_web
pip install -r requirements.txt
```

### 2. 初始化数据库

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 3. 创建管理员账号(可选)

```powershell
python manage.py createsuperuser
```

### 4. 启动开发服务器

```powershell
python manage.py runserver
```

### 5. 访问应用

打开浏览器访问: http://127.0.0.1:8000/

## 使用指南

### 创建任务

1. 点击"开始使用"或"创建新任务"
2. 输入任务名称,选择输出格式
3. 上传需要合并的 Excel 文件
4. (可选)配置列派生规则
5. (可选)配置单元格批量操作
6. 点击"开始处理"执行任务
7. 下载处理完成的结果文件

### 列派生规则

根据现有列的特征自动生成新列,例如:

- 根据学号判断班级
- 根据邮箱判断邮箱类型
- 根据手机号判断运营商

配置项:
- **源列名**: 要提取信息的列
- **新列名**: 生成的新列名称
- **子串提取**: 提取源列的特定位置字符
- **映射规则**: 模式匹配和值映射

### 单元格操作

对指定列的所有单元格进行统一修改:

- **添加前缀/后缀**: 为所有单元格添加固定文本
- **删除前缀/后缀**: 删除单元格开头/结尾的文本
- **替换文本**: 将指定文本替换为新文本
- **指定位置插入**: 在特定位置插入字符
- **指定位置删除**: 删除特定位置的字符

## 项目结构

```
excel_merger_web/
├── excel_merger_web/       # 项目配置
│   ├── settings.py         # Django 设置
│   ├── urls.py             # 主路由
│   └── wsgi.py             # WSGI 配置
├── merger/                 # 主应用
│   ├── models.py           # 数据模型
│   ├── views.py            # 视图函数
│   ├── urls.py             # 应用路由
│   ├── admin.py            # 管理后台
│   ├── core/               # 核心逻辑
│   │   └── excel_processor.py  # Excel 处理
│   ├── templates/          # HTML 模板
│   │   ├── base.html       # 基础模板
│   │   └── merger/         # 应用模板
│   └── static/             # 静态文件
│       ├── css/            # 样式
│       └── js/             # JavaScript
├── media/                  # 媒体文件
│   ├── uploads/            # 上传文件
│   └── results/            # 结果文件
├── manage.py               # Django 管理脚本
└── requirements.txt        # 依赖列表
```

## API 接口

### 创建任务
POST `/api/tasks/create/`

### 上传文件
POST `/api/tasks/<task_id>/upload/`

### 添加列规则
POST `/api/tasks/<task_id>/column-rule/`

### 添加单元格操作
POST `/api/tasks/<task_id>/cell-operations/`

### 处理任务
POST `/api/tasks/<task_id>/process/`

### 下载结果
GET `/api/tasks/<task_id>/download/`

### 删除任务
POST `/api/tasks/<task_id>/delete/`

### 获取任务状态
GET `/api/tasks/<task_id>/status/`

## 数据模型

### MergeTask (合并任务)
- name: 任务名称
- status: 状态(pending/processing/completed/failed)
- output_format: 输出格式(xlsx/xls)
- result_file: 结果文件
- error_message: 错误信息

### UploadedFile (上传文件)
- task: 所属任务
- file: 文件
- original_filename: 原始文件名

### ColumnRule (列规则)
- task: 所属任务
- source_column: 源列名
- new_column: 新列名
- extraction_*: 提取配置
- mappings: 映射规则(JSON)

### CellOperation (单元格操作)
- task: 所属任务
- column: 列名
- action: 操作类型
- value: 值
- order: 执行顺序

## 管理后台

访问 http://127.0.0.1:8000/admin/ 可以查看和管理:

- 任务列表
- 上传文件
- 列规则
- 单元格操作

## 开发说明

### 添加新功能

1. 在 `models.py` 中定义数据模型
2. 在 `views.py` 中实现视图逻辑
3. 在 `urls.py` 中添加路由
4. 在 `templates/` 中创建前端页面
5. 运行迁移:
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```

### 静态文件

修改 CSS/JS 后,在生产环境需要收集静态文件:

```powershell
python manage.py collectstatic
```

## 部署

### 生产环境配置

1. 修改 `settings.py`:
   - 设置 `DEBUG = False`
   - 配置 `ALLOWED_HOSTS`
   - 修改 `SECRET_KEY`

2. 配置数据库(推荐 PostgreSQL)

3. 配置 Web 服务器(Nginx + Gunicorn)

4. 配置静态文件服务

## 常见问题

**Q: 上传文件大小限制?**
A: 默认限制 10MB,可在 `settings.py` 中修改 `FILE_UPLOAD_MAX_MEMORY_SIZE`

**Q: 支持哪些 Excel 格式?**
A: 输入仅支持 .xlsx 格式,输出支持 .xlsx 和 .xls

**Q: 任务处理失败怎么办?**
A: 查看任务详情页的错误信息,检查上传文件和配置规则

**Q: 如何批量删除任务?**
A: 可以在管理后台批量选择并删除

## 许可证

内部使用工具

## 联系方式

如有问题或建议,请联系开发者。
