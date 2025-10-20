# 🚀 快速使用指南 - 新功能版

## 📦 已完成的5大扩展功能

### ✅ 1. 数据预览 - 上传后实时查看数据
### ✅ 2. 模板系统 - 保存和复用配置
### ✅ 3. 数据清洗 - 自动处理脏数据
### ✅ 4. 数据验证 - 确保数据质量
### ✅ 5. 可视化报表 - 自动生成统计图表

---

## 🎯 功能演示

### 功能1: 数据预览

**使用场景**: 上传文件后立即查看文件内容，无需下载处理

**步骤**:
1. 访问 http://127.0.0.1:8000/tasks/create/
2. 填写任务名称和选择输出格式
3. 点击"下一步"
4. 上传Excel/CSV/JSON文件
5. 文件上传成功后，文件列表会显示"预览"按钮
6. 点击"预览"按钮

**预览内容包括**:
- 📊 总行数、总列数、文件大小
- 🏷️ 列类型分布（数字、文本、日期、邮箱、电话）
- ⚠️ 空值统计（每列空值数量和百分比）
- 📋 前100行数据表格

**API调用示例**:
```javascript
// 通过文件ID预览
await previewFile(123);
```

**API端点**:
```
GET /api/files/123/preview/
```

---

### 功能2: 模板系统

**使用场景**: 经常处理相同类型的数据，每次都要重新配置太麻烦

**步骤**:

#### 保存模板:
1. 完成任务配置（输出格式、列规则、单元格操作等）
2. 在页面调用 `saveAsTemplate()` 函数
3. 输入模板名称和描述
4. 保存成功

#### 使用模板:
1. 创建新任务
2. 在模板列表中选择合适的模板
3. 点击"应用"按钮
4. 所有配置自动填充

**模板包含的配置**:
- 输出格式（XLSX/XLS/CSV/JSON）
- 列过滤模式和过滤列
- 列派生规则
- 单元格操作
- **数据清洗规则** ✨
- **数据验证规则** ✨

**API示例**:
```javascript
// 保存模板
await saveAsTemplate();

// 应用模板
await applyTemplate(templateId);

// 获取所有模板
const templates = await fetch('/api/templates/').then(r => r.json());
```

---

### 功能3: 数据清洗

**使用场景**: 数据有重复、空值、格式不统一等问题

**支持的清洗操作**:

#### 1. 删除重复行
```javascript
{
    "action": "remove_duplicates",
    "columns": ["学号"],  // 按学号判断重复
    "parameters": {}
}
```

#### 2. 填充空值
```javascript
{
    "action": "fill_null",
    "columns": ["姓名", "班级"],
    "parameters": {
        "method": "forward"  // 向前填充 | backward | value | mean | median
    }
}
```

#### 3. 转换数据类型
```javascript
{
    "action": "convert_type",
    "columns": ["年龄", "成绩"],
    "parameters": {
        "type": "integer"  // integer | float | string
    }
}
```

#### 4. 去除空格
```javascript
{
    "action": "trim_spaces",
    "columns": ["姓名", "地址"]
}
```

#### 5. 标准化日期
```javascript
{
    "action": "standardize_date",
    "columns": ["注册日期"],
    "parameters": {
        "format": "%Y-%m-%d"  // 统一输出格式
    }
}
```

#### 6. 转大写/小写
```javascript
{
    "action": "uppercase",  // 或 lowercase
    "columns": ["省份"]
}
```

**完整示例**:
```javascript
// 添加多个清洗规则
cleaningRules = [
    {
        action: 'remove_duplicates',
        columns: ['学号'],
        parameters: {},
        order: 0
    },
    {
        action: 'fill_null',
        columns: ['姓名'],
        parameters: {method: 'forward'},
        order: 1
    },
    {
        action: 'trim_spaces',
        columns: ['地址'],
        parameters: {},
        order: 2
    }
];

// 提交到服务器
await submitCleaningRules();
```

**API端点**:
```
POST /api/tasks/<task_id>/cleaning-rules/
Body: {"rules": [...]}
```

---

### 功能4: 数据验证

**使用场景**: 确保数据符合业务规则，处理前发现问题

**支持的验证规则**:

#### 1. 必填字段
```javascript
{
    "column": "学号",
    "rule_type": "required",
    "error_message": "学号不能为空"
}
```

#### 2. 数据类型验证
```javascript
{
    "column": "邮箱",
    "rule_type": "type",
    "parameters": {"type": "email"},  // number | integer | email | phone | date
    "error_message": "邮箱格式不正确"
}
```

