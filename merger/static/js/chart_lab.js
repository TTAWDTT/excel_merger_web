(function () {
    const state = {
        columns: [],
        numericColumns: [],
        datetimeColumns: [],
        dtypes: {},
        filters: [],
        lastFile: null,
        lastPreviewRows: 30
    };

    const endpoints = window.chartLabConfig || {
        inspectUrl: '/api/charts/inspect/',
        generateUrl: '/api/charts/custom/'
    };

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        const inspectForm = document.getElementById('inspectForm');
        const resetButton = document.getElementById('resetInspectBtn');
        const addFilterBtn = document.getElementById('addFilterBtn');
        const generateBtn = document.getElementById('generateChartBtn');
        const chartTypeSelect = document.getElementById('chartType');

        if (inspectForm) {
            inspectForm.addEventListener('submit', handleInspectSubmit);
        }
        if (resetButton) {
            resetButton.addEventListener('click', resetInspectState);
        }
        if (addFilterBtn) {
            addFilterBtn.addEventListener('click', addFilter);
        }
        if (generateBtn) {
            generateBtn.addEventListener('click', handleGenerateChart);
        }
        if (chartTypeSelect) {
            chartTypeSelect.addEventListener('change', () => updateChartTypeHints(chartTypeSelect.value));
        }

        updateChartTypeHints(chartTypeSelect ? chartTypeSelect.value : 'bar');
    }

    async function handleInspectSubmit(event) {
        event.preventDefault();

        const fileInput = document.getElementById('dataFile');
        const sheetNameInput = document.getElementById('sheetName');
        const previewRowsInput = document.getElementById('previewRows');

        if (!fileInput || !fileInput.files.length) {
            showError('请选择需要分析的文件');
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        const sheetName = sheetNameInput ? sheetNameInput.value.trim() : '';
        if (sheetName) {
            formData.append('sheet_name', sheetName);
        }

        const previewRows = previewRowsInput ? Number(previewRowsInput.value) || 30 : 30;
        formData.append('preview_rows', previewRows);

        state.lastFile = file;
        state.lastPreviewRows = previewRows;

        toggleGenerateButton(false);
        showLoading('正在解析数据...');

        try {
            const response = await fetch(endpoints.inspectUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
                body: formData
            });

            const payload = await response.json();
            if (!response.ok || !payload.success) {
                throw new Error(payload.error || '数据解析失败');
            }

            handleInspectSuccess(payload, sheetName);
            showSuccess('数据预览已生成');
        } catch (error) {
            console.error(error);
            showError(error.message || '生成数据预览时出现问题');
        } finally {
            hideLoading();
        }
    }

    function handleInspectSuccess(payload, sheetName) {
        state.columns = payload.columns || [];
        state.numericColumns = payload.numeric_columns || [];
        state.datetimeColumns = payload.datetime_columns || [];
        state.dtypes = payload.dtypes || {};
        state.filters = [];

        updateSummary(payload, sheetName);
        renderTable('previewContainer', payload.preview || []);
        renderStatistics('statisticsContainer', payload.statistics || []);
        populateColumnControls();
        renderFilters();
        toggleGenerateButton(state.columns.length > 0);
    }

    function resetInspectState() {
        const fileInput = document.getElementById('dataFile');
        const sheetNameInput = document.getElementById('sheetName');
        const previewRowsInput = document.getElementById('previewRows');
        const summaryBox = document.getElementById('inspectSummary');
        const previewContainer = document.getElementById('previewContainer');
        const statisticsContainer = document.getElementById('statisticsContainer');

        if (fileInput) {
            fileInput.value = '';
        }
        if (sheetNameInput) {
            sheetNameInput.value = '';
        }
        if (previewRowsInput) {
            previewRowsInput.value = 30;
        }
        if (summaryBox) {
            summaryBox.style.display = 'none';
            summaryBox.innerHTML = '';
        }
        if (previewContainer) {
            previewContainer.style.display = 'none';
            previewContainer.innerHTML = '';
        }
        if (statisticsContainer) {
            statisticsContainer.style.display = 'none';
            statisticsContainer.innerHTML = '';
        }

        state.columns = [];
        state.numericColumns = [];
        state.datetimeColumns = [];
        state.dtypes = {};
        state.filters = [];
        state.lastFile = null;
        state.lastPreviewRows = 30;

        renderFilters();
        toggleGenerateButton(false);

        const warningBox = document.getElementById('chartWarnings');
        if (warningBox) {
            warningBox.style.display = 'none';
            warningBox.innerHTML = '';
        }

        const chartOutput = document.getElementById('chartOutput');
        if (chartOutput) {
            chartOutput.innerHTML = '<p class="text-muted">上传数据并完成配置后，图表将在此处展示。</p>';
        }

        const chartStats = document.getElementById('chartStats');
        if (chartStats) {
            chartStats.style.display = 'none';
            chartStats.innerHTML = '';
        }
    }

    function updateSummary(payload, sheetName) {
        const summaryBox = document.getElementById('inspectSummary');
        if (!summaryBox) {
            return;
        }

        const items = [
            { label: '总行数', value: payload.row_count, icon: 'fa-list-ol' },
            { label: '列数量', value: payload.column_count, icon: 'fa-columns' },
            { label: '数值列', value: payload.numeric_columns ? payload.numeric_columns.length : 0, icon: 'fa-hashtag' }
        ];

        if (sheetName) {
            items.push({ label: '工作表', value: sheetName, icon: 'fa-table' });
        }

        summaryBox.innerHTML = items.map(item => (
            '<div class="summary-item">' +
            '<span><i class="fas ' + item.icon + '"></i> ' + item.label + '</span>' +
            '<strong>' + (item.value !== undefined ? item.value : '-') + '</strong>' +
            '</div>'
        )).join('');

        summaryBox.style.display = 'flex';
    }

    function renderTable(containerId, records) {
        const container = document.getElementById(containerId);
        if (!container) {
            return;
        }

        if (!records || !records.length) {
            container.innerHTML = '<p class="text-muted">暂无预览数据</p>';
            container.style.display = 'block';
            return;
        }

        const columns = Object.keys(records[0]);
        const header = columns.map(col => '<th>' + escapeHtml(col) + '</th>').join('');
        const rows = records.map(row => {
            const cells = columns.map(col => '<td>' + escapeHtml(formatValue(row[col])) + '</td>').join('');
            return '<tr>' + cells + '</tr>';
        }).join('');

        container.innerHTML = '<table class="data-table"><thead><tr>' + header + '</tr></thead><tbody>' + rows + '</tbody></table>';
        container.style.display = 'block';
    }

    function renderStatistics(containerId, statistics) {
        const container = document.getElementById(containerId);
        if (!container) {
            return;
        }

        if (!statistics || !statistics.length) {
            container.style.display = 'none';
            container.innerHTML = '';
            return;
        }

        const cards = statistics.map(stat => {
            const entries = Object.entries(stat).filter(([key]) => key !== 'column');
            const lines = entries.slice(0, 6).map(([key, value]) => (
                '<div style="display: flex; justify-content: space-between; margin: 0.35rem 0; font-size: 0.85rem;">' +
                '<span style="color: var(--text-muted);">' + escapeHtml(key) + ':</span>' +
                '<strong style="color: var(--text-color);">' + escapeHtml(formatValue(value)) + '</strong>' +
                '</div>'
            )).join('');
            return '<div class="stat-card">' +
                   '<h4><i class="fas fa-chart-line"></i> ' + escapeHtml(stat.column) + '</h4>' +
                   lines +
                   '</div>';
        }).join('');

        container.innerHTML = cards;
        container.style.display = 'grid';
    }

    function populateColumnControls() {
        const xSelect = document.getElementById('xAxis');
        const ySelect = document.getElementById('yAxis');
        const groupSelect = document.getElementById('groupBy');
        const filterSelect = document.getElementById('filterColumn');

        const columns = state.columns || [];
        const dtypes = state.dtypes || {};
        const numeric = state.numericColumns || [];
        const options = columns.map(name => ({
            value: name,
            label: name,
            dtype: (dtypes[name] || '').toLowerCase()
        }));

        populateSelect(xSelect, options, { includeBlank: true });
        populateSelect(groupSelect, options, { includeBlank: false, multiple: true });
        populateSelect(filterSelect, options, { includeBlank: true });
        populateSelect(ySelect, options, { includeBlank: false, multiple: true });

        // 预选默认列
        if (xSelect && columns.length) {
            xSelect.value = columns[0];
        }
        if (ySelect) {
            const defaults = numeric.length ? numeric.slice(0, 2) : columns.slice(0, 1);
            setMultiSelect(ySelect, defaults);
        }
    }

    function populateSelect(select, options, config = {}) {
        if (!select) {
            return;
        }
        const { includeBlank = false } = config;
        const items = Array.isArray(options) ? options : [];
        select.innerHTML = '';

        if (includeBlank && !select.multiple) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = '自动选择';
            select.appendChild(option);
        }

        items.forEach(item => {
            const value = typeof item === 'object' && item !== null ? item.value : item;
            const label = typeof item === 'object' && item !== null ? (item.label || item.value) : item;
            const dtype = typeof item === 'object' && item !== null ? item.dtype : undefined;
            const option = document.createElement('option');
            option.value = value;
            option.textContent = label;
            if (dtype) {
                option.dataset.dtype = dtype;
            }
            select.appendChild(option);
        });
    }

    function setMultiSelect(select, values) {
        if (!select) {
            return;
        }
        const targets = new Set(values || []);
        Array.from(select.options).forEach(option => {
            option.selected = targets.has(option.value);
        });
    }

    function addFilter() {
        const columnSelect = document.getElementById('filterColumn');
        const operatorSelect = document.getElementById('filterOperator');
        const valueInput = document.getElementById('filterValue');

        if (!columnSelect || !operatorSelect || !valueInput) {
            return;
        }

        const column = columnSelect.value;
        const operator = operatorSelect.value;
        const rawValue = valueInput.value.trim();

        if (!column) {
            showError('请先选择需要过滤的字段');
            return;
        }
        if (!rawValue && !['is_null', 'not_null'].includes(operator)) {
            showError('请输入过滤条件的值');
            return;
        }

        const value = parseFilterValue(column, operator, rawValue);
        state.filters.push({ id: Date.now(), column, operator, value });
        renderFilters();
        valueInput.value = '';
    }

    function parseFilterValue(column, operator, rawValue) {
        if (['in', 'not_in'].includes(operator)) {
            return rawValue.split(',').map(item => convertByDtype(column, item.trim())).filter(item => item !== null && item !== '');
        }
        return convertByDtype(column, rawValue);
    }

    function convertByDtype(column, value) {
        if (value === '') {
            return value;
        }
        const dtype = state.dtypes[column] || '';
        const normalized = dtype.toLowerCase();

        if (normalized.includes('int') || normalized.includes('float') || normalized.includes('double') || normalized.includes('decimal')) {
            const num = Number(value);
            if (!Number.isNaN(num)) {
                return num;
            }
        }
        if (normalized.includes('bool')) {
            if (value === '1' || value.toLowerCase() === 'true') {
                return true;
            }
            if (value === '0' || value.toLowerCase() === 'false') {
                return false;
            }
        }
        return value;
    }

    function renderFilters() {
        const filterList = document.getElementById('filterList');
        if (!filterList) {
            return;
        }

        if (!state.filters.length) {
            filterList.innerHTML = '<p class="text-muted" style="margin: 0.5rem 0;"><i class="fas fa-info-circle"></i> 尚未添加过滤条件</p>';
            return;
        }

        filterList.innerHTML = state.filters.map(filter => (
            '<span class="filter-badge">' +
            '<i class="fas fa-filter"></i> ' +
            escapeHtml(filter.column) + ' ' + escapeHtml(filter.operator) + ' ' + escapeHtml(formatValue(filter.value)) +
            ' <button type="button" data-id="' + filter.id + '"><i class="fas fa-times"></i></button>' +
            '</span>'
        )).join('');

        Array.from(filterList.querySelectorAll('button')).forEach(button => {
            button.addEventListener('click', () => {
                const id = Number(button.getAttribute('data-id'));
                state.filters = state.filters.filter(item => item.id !== id);
                renderFilters();
            });
        });
    }

    async function handleGenerateChart() {
        if (!state.lastFile) {
            showError('请先上传并预览数据');
            return;
        }

        const config = buildChartConfig();
        if (!config) {
            return;
        }

        toggleGenerateButton(false);
        showLoading('正在生成图表...');

        const formData = new FormData();
        formData.append('file', state.lastFile);
        formData.append('config', JSON.stringify(config));
        if (config.sheet_name) {
            formData.append('sheet_name', config.sheet_name);
        }

        try {
            const response = await fetch(endpoints.generateUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
                body: formData
            });

            const payload = await response.json();
            if (!response.ok || !payload.success) {
                throw new Error(payload.error || '图表生成失败');
            }

            renderChartResult(payload);
            renderStatistics('chartStats', payload.statistics || []);
            showWarnings(payload.warnings || []);
            showSuccess('图表已生成');
        } catch (error) {
            console.error(error);
            showError(error.message || '生成图表时出现问题');
        } finally {
            hideLoading();
            toggleGenerateButton(true);
        }
    }

    function buildChartConfig() {
        const chartType = document.getElementById('chartType').value;
        const xSelect = document.getElementById('xAxis');
        const ySelect = document.getElementById('yAxis');
        const groupSelect = document.getElementById('groupBy');
        const aggregateSelect = document.getElementById('aggregateFunc');
        const titleInput = document.getElementById('chartTitle');
        const xLabelInput = document.getElementById('xLabel');
        const yLabelInput = document.getElementById('yLabel');
        const widthInput = document.getElementById('chartWidth');
        const heightInput = document.getElementById('chartHeight');
        const binsInput = document.getElementById('bins');
        const autopctInput = document.getElementById('autopct');
        const rotationInput = document.getElementById('xRotation');
        const gridCheckbox = document.getElementById('showGrid');
        const legendCheckbox = document.getElementById('showLegend');
        const sheetNameInput = document.getElementById('sheetName');
        const previewRowsInput = document.getElementById('previewRows');

        const xField = xSelect ? (xSelect.value || null) : null;
        const yFields = ySelect ? Array.from(ySelect.selectedOptions).map(opt => opt.value).filter(Boolean) : [];
        const groupBy = groupSelect ? Array.from(groupSelect.selectedOptions).map(opt => opt.value).filter(Boolean) : [];
        const dtypeMap = state.dtypes || {};

        if (!yFields.length) {
            showError('请选择至少一个 Y 轴字段');
            return null;
        }

        if (chartType === 'scatter' && yFields.length !== 1) {
            showError('散点图需要且仅支持一个 Y 轴字段');
            return null;
        }

        if (chartType === 'pie' && yFields.length !== 1) {
            showError('饼图需要且仅支持一个数值字段');
            return null;
        }

        const config = {
            chart_type: chartType,
            x: xField,
            y: yFields,
            grid: gridCheckbox ? gridCheckbox.checked : true,
            legend: legendCheckbox ? legendCheckbox.checked : true,
            filters: state.filters.map(({ column, operator, value }) => ({ column, operator, value })),
            preview_rows: previewRowsInput ? Number(previewRowsInput.value) || state.lastPreviewRows : state.lastPreviewRows
        };

        const sheetName = sheetNameInput ? sheetNameInput.value.trim() : '';
        if (sheetName) {
            config.sheet_name = sheetName;
        }

        assignIfValue(config, 'title', titleInput ? titleInput.value.trim() : '');
        assignIfValue(config, 'x_label', xLabelInput ? xLabelInput.value.trim() : '');
        assignIfValue(config, 'y_label', yLabelInput ? yLabelInput.value.trim() : '');

        const width = widthInput ? Number(widthInput.value) : 10;
        const height = heightInput ? Number(heightInput.value) : 6;
        if (width > 0) {
            config.width = width;
        }
        if (height > 0) {
            config.height = height;
        }

        if (binsInput) {
            const bins = Number(binsInput.value);
            if (!Number.isNaN(bins) && bins > 0) {
                config.bins = bins;
            }
        }

        if (autopctInput && autopctInput.value.trim()) {
            config.autopct = autopctInput.value.trim();
        }

        if (rotationInput) {
            const rotation = Number(rotationInput.value);
            if (!Number.isNaN(rotation)) {
                config.x_rotation = rotation;
            }
        }

        const aliasRegistry = new Set();
        const allNonNumeric = yFields.every(field => !isNumericDtype(dtypeMap[field] || ''));

        if (groupBy.length) {
            const selectedAgg = aggregateSelect ? (aggregateSelect.value || 'sum') : 'sum';
            const metrics = yFields.map(field => {
                const dtype = dtypeMap[field] || '';
                let agg = selectedAgg;
                if (!isNumericDtype(dtype)) {
                    agg = agg === 'nunique' ? 'nunique' : 'count';
                }
                const alias = buildMetricAlias(field, agg, aliasRegistry);
                return { column: field, agg, alias };
            });
            config.aggregation = { group_by: groupBy, metrics };
            config.y = metrics.map(metric => metric.alias);
        } else if (allNonNumeric) {
            const pivotDimension = xField || yFields[0];
            if (!pivotDimension) {
                showError('请选择至少一个维度或数值字段');
                return null;
            }
            if (!xField) {
                config.x = pivotDimension;
            }
            const metrics = yFields.map(field => {
                const alias = buildMetricAlias(field, 'count', aliasRegistry);
                return { column: field, agg: 'count', alias };
            });
            config.aggregation = { group_by: [pivotDimension], metrics };
            config.y = metrics.map(metric => metric.alias);
        }

        return config;
    }

    function assignIfValue(target, key, value) {
        if (!value) {
            return;
        }
        target[key] = value;
    }

    function renderChartResult(payload) {
        const chartOutput = document.getElementById('chartOutput');
        if (!chartOutput) {
            return;
        }

        const chart = payload.chart || {};
        const image = chart.image;
        const metadata = chart.metadata || {};
        const dataPreview = (payload.data && payload.data.preview) || [];

        if (!image) {
            chartOutput.innerHTML = '<div style="text-align: center; color: var(--text-muted);"><i class="fas fa-chart-pie" style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.3;"></i><p>暂未获取到图表结果</p></div>';
            return;
        }

        const summaryItems = [
            { label: '图表类型', value: formatValue(metadata.chart_type), icon: 'fa-chart-bar' },
            { label: '绘制行数', value: metadata.rows_plotted, icon: 'fa-list-ol' },
            { label: 'X 轴', value: metadata.x_field || '自动', icon: 'fa-arrows-alt-h' },
            { label: 'Y 轴', value: (metadata.y_fields || []).join(', '), icon: 'fa-arrows-alt-v' }
        ];

        const summaryHtml = summaryItems.map(item => (
            '<div class="summary-item">' +
            '<span><i class="fas ' + item.icon + '"></i> ' + escapeHtml(item.label) + '</span>' +
            '<strong>' + escapeHtml(formatValue(item.value)) + '</strong>' +
            '</div>'
        )).join('');

        let previewHtml = '';
        if (dataPreview && dataPreview.length) {
            previewHtml = '<div style="margin-top:1.5rem;"><h4 style="font-size:1.1rem;margin-bottom:1rem;color:var(--primary-color);display:flex;align-items:center;gap:0.5rem;">' +
                '<i class="fas fa-table"></i> 绘图数据样例</h4>' +
                buildTableHtml(dataPreview) + '</div>';
        }

        chartOutput.innerHTML = '<img src="' + image + '" alt="自定义图表">' +
            '<div class="summary-bar" style="margin-top:1.5rem;">' + summaryHtml + '</div>' + previewHtml;
    }

    function buildTableHtml(records) {
        if (!records.length) {
            return '';
        }
        const columns = Object.keys(records[0]);
        const header = columns.map(col => '<th>' + escapeHtml(col) + '</th>').join('');
        const rows = records.map(row => {
            const cells = columns.map(col => '<td>' + escapeHtml(formatValue(row[col])) + '</td>').join('');
            return '<tr>' + cells + '</tr>';
        }).join('');
        return '<div class="table-scroll" style="max-height:240px;"><table class="data-table"><thead><tr>' + header + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
    }

    function showWarnings(warnings) {
        const warningBox = document.getElementById('chartWarnings');
        if (!warningBox) {
            return;
        }
        if (!warnings || !warnings.length) {
            warningBox.style.display = 'none';
            warningBox.innerHTML = '';
            return;
        }
        warningBox.innerHTML = '<i class="fas fa-exclamation-triangle"></i>' +
                               '<div>' + warnings.map(item => '<p style="margin: 0.25rem 0;">' + escapeHtml(item) + '</p>').join('') + '</div>';
        warningBox.style.display = 'flex';
    }

    function toggleGenerateButton(enabled) {
        const generateBtn = document.getElementById('generateChartBtn');
        if (generateBtn) {
            generateBtn.disabled = !enabled;
        }
    }

    function updateChartTypeHints(chartType) {
        const binsInput = document.getElementById('bins');
        const autopctInput = document.getElementById('autopct');

        if (binsInput) {
            binsInput.parentElement.style.display = chartType === 'hist' ? 'block' : 'none';
        }
        if (autopctInput) {
            autopctInput.parentElement.style.display = chartType === 'pie' ? 'block' : 'none';
        }
    }

    function isNumericDtype(dtype) {
        if (!dtype) {
            return false;
        }
        const normalized = dtype.toString().toLowerCase();
        return normalized.includes('int') ||
               normalized.includes('float') ||
               normalized.includes('double') ||
               normalized.includes('decimal') ||
               normalized.includes('number');
    }

    function buildMetricAlias(field, agg, registry) {
        const base = (field || 'metric') + '_' + agg;
        let alias = base;
        let counter = 2;
        while (registry.has(alias)) {
            alias = base + '_' + counter;
            counter += 1;
        }
        registry.add(alias);
        return alias;
    }

    function formatValue(value) {
        if (value === null || value === undefined) {
            return '-';
        }
        if (Array.isArray(value)) {
            return value.map(item => formatValue(item)).join(', ');
        }
        if (typeof value === 'number') {
            return Number.isInteger(value) ? value : value.toFixed(2);
        }
        return String(value);
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
})();
