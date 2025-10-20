# 文件类型支持说明

## 📋 概述

系统现在能够智能识别文件类型，并根据文件格式提供相应的功能。不同的功能对文件类型有不同的要求。

## 🎯 功能与文件类型对照表

| 功能 | 支持的文件类型 | 说明 |
|------|---------------|------|
| **文件上传** | XLSX, XLS, CSV, JSON | 所有格式均可上传 |
| **文件合并** | XLSX, XLS, CSV, JSON | 所有格式均可合并 |
| **数据预览** | XLSX, XLS, CSV | 仅表格类文件支持预览 |
| **数据清洗** | XLSX, XLS, CSV | 仅表格类文件支持 |
| **数据验证** | XLSX, XLS, CSV | 仅表格类文件支持 |
| **统计图表** | XLSX, XLS, CSV | 仅表格类文件支持 |

## 📊 详细说明

### 1. 数据预览功能

**支持格式**: `.xlsx`, `.xls`, `.csv`

**特点**:
- ✅ 显示前100行数据
- ✅ 显示列类型（int/float/str/datetime）
- ✅ 显示空值统计
- ✅ 显示行数/列数统计

**不支持格式**: `.json`

**原因**: JSON文件结构多样，可能是嵌套对象、数组等，不适合表格预览。

**界面行为**:
- Excel/CSV文件：显示 "预览数据" 按钮
- JSON文件：显示提示文字 "仅支持 Excel/CSV 预览"

### 2. 统计图表功能

**支持格式**: `.xlsx`, `.xls`, `.csv`

**生成的图表**:
- 📊 数值列统计（柱状图）
- 🥧 分类列分布（饼图）
- 📈 数据趋势分析

**不支持格式**: `.json`

**混合文件处理**:
- 如果任务中既有Excel/CSV又有JSON文件
- 系统会**自动跳过**JSON文件
- 仅使用Excel/CSV文件生成图表
- 显示警告信息：列出被跳过的文件

**示例警告消息**:
```
⚠️ 以下文件不支持图表分析，已跳过：data.json, config.json
```

### 3. 数据清洗和验证

**支持格式**: `.xlsx`, `.xls`, `.csv`

**可用的清洗规则**:
1. 去除重复行
2. 填充空值
3. 去除空格
4. 标准化大小写
5. 标准化日期
6. 移除特殊字符
7. 标准化电话号码

**可用的验证规则**:
1. 类型检查
2. 范围验证
3. 正则匹配
4. 非空检查
5. 唯一性检查
6. 长度检查
7. 枚举值检查

**应用时机**: 在任务处理时自动应用到表格类文件

## 🔧 技术实现

### 后端验证

**预览API** (`/api/files/<id>/preview/`)
```python
# 检查文件扩展名
supported_formats = ['.xlsx', '.xls', '.csv']
file_ext = Path(file_path).suffix.lower()

if file_ext not in supported_formats:
    return JsonResponse({
        'success': False,
        'error': '暂不支持 {ext} 格式的文件预览',
        'supported_formats': supported_formats
    }, status=400)
```

**图表API** (`/api/tasks/<id>/charts/`)
```python
# 过滤支持的文件
for file in files:
    file_ext = Path(file.path).suffix.lower()
    if file_ext in ['.xlsx', '.xls', '.csv']:
        file_paths.append(file.path)
    else:
        unsupported_files.append(file.name)

# 返回警告信息
if unsupported_files:
    response['warning'] = f'以下文件不支持图表分析，已跳过：{", ".join(unsupported_files)}'
```

### 前端处理

**预览按钮显示逻辑**:
```javascript
const supportedFormats = ['.xlsx', '.xls', '.csv'];
const fileName = file.name.toLowerCase();
const isSupported = supportedFormats.some(ext => fileName.endsWith(ext));

if (isSupported) {
    // 显示预览按钮
} else {
    // 显示提示文字
}
```

**图表警告显示**:
```javascript
if (data.warning) {
    showToast(data.warning, 'warning');
    // 在图表弹窗中也显示警告
}
```