#### 3. 数值范围
```javascript
{
    "column": "年龄",
    "rule_type": "range",
    "parameters": {"min": 0, "max": 150},
    "error_message": "年龄必须在0-150之间"
}
```

#### 4. 长度限制
```javascript
{
    "column": "学号",
    "rule_type": "length",
    "parameters": {"min": 10, "max": 10},
    "error_message": "学号必须是10位"
}
```

#### 5. 正则表达式
```javascript
{
    "column": "身份证号",
    "rule_type": "regex",
    "parameters": {"pattern": "^\\d{18}$"},
    "error_message": "身份证号格式不正确"
}
```

#### 6. 唯一性
```javascript
{
    "column": "学号",
    "rule_type": "unique",
    "error_message": "学号不能重复"
}
```

#### 7. 枚举值
```javascript
{
    "column": "性别",
    "rule_type": "enum",
    "parameters": {"values": ["男", "女"]},
    "error_message": "性别只能是男或女"
}
```

**完整示例**:
```javascript
// 添加验证规则
validationRules = [
    {
        column: '学号',
        rule_type: 'required'
    },
    {
        column: '学号',
        rule_type: 'unique'
    },
    {
        column: '成绩',
        rule_type: 'range',
        parameters: {min: 0, max: 100},
        error_message: '成绩必须在0-100之间'
    },
    {
        column: '邮箱',
        rule_type: 'type',
        parameters: {type: 'email'}
    }
];

// 提交到服务器
await submitValidationRules();

// 执行验证
await fetch(`/api/tasks/${taskId}/validate/`, {method: 'POST'});
```

**验证结果示例**:
```json
{
    "is_valid": false,
    "errors": [
        {
            "row": 15,
            "column": "年龄",
            "value": 200,
            "message": "年龄必须在0-150之间"
        },
        {
            "row": 23,
            "column": "学号",
            "value": null,
            "message": "学号不能为空"
        }
    ],
    "warnings": [],
    "statistics": {
        "total_rows": 1000,
        "total_errors": 5,
        "total_warnings": 0,
        "error_rate": 0.005
    }
}
```

---

### 功能5: 可视化报表

**使用场景**: 处理后想了解数据分布和质量

**生成的图表**:

#### 1. 数据分布柱状图
- 总行数
- 总列数

#### 2. 列类型饼图
- 数字列数量
- 文本列数量
- 日期列数量
- 其他类型

#### 3. 空值分析柱状图
- 每列的空值数量
- 空值百分比

#### 4. 数值列统计表
| 列名 | 最小值 | 最大值 | 平均值 | 中位数 | 数据量 |
|------|--------|--------|--------|--------|--------|
| 年龄 | 18     | 65     | 32.5   | 30     | 1000   |
| 成绩 | 0      | 100    | 75.3   | 78     | 1000   |

#### 5. 文本列频率分析
- 显示前10个最常见的值
- 总数和唯一值数

**使用方式**:
```javascript
// 生成图表
await generateCharts(taskId);

// API调用
const response = await fetch(`/api/tasks/${taskId}/charts/`);
const result = await response.json();
console.log(result.charts);
```

**API端点**:
```
GET /api/tasks/<task_id>/charts/
```

---

## 🎮 完整工作流程

### 场景: 处理学生成绩表

```javascript
// 1. 创建任务
const task = await fetch('/api/tasks/create/', {
    method: 'POST',
    body: JSON.stringify({
        name: '2024学年成绩处理',
        output_format: 'xlsx'
    })
});
const {task_id} = await task.json();

// 2. 上传文件
const formData = new FormData();
formData.append('files', file1);
formData.append('files', file2);
await fetch(`/api/tasks/${task_id}/upload/`, {
    method: 'POST',
    body: formData
});

// 3. 预览文件（可选）
await previewFile(fileId);

// 4. 添加数据清洗规则
await fetch(`/api/tasks/${task_id}/cleaning-rules/`, {
    method: 'POST',
    body: JSON.stringify({
        rules: [
            {
                action: 'remove_duplicates',
                columns: ['学号'],
                parameters: {},
                order: 0
            },
            {
                action: 'fill_null',
                columns: ['姓名'],
                parameters: {method: 'forward'},
                order: 1
            },
            {
                action: 'convert_type',
                columns: ['成绩'],
                parameters: {type: 'float'},
                order: 2
            }
        ]
    })
});

// 5. 添加数据验证规则
await fetch(`/api/tasks/${task_id}/validation-rules/`, {
    method: 'POST',
    body: JSON.stringify({
        rules: [
            {
                column: '学号',
                rule_type: 'required'
            },
            {
                column: '学号',
                rule_type: 'unique'
            },
            {
                column: '成绩',
                rule_type: 'range',
                parameters: {min: 0, max: 100},
                error_message: '成绩必须在0-100之间'
            }
        ]
    })
});

// 6. 执行处理
await fetch(`/api/tasks/${task_id}/process/`, {method: 'POST'});

// 7. 查看统计图表
await generateCharts(task_id);

// 8. 下载结果
window.location.href = `/api/tasks/${task_id}/download/`;

// 9. 保存为模板（供下次使用）
await saveAsTemplate();
```

