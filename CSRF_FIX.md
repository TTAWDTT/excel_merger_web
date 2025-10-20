# CSRF Token 修复

## 问题描述

```
Forbidden (CSRF token missing.): /api/tasks/16/charts/
[20/Oct/2025 19:05:11] "POST /api/tasks/16/charts/ HTTP/1.1" 403 2486
```

生成统计图表时出现403 Forbidden错误，原因是POST请求缺少CSRF token。

## 根本原因

Django的CSRF保护要求所有POST、PUT、DELETE等修改数据的请求必须包含CSRF token，但在添加新功能时忘记在部分API调用中添加此token。

## 已修复的API调用

### 1. 生成统计图表
```javascript
// 修复前
fetch(`/api/tasks/${currentTaskId}/charts/`, {
    method: 'POST'
});

// 修复后
fetch(`/api/tasks/${currentTaskId}/charts/`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    }
});
```

### 2. 运行数据验证
```javascript
// 修复前
await fetch('/api/validation-rules/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...})
});

// 修复后
await fetch('/api/validation-rules/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({...})
});
```

### 3. 应用模板
```javascript
// 修复后添加了 CSRF token
fetch(`/api/templates/${templateId}/apply/`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({task_id: currentTaskId})
});
```

### 4. 保存模板
```javascript
// 修复后添加了 CSRF token
fetch('/api/templates/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({...})
});
```

## 修复文件

- `merger/templates/merger/task_create.html` - 添加CSRF token到所有新功能的POST请求

## 测试步骤

1. 刷新页面（清除浏览器缓存）
2. 创建新任务并上传文件
3. 点击"生成统计图表"
4. 应该能正常生成，不再出现403错误

## 技术说明

### getCookie函数
页面中已有的辅助函数，用于从Cookie中获取CSRF token：
```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
```

### Django CSRF保护
Django默认启用CSRF保护，要求：
- 所有POST/PUT/DELETE请求必须包含有效的CSRF token
- Token可以通过Cookie获取
- 需要在请求头中设置 `X-CSRFToken`

## 状态

✅ **已修复** - 所有新增功能的API调用都已添加CSRF token

---

修复时间：2025年10月20日