## 💡 使用建议

### 场景1: 纯Excel/CSV任务
```
✅ 所有功能都可用
✅ 预览、清洗、验证、图表全部支持
```

### 场景2: 纯JSON任务
```
✅ 可以上传和合并
❌ 不支持预览
❌ 不支持数据清洗
❌ 不支持数据验证
❌ 不支持统计图表
```

### 场景3: 混合文件任务（Excel + JSON）
```
✅ 所有文件都可上传
✅ 所有文件都可合并
✅ Excel文件可以预览
❌ JSON文件不显示预览按钮
✅ 图表生成时自动跳过JSON文件
⚠️ 会显示警告提示
```

## 📱 用户界面提示

### 预览功能
**Excel/CSV文件**:
```
[文件名.xlsx] [123 KB]  [预览数据]
```

**JSON文件**:
```
[文件名.json] [45 KB]  [ℹ️ 仅支持 Excel/CSV 预览]
```

### 图表功能
**所有文件支持**:
```
✅ 图表生成成功
显示：5个图表（基于3个Excel文件）
```

**部分文件不支持**:
```
⚠️ 以下文件不支持图表分析，已跳过：config.json
✅ 图表生成成功
显示：5个图表（基于2个Excel文件）
```

**所有文件都不支持**:
```
❌ 所有文件都不支持图表生成
支持的格式：Excel (.xlsx, .xls) 和 CSV (.csv)
```

## 🎯 最佳实践

### 推荐做法

1. **按文件类型分组任务**
   - Excel/CSV数据文件用一个任务
   - JSON配置文件用另一个任务

2. **充分利用预览功能**
   - 上传Excel/CSV后先预览
   - 根据预览结果配置清洗规则

3. **注意警告信息**
   - 查看图表生成时的警告
   - 了解哪些文件被跳过

### 避免问题

1. **不要期望JSON文件预览**
   - JSON结构复杂，不适合表格展示
   - 如需查看JSON，请使用文本编辑器

2. **混合任务时注意统计结果**
   - 图表只基于Excel/CSV文件
   - JSON文件数据不会出现在图表中

3. **清洗规则只对表格有效**
   - JSON文件不会应用清洗规则
   - 验证规则也仅针对表格数据

## 🔮 未来扩展

### 可能的改进方向

1. **JSON预览支持**
   - 树形结构展示
   - 语法高亮显示
   - 折叠/展开节点

2. **更多文件格式**
   - XML文件支持
   - YAML文件支持
   - 数据库导出文件

3. **智能格式检测**
   - 自动识别分隔符（CSV）
   - 自动检测编码
   - 智能推断数据类型

## ⚠️ 当前限制

1. **JSON文件**
   - ❌ 无法预览
   - ❌ 无法生成图表
   - ❌ 无法应用清洗规则
   - ❌ 无法应用验证规则
   - ✅ 可以合并（转换为表格格式）

2. **其他格式**
   - 目前仅支持 XLSX, XLS, CSV, JSON
   - 其他格式需要先转换

## 📞 错误消息说明

### 预览失败
```
错误: 暂不支持 .json 格式的文件预览
支持的格式：Excel (.xlsx, .xls) 和 CSV (.csv)
```
**解决方案**: 此为正常提示，JSON文件不支持预览功能。

### 图表生成失败（全部不支持）
```
错误: 所有文件都不支持图表生成
支持的格式：Excel (.xlsx, .xls) 和 CSV (.csv)
```
**解决方案**: 任务中至少需要包含一个Excel或CSV文件。

### 图表生成警告（部分不支持）
```
⚠️ 以下文件不支持图表分析，已跳过：data.json
```
**解决方案**: 这是正常警告，不影响其他文件的图表生成。

## 📚 相关文档

- `UI_USER_GUIDE.md` - 用户使用指南
- `QUICK_REFERENCE.md` - 快速参考
- `FEATURES_READY.md` - 功能概览

---

**总结**: 系统现在能够智能处理不同文件类型，为Excel/CSV文件提供完整功能，同时优雅地处理JSON等其他格式文件。
