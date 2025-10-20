/**
 * 增强功能模块 - 数据预览、模板、清洗、验证、可视化
 */

// ==================== 数据预览功能 ====================

/**
 * 预览上传的文件
 */
async function previewFile(fileId) {
    try {
        showLoading('正在加载数据预览...');
        
        const response = await fetch(`/api/files/${fileId}/preview/`);
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showPreviewModal(result.preview);
        } else {
            showError('预览失败: ' + result.error);
        }
    } catch (error) {
        hideLoading();
        showError('预览失败: ' + error.message);
    }
}

/**
 * 显示预览模态框
 */
function showPreviewModal(preview) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content modal-large">
            <div class="modal-header">
                <h3><i class="fas fa-eye"></i> 数据预览</h3>
                <button class="modal-close" onclick="closeModal(this)">&times;</button>
            </div>
            <div class="modal-body">
                <!-- 文件统计信息 -->
                <div class="preview-stats">
                    <div class="stat-card">
                        <div class="stat-value">${preview.total_rows}</div>
                        <div class="stat-label">总行数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${preview.total_columns}</div>
                        <div class="stat-label">总列数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${formatFileSize(preview.file_size)}</div>
                        <div class="stat-label">文件大小</div>
                    </div>
                </div>
                
                <!-- 列类型分布 -->
                <div class="preview-section">
                    <h4><i class="fas fa-info-circle"></i> 列类型分布</h4>
                    <div class="column-types">
                        ${Object.entries(preview.column_types).slice(0, 10).map(([col, type]) => `
                            <span class="type-badge type-${type}">${col}: ${type}</span>
                        `).join('')}
                    </div>
                </div>
                
                <!-- 空值统计 -->
                <div class="preview-section">
                    <h4><i class="fas fa-exclamation-triangle"></i> 空值统计</h4>
                    <div class="null-stats">
                        ${Object.entries(preview.null_counts)
                            .filter(([col, count]) => count > 0)
                            .slice(0, 5)
                            .map(([col, count]) => `
                                <div class="null-stat-item">
                                    <span class="null-column">${col}</span>
                                    <span class="null-count">${count} 个空值</span>
                                    <span class="null-percent">${((count / preview.total_rows) * 100).toFixed(1)}%</span>
                                </div>
                            `).join('') || '<p class="text-muted">没有空值</p>'}
                    </div>
                </div>
                
                <!-- 数据预览表格 -->
                <div class="preview-section">
                    <h4><i class="fas fa-table"></i> 数据预览 (前 ${Math.min(preview.sample_rows.length, 100)} 行)</h4>
                    <div class="table-wrapper">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    ${preview.headers.map(h => `<th>${h}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${preview.sample_rows.slice(0, 100).map((row, idx) => `
                                    <tr>
                                        <td>${idx + 1}</td>
                                        ${row.map(cell => `<td>${cell !== null && cell !== '' ? cell : '<span class="null-value">-</span>'}</td>`).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal(this)">关闭</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 添加点击外部关闭功能
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal(modal.querySelector('.modal-close'));
        }
    });
}

// ==================== 模板功能 ====================

let templates = [];

/**
 * 加载模板列表
 */
async function loadTemplates() {
    try {
        const response = await fetch('/api/templates/');
        const result = await response.json();
        
        if (result.success) {
            templates = result.templates;
            renderTemplateList();
        }
    } catch (error) {
        console.error('加载模板失败:', error);
    }
}

/**
 * 渲染模板列表
 */