---

## 🔧 数据库迁移

所有新功能都已创建数据库迁移并应用：

```bash
# 已执行的迁移
python manage.py makemigrations  # 创建迁移文件
python manage.py migrate         # 应用迁移

# 新增的表
- merger_tasktemplate           # 任务模板
- merger_filepreview            # 文件预览
- merger_datacleaningrule       # 数据清洗规则
- merger_datavalidationrule     # 数据验证规则
- merger_validationresult       # 验证结果
```

---

## 📊 性能优化

### 预览功能
- ✅ 只读取前100行
- ✅ 预览数据缓存到数据库
- ✅ 避免重复分析

### 清洗和验证
- ✅ 按顺序执行规则
- ✅ 支持部分列处理
- ✅ 错误提前中断（可配置）

### 图表生成
- ✅ 客户端渲染
- ✅ 数据采样（大数据集）
- ✅ 延迟加载

---

## 🎯 实际案例

### 案例1: 客户数据清洗

**原始数据问题**:
- 姓名有多余空格
- 电话格式不统一
- 邮箱有错误
- 有重复记录

**解决方案**:
```javascript
// 清洗规则
cleaningRules = [
    {action: 'trim_spaces', columns: ['姓名', '公司']},
    {action: 'remove_duplicates', columns: ['电话']},
    {action: 'lowercase', columns: ['邮箱']}
];

// 验证规则
validationRules = [
    {column: '姓名', rule_type: 'required'},
    {column: '电话', rule_type: 'type', parameters: {type: 'phone'}},
    {column: '邮箱', rule_type: 'type', parameters: {type: 'email'}}
];
```

### 案例2: 财务数据合并

**需求**:
- 多个分公司Excel合并
- 金额格式统一
- 日期标准化
- 数值范围验证

**解决方案**:
```javascript
// 清洗规则
cleaningRules = [
    {action: 'convert_type', columns: ['金额'], parameters: {type: 'float'}},
    {action: 'standardize_date', columns: ['交易日期']},
    {action: 'trim_spaces', columns: ['备注']}
];

// 验证规则
validationRules = [
    {column: '金额', rule_type: 'range', parameters: {min: 0}},
    {column: '交易日期', rule_type: 'required'},
    {column: '分公司', rule_type: 'enum', parameters: {values: ['北京', '上海', '广州']}}
];
```

---

## 🌟 亮点功能

### 1. 智能列类型识别
自动识别：
- 📧 邮箱格式
- 📱 电话号码
- 📅 日期格式
- 🔢 数值类型

### 2. 可视化数据质量
- 空值热力图
- 类型分布饼图
- 统计箱线图

### 3. 模板复用
- 一次配置，永久使用
- 团队共享配置
- 快速应用

### 4. 数据验证报告
- 详细错误定位（行号+列名）
- 错误率统计
- 导出验证报告

---

## 🚀 快速开始

```bash
# 1. 启动服务器
python manage.py runserver

# 2. 访问系统
http://127.0.0.1:8000/

# 3. 创建第一个任务
http://127.0.0.1:8000/tasks/create/

# 4. 上传文件并预览

# 5. 添加清洗和验证规则

# 6. 执行处理

# 7. 查看统计图表

# 8. 下载结果

# 9. 保存为模板
```

---

## 📖 更多文档

- **完整功能文档**: `ENHANCEMENTS_GUIDE.md`
- **API文档**: 查看各API端点的详细说明
- **未来扩展**: `FUTURE_ENHANCEMENTS.md`

---

**系统状态**: ✅ 所有功能已完成并测试
**服务器**: 🟢 运行中 (http://127.0.0.1:8000/)
**数据库**: ✅ 迁移已应用
**前端**: ✅ 所有JS和CSS已加载

**版本**: v4.0
**更新时间**: 2025-10-20