function renderTemplateList() {
    const container = document.getElementById('template-list');
    if (!container) return;
    
    if (templates.length === 0) {
        container.innerHTML = '<p class="text-muted">还没有保存的模板</p>';
        return;
    }
    
    container.innerHTML = templates.map(t => `
        <div class="template-card" data-id="${t.id}">
            <div class="template-header">
                <h4>${t.name}</h4>
                <span class="template-format">${t.output_format.toUpperCase()}</span>
            </div>
            <p class="template-description">${t.description || '无描述'}</p>
            <div class="template-actions">
                <button class="btn btn-sm btn-primary" onclick="applyTemplate(${t.id})">
                    <i class="fas fa-check"></i> 应用
                </button>
                <button class="btn btn-sm btn-secondary" onclick="viewTemplate(${t.id})">
                    <i class="fas fa-eye"></i> 查看
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteTemplate(${t.id})">
                    <i class="fas fa-trash"></i> 删除
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * 保存当前配置为模板
 */
async function saveAsTemplate() {
    const name = prompt('请输入模板名称:');
    if (!name) return;
    
    const description = prompt('请输入模板描述 (可选):');
    
    const templateData = {
        name: name,
        description: description || '',
        output_format: document.getElementById('output-format').value,
        filter_mode: document.getElementById('filter-mode').value,
        filter_columns: getFilterColumns(),
        column_rule_config: getCurrentColumnRule(),
        cell_operations_config: getCurrentCellOperations(),
        cleaning_config: getCurrentCleaningConfig(),
        validation_config: getCurrentValidationConfig()
    };
    
    try {
        showLoading('正在保存模板...');
        
        const response = await fetch('/api/templates/save/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(templateData)
        });
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showSuccess('模板保存成功!');
            loadTemplates();
        } else {
            showError('保存失败: ' + result.error);
        }
    } catch (error) {
        hideLoading();
        showError('保存失败: ' + error.message);
    }
}

/**
 * 应用模板到当前任务
 */
async function applyTemplate(templateId) {
    if (!currentTaskId) {
        showError('请先创建任务');
        return;
    }
    
    try {
        showLoading('正在应用模板...');
        
        const response = await fetch(`/api/tasks/${currentTaskId}/apply-template/${templateId}/`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showSuccess('模板应用成功!');
            // 重新加载任务配置
            location.reload();
        } else {
            showError('应用失败: ' + result.error);
        }
    } catch (error) {
        hideLoading();
        showError('应用失败: ' + error.message);
    }
}

// ==================== 数据清洗功能 ====================

let cleaningRules = [];

/**
 * 添加清洗规则
 */
function addCleaningRule() {
    const ruleType = document.getElementById('cleaning-rule-type').value;
    const columns = document.getElementById('cleaning-columns').value.split('\n').filter(c => c.trim());
    
    if (columns.length === 0) {
        showError('请输入要清洗的列名');
        return;
    }
    
    const rule = {
        action: ruleType,
        columns: columns,
        parameters: getCleaningParameters(ruleType),
        order: cleaningRules.length
    };
    
    cleaningRules.push(rule);
    renderCleaningRules();
    
    // 清空输入
    document.getElementById('cleaning-columns').value = '';
}

/**
 * 获取清洗参数
 */
function getCleaningParameters(ruleType) {
    const params = {};
    
    switch (ruleType) {
        case 'fill_null':
            params.method = document.getElementById('fill-method')?.value || 'forward';
            params.value = document.getElementById('fill-value')?.value || '';
            break;
        case 'convert_type':
            params.type = document.getElementById('target-type')?.value || 'string';
            break;
        case 'standardize_date':
            params.format = document.getElementById('date-format')?.value || '%Y-%m-%d';
            break;
    }
    
    return params;
}

/**
 * 渲染清洗规则列表
 */
function renderCleaningRules() {
    const container = document.getElementById('cleaning-rules-list');
    if (!container) return;
    
    if (cleaningRules.length === 0) {
        container.innerHTML = '<p class="text-muted">还没有添加清洗规则</p>';
        return;
    }
    
    const actionNames = {
        'remove_duplicates': '删除重复行',
        'fill_null': '填充空值',
        'convert_type': '转换数据类型',
        'trim_spaces': '去除空格',
        'standardize_date': '标准化日期',
        'uppercase': '转大写',
        'lowercase': '转小写'
    };
    
    container.innerHTML = cleaningRules.map((rule, idx) => `
        <div class="rule-card">
            <div class="rule-header">
                <span class="rule-order">#${idx + 1}</span>
                <strong>${actionNames[rule.action]}</strong>
            </div>
            <div class="rule-body">
                <div class="rule-info">列: ${rule.columns.join(', ')}</div>
                ${Object.keys(rule.parameters).length > 0 ? `
                    <div class="rule-params">参数: ${JSON.stringify(rule.parameters)}</div>
                ` : ''}
            </div>
            <button class="btn btn-sm btn-danger" onclick="removeCleaningRule(${idx})">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

/**
 * 删除清洗规则
 */
function removeCleaningRule(index) {
    cleaningRules.splice(index, 1);
    renderCleaningRules();
}

/**
 * 提交清洗规则到服务器
 */
async function submitCleaningRules() {
    if (!currentTaskId) {
        showError('请先创建任务');
        return;
    }
    
    if (cleaningRules.length === 0) {
        return; // 没有规则就跳过
    }
    
    try {
        const response = await fetch(`/api/tasks/${currentTaskId}/cleaning-rules/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({rules: cleaningRules})
        });
        
        const result = await response.json();
        
        if (result.success) {
            return true;
        } else {
            showError('添加清洗规则失败: ' + result.error);
            return false;
        }
    } catch (error) {
        showError('添加清洗规则失败: ' + error.message);
        return false;
    }
}

// ==================== 数据验证功能 ====================

let validationRules = [];

/**
 * 添加验证规则
 */
function addValidationRule() {
    const column = document.getElementById('validation-column').value.trim();
    const ruleType = document.getElementById('validation-rule-type').value;
    
    if (!column) {
        showError('请输入列名');
        return;
    }
    
    const rule = {
        column: column,
        rule_type: ruleType,
        parameters: getValidationParameters(ruleType),
        error_message: document.getElementById('validation-error-msg')?.value || ''
    };
    
    validationRules.push(rule);
    renderValidationRules();
    
    // 清空输入
    document.getElementById('validation-column').value = '';
    document.getElementById('validation-error-msg').value = '';
}

/**
 * 获取验证参数
 */
function getValidationParameters(ruleType) {
    const params = {};
    
    switch (ruleType) {
        case 'type':
            params.type = document.getElementById('validation-type')?.value || 'string';
            break;
        case 'range':
            params.min = parseFloat(document.getElementById('range-min')?.value) || null;
            params.max = parseFloat(document.getElementById('range-max')?.value) || null;
            break;
        case 'length':
            params.min = parseInt(document.getElementById('length-min')?.value) || null;
            params.max = parseInt(document.getElementById('length-max')?.value) || null;
            break;
        case 'regex':
            params.pattern = document.getElementById('regex-pattern')?.value || '';
            break;
        case 'enum':
            const values = document.getElementById('enum-values')?.value || '';
            params.values = values.split('\n').filter(v => v.trim());
            break;
    }
    
    return params;
}

/**
 * 渲染验证规则列表
 */
function renderValidationRules() {
    const container = document.getElementById('validation-rules-list');
    if (!container) return;
    
    if (validationRules.length === 0) {
        container.innerHTML = '<p class="text-muted">还没有添加验证规则</p>';
        return;
    }
    
    const ruleNames = {
        'required': '必填字段',
        'type': '数据类型',
        'range': '数值范围',
        'length': '长度限制',
        'regex': '正则表达式',
        'unique': '唯一性',
        'enum': '枚举值'
    };
    
    container.innerHTML = validationRules.map((rule, idx) => `
        <div class="rule-card">
            <div class="rule-header">
                <span class="rule-order">#${idx + 1}</span>
                <strong>${rule.column}</strong>
                <span class="rule-type">${ruleNames[rule.rule_type]}</span>
            </div>
            <div class="rule-body">
                ${Object.keys(rule.parameters).length > 0 ? `
                    <div class="rule-params">参数: ${JSON.stringify(rule.parameters)}</div>
                ` : ''}
                ${rule.error_message ? `
                    <div class="rule-error">错误提示: ${rule.error_message}</div>
                ` : ''}
            </div>
            <button class="btn btn-sm btn-danger" onclick="removeValidationRule(${idx})">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

/**
 * 删除验证规则
 */
function removeValidationRule(index) {
    validationRules.splice(index, 1);
    renderValidationRules();
}

/**
 * 提交验证规则到服务器
 */
async function submitValidationRules() {
    if (!currentTaskId) {
        showError('请先创建任务');
        return;
    }
    
    if (validationRules.length === 0) {
        return; // 没有规则就跳过
    }
    
    try {
        const response = await fetch(`/api/tasks/${currentTaskId}/validation-rules/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({rules: validationRules})
        });
        
        const result = await response.json();
        
        if (result.success) {
            return true;
        } else {
            showError('添加验证规则失败: ' + result.error);
            return false;
        }
    } catch (error) {
        showError('添加验证规则失败: ' + error.message);
        return false;
    }
}

// ==================== 可视化图表功能 ====================

/**
 * 生成并显示统计图表
 */
async function generateCharts(taskId) {
    try {
        showLoading('正在生成统计图表...');
        
        const response = await fetch(`/api/tasks/${taskId}/charts/`);
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showChartsModal(result.charts, result.statistics);
        } else {
            showError('生成图表失败: ' + result.error);
        }
    } catch (error) {
        hideLoading();
        showError('生成图表失败: ' + error.message);
    }
}

/**
 * 显示图表模态框
 */
function showChartsModal(charts, statistics) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content modal-xlarge">
            <div class="modal-header">
                <h3><i class="fas fa-chart-bar"></i> 数据分析报表</h3>
                <button class="modal-close" onclick="closeModal(this)">&times;</button>
            </div>
            <div class="modal-body">
                <div class="charts-container">
                    ${renderChart(charts.data_distribution)}
                    ${renderChart(charts.column_types)}
                    ${renderChart(charts.null_analysis)}
                    ${renderNumericStats(charts.numeric_stats)}
                    ${renderTextFrequency(charts.text_frequency)}
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal(this)">关闭</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

/**
 * 渲染图表
 */
function renderChart(chart) {
    if (chart.type === 'bar') {
        return `
            <div class="chart-card">
                <h4>${chart.title}</h4>
                <div class="bar-chart">
                    ${chart.data.categories.map((cat, idx) => `
                        <div class="bar-item">
                            <div class="bar-label">${cat}</div>
                            <div class="bar-wrapper">
                                <div class="bar-fill" style="width: ${(chart.data.values[idx] / Math.max(...chart.data.values)) * 100}%"></div>
                                <span class="bar-value">${chart.data.values[idx]}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else if (chart.type === 'pie') {
        const total = chart.data.values.reduce((a, b) => a + b, 0);
        return `
            <div class="chart-card">
                <h4>${chart.title}</h4>
                <div class="pie-chart">
                    ${chart.data.labels.map((label, idx) => {
                        const percent = ((chart.data.values[idx] / total) * 100).toFixed(1);
                        return `
                            <div class="pie-item">
                                <span class="pie-color" style="background: ${getChartColor(idx)}"></span>
                                <span class="pie-label">${label}</span>
                                <span class="pie-value">${chart.data.values[idx]} (${percent}%)</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }
    return '';
}

/**
 * 渲染数值统计
 */
function renderNumericStats(chart) {
    if (!chart.data || chart.data.length === 0) {
        return '';
    }
    
    return `
        <div class="chart-card full-width">
            <h4>${chart.title}</h4>
            <div class="stats-table">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>列名</th>
                            <th>最小值</th>
                            <th>最大值</th>
                            <th>平均值</th>
                            <th>中位数</th>
                            <th>数据量</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${chart.data.map(stat => `
                            <tr>
                                <td><strong>${stat.column}</strong></td>
                                <td>${stat.min.toFixed(2)}</td>
                                <td>${stat.max.toFixed(2)}</td>
                                <td>${stat.mean.toFixed(2)}</td>
                                <td>${stat.median.toFixed(2)}</td>
                                <td>${stat.count}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

/**
 * 渲染文本频率
 */
function renderTextFrequency(chart) {
    if (!chart.data || Object.keys(chart.data).length === 0) {
        return '';
    }
    
    return `
        <div class="chart-card full-width">
            <h4>${chart.title}</h4>
            <div class="text-frequency">
                ${Object.entries(chart.data).map(([column, freq]) => `
                    <div class="frequency-section">
                        <h5>${column}</h5>
                        <p>总计: ${freq.total_count} | 唯一值: ${freq.unique_count}</p>
                        <div class="frequency-list">
                            ${freq.most_common.map(([value, count]) => `
                                <span class="frequency-tag">
                                    ${value} <span class="frequency-count">(${count})</span>
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ==================== 工具函数 ====================

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function getChartColor(index) {
    const colors = [
        '#4A90E2', '#7B68EE', '#50C878', '#FFB347', 
        '#FF6B6B', '#95E1D3', '#F38181', '#AA96DA'
    ];
    return colors[index % colors.length];
}

function closeModal(button) {
    const modal = button.closest('.modal-overlay');
    if (modal) {
        modal.remove();
    }
}

function getCurrentColumnRule() {
    // 从表单获取当前的列规则配置
    // 这需要根据实际的表单结构实现
    return null;
}

function getCurrentCellOperations() {
    // 从表单获取当前的单元格操作
    return [];
}

function getCurrentCleaningConfig() {
    return {rules: cleaningRules};
}

function getCurrentValidationConfig() {
    return {rules: validationRules};
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadTemplates();
});
