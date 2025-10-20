from contextlib import nullcontext
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
from pathlib import Path
import base64
import io
import json
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import seaborn as sns
except ImportError:  # pragma: no cover - seaborn is optional
    sns = None

from .models import (MergeTask, UploadedFile, ColumnRule, CellOperation,
                     TaskTemplate, FilePreview, DataCleaningRule, 
                     DataValidationRule, ValidationResult)
from .core import excel_processor
from .core.data_processor import DataProcessor
from .core.data_analyzer import (DataPreviewGenerator, DataCleaner, 
                                DataValidator, ChartGenerator)


def index(request):
    """首页"""
    tasks = MergeTask.objects.all()[:10]
    return render(request, 'merger/index.html', {'tasks': tasks})


def task_list(request):
    """任务列表页面"""
    tasks = MergeTask.objects.all()
    return render(request, 'merger/task_list.html', {'tasks': tasks})


def task_create(request):
    """创建任务页面"""
    if request.method == 'POST':
        return redirect('task_list')
    return render(request, 'merger/task_create.html')


def task_detail(request, task_id):
    """任务详情页面"""
    task = get_object_or_404(MergeTask, pk=task_id)
    return render(request, 'merger/task_detail.html', {'task': task})


def chart_lab(request):
    """统计图表实验室页面"""
    return render(request, 'merger/chart_lab.html')


def _normalize_value_for_json(value):
    """将 pandas/numpy 类型值转换为可序列化格式"""
    if value is None:
        return None
    if isinstance(value, (np.generic,)):
        return value.item()
    if isinstance(value, (pd.Timestamp, pd.Timedelta, pd.Period)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_normalize_value_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_value_for_json(val) for key, val in value.items()}
    if pd.isna(value):  # pandas 会将 NaN 视为缺失值
        return None
    return value


def _is_empty_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ''
    return pd.isna(value)


def _looks_like_default_header(value):
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    lowered = text.lower()
    if lowered.startswith('unnamed'):
        return True
    if re.fullmatch(r'列\d+', text):
        return True
    if re.fullmatch(r'\d+', text):
        return True
    return False


def _sanitize_column_names(raw_columns):
    sanitized = []
    seen = {}
    for idx, column in enumerate(raw_columns):
        name = str(column).strip() if column is not None else ''
        if not name or _looks_like_default_header(name):
            name = f'列{idx + 1}'
        if name in seen:
            seen[name] += 1
            name = f'{name}_{seen[name]}'
        else:
            seen[name] = 1
        sanitized.append(name)
    return sanitized


def _trim_leading_empty_rows(df):
    if df.empty:
        return df
    first_valid_idx = None
    for idx in range(len(df)):
        row = df.iloc[idx]
        if row.notna().any():
            first_valid_idx = idx
            break
    if first_valid_idx in (None, 0):
        return df
    return df.iloc[first_valid_idx:].reset_index(drop=True)


def _value_is_numeric_like(value):
    if value is None:
        return False
    if isinstance(value, (int, float, np.number)) and not pd.isna(value):
        return True
    if isinstance(value, str):
        candidate = value.strip().replace(',', '')
        if not candidate:
            return False
        try:
            float(candidate)
            return True
        except ValueError:
            return False
    return False


def _should_infer_header(columns):
    if not columns:
        return False
    normalized = [str(col).strip().lower() if col is not None else '' for col in columns]
    default_like = sum(1 for name in normalized if not name or name.startswith('unnamed') or re.fullmatch(r'列\d+', name))
    duplicate = len(set(normalized)) != len(normalized)
    return (default_like / max(len(columns), 1) >= 0.5) or duplicate


def _infer_header_from_frame(df_raw):
    df_raw = _trim_leading_empty_rows(df_raw)
    if df_raw.empty:
        return None, df_raw

    candidate_row = None
    best_score = -1
    max_rows = min(len(df_raw), 12)

    for idx in range(max_rows):
        row = df_raw.iloc[idx]
        values = []
        for value in row.tolist():
            if _is_empty_value(value):
                values.append('')
            else:
                values.append(str(value).strip())

        non_empty = [val for val in values if val]
        if not non_empty:
            continue

        unique_ratio = len(set(val.lower() for val in non_empty)) / len(non_empty)
        string_ratio = sum(1 for val in non_empty if not _value_is_numeric_like(val)) / len(non_empty)
        score = len(non_empty) + unique_ratio * 2 + string_ratio

        if score > best_score:
            best_score = score
            candidate_row = idx

    if candidate_row is None:
        return None, df_raw

    header_values = df_raw.iloc[candidate_row].tolist()
    meaningful_count = sum(1 for val in header_values if not _is_empty_value(val))
    if meaningful_count < max(2, int(len(header_values) * 0.4)):
        return None, df_raw

    new_header = _sanitize_column_names(header_values)
    trimmed_df = df_raw.iloc[candidate_row + 1:].reset_index(drop=True)
    trimmed_df.columns = new_header
    return new_header, trimmed_df


def _coerce_dataframe_types(df):
    if df.empty:
        return df

    object_columns = df.select_dtypes(include=['object', 'string']).columns
    for column in object_columns:
        series = df[column]
        sample = series.dropna().astype(str).str.strip().replace({'': np.nan}).dropna().head(50)
        if sample.empty:
            continue

        numeric_sample = pd.to_numeric(sample.str.replace(',', '', regex=False), errors='coerce')
        if numeric_sample.notna().mean() >= 0.8:
            df[column] = pd.to_numeric(series.astype(str).str.replace(',', '', regex=False).str.strip(), errors='coerce')
            continue

        datetime_sample = pd.to_datetime(sample, errors='coerce', infer_datetime_format=True)
        if datetime_sample.notna().mean() >= 0.8:
            df[column] = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)

    return df


def _read_dataframe_from_upload(uploaded_file, sheet_name=None, max_rows=50000):
    """将上传文件解析为 DataFrame，支持 Excel/CSV/JSON"""
    if not uploaded_file:
        raise ValueError('请上传需要分析的数据文件')

    file_name = getattr(uploaded_file, 'name', '数据文件')
    file_ext = Path(file_name).suffix.lower()

    # 复制文件内容，避免改变外部文件指针
    payload = uploaded_file.read()
    uploaded_file.seek(0)
    stream = io.BytesIO(payload)

    try:
        if file_ext in {'.xlsx', '.xls'}:
            df = pd.read_excel(stream, sheet_name=sheet_name or 0, header=0)
        elif file_ext == '.csv':
            df = pd.read_csv(stream, header=0)
        elif file_ext == '.json':
            df = pd.read_json(stream)
        else:
            raise ValueError('仅支持 Excel (.xlsx/.xls)、CSV 或 JSON 文件')
    except ValueError as exc:
        raise exc
    except Exception as exc:
        raise ValueError(f'解析文件失败: {exc}') from exc

    df = _trim_leading_empty_rows(df)

    inferred_header = None
    if file_ext != '.json' and _should_infer_header(df.columns):
        raw_stream = io.BytesIO(payload)
        try:
            if file_ext in {'.xlsx', '.xls'}:
                raw_df = pd.read_excel(raw_stream, sheet_name=sheet_name or 0, header=None)
            elif file_ext == '.csv':
                raw_df = pd.read_csv(raw_stream, header=None)
            else:
                raw_df = df.copy()
        except Exception:
            raw_df = df.copy()

        inferred_header, candidate_df = _infer_header_from_frame(raw_df)
        if inferred_header:
            df = candidate_df

    if inferred_header:
        df.columns = inferred_header
    else:
        df.columns = _sanitize_column_names(df.columns)

    # 删除完全空白的列
    df = df.loc[:, [column for column in df.columns if column.strip()]]

    df = _coerce_dataframe_types(df)

    if max_rows and len(df) > max_rows:
        df = df.head(max_rows)

    return df


def _dataframe_preview(df, limit=50):
    """返回数据预览，确保可以序列化"""
    preview_df = df.head(limit)
    records = []
    for row in preview_df.to_dict(orient='records'):
        records.append({key: _normalize_value_for_json(value) for key, value in row.items()})
    return records


def _apply_dataframe_filters(df, filters):
    """按照用户配置过滤数据"""
    if not filters:
        return df

    filtered_df = df.copy()

    for rule in filters:
        column = rule.get('column')
        operator = str(rule.get('operator', '==')).lower()
        value = rule.get('value')

        if column not in filtered_df.columns:
            continue

        try:
            if operator == '==':
                filtered_df = filtered_df[filtered_df[column] == value]
            elif operator == '!=':
                filtered_df = filtered_df[filtered_df[column] != value]
            elif operator == '>':
                filtered_df = filtered_df[filtered_df[column] > value]
            elif operator == '>=':
                filtered_df = filtered_df[filtered_df[column] >= value]
            elif operator == '<':
                filtered_df = filtered_df[filtered_df[column] < value]
            elif operator == '<=':
                filtered_df = filtered_df[filtered_df[column] <= value]
            elif operator == 'contains':
                filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(str(value), na=False)]
            elif operator == 'not_contains':
                mask = filtered_df[column].astype(str).str.contains(str(value), na=False)
                filtered_df = filtered_df[~mask]
            elif operator == 'in':
                if not isinstance(value, (list, tuple, set)):
                    value = [value]
                filtered_df = filtered_df[filtered_df[column].isin(value)]
            elif operator == 'not_in':
                if not isinstance(value, (list, tuple, set)):
                    value = [value]
                filtered_df = filtered_df[~filtered_df[column].isin(value)]
        except Exception:
            # 忽略单个规则的错误，继续处理其他规则
            continue

    return filtered_df


def _apply_dataframe_aggregation(df, aggregation_config):
    """应用聚合规则，返回聚合后的数据和指标别名"""
    if not aggregation_config:
        return df, []

    group_by = aggregation_config.get('group_by') or []
    metrics = aggregation_config.get('metrics') or []

    if not group_by or not metrics:
        return df, []

    missing_columns = [column for column in group_by if column not in df.columns]
    if missing_columns:
        raise ValueError(f"分组字段不存在: {', '.join(missing_columns)}")

    named_metrics = {}
    supported_aggs = {
        'sum': 'sum',
        'avg': 'mean',
        'mean': 'mean',
        'median': 'median',
        'max': 'max',
        'min': 'min',
        'count': 'count',
        'nunique': 'nunique',
        'std': 'std',
        'var': 'var'
    }

    for metric in metrics:
        source_column = metric.get('column')
        agg_func = metric.get('agg') or metric.get('function') or 'sum'
        alias = metric.get('alias') or f"{source_column}_{agg_func}"

        if source_column not in df.columns:
            continue

        agg_func = supported_aggs.get(agg_func.lower(), agg_func)
        column_dtype = df[source_column].dtype if source_column in df.columns else None
        if column_dtype is not None and not pd.api.types.is_numeric_dtype(column_dtype):
            if agg_func not in {'count', 'nunique'}:
                agg_func = 'count'

        base_alias = alias.strip() or f"{source_column}_{agg_func}"
        alias_candidate = base_alias
        counter = 2
        while alias_candidate in named_metrics:
            alias_candidate = f"{base_alias}_{counter}"
            counter += 1

        named_metrics[alias_candidate] = pd.NamedAgg(column=source_column, aggfunc=agg_func)

    if not named_metrics:
        return df, []

    aggregated = df.groupby(group_by, dropna=False).agg(**named_metrics).reset_index()
    return aggregated, list(named_metrics.keys())


def _prepare_chart_dataframe(df, config):
    """根据配置生成绘图数据"""
    filters = config.get('filters') or []
    aggregation = config.get('aggregation') or {
        'group_by': config.get('group_by'),
        'metrics': config.get('metrics')
    }

    filtered_df = _apply_dataframe_filters(df, filters)
    aggregated_df, metric_aliases = _apply_dataframe_aggregation(filtered_df, aggregation)
    return aggregated_df, metric_aliases, len(filters)


def _determine_chart_fields(chart_df, config, metric_aliases):
    """解析 X/Y 轴字段"""
    x_field = config.get('x') or config.get('dimension')
    if isinstance(x_field, list):
        x_field = x_field[0] if x_field else None

    if not x_field:
        group_by = (config.get('aggregation') or {}).get('group_by') or config.get('group_by') or []
        if group_by:
            x_field = group_by[0]
        elif len(chart_df.columns) > 0:
            x_field = chart_df.columns[0]

    if x_field and x_field not in chart_df.columns:
        raise ValueError(f'X 轴字段 "{x_field}" 不存在')

    y_fields = config.get('y') or config.get('y_fields') or config.get('values')
    if isinstance(y_fields, str):
        y_fields = [y_fields]

    if not y_fields:
        if metric_aliases:
            y_fields = metric_aliases
        else:
            numeric_columns = [col for col in chart_df.columns if col != x_field and pd.api.types.is_numeric_dtype(chart_df[col])]
            y_fields = numeric_columns[:2]

    if not y_fields:
        raise ValueError('缺少可用于绘制的数值列')

    missing_y = [col for col in y_fields if col not in chart_df.columns]
    if missing_y and metric_aliases:
        fallback = [alias for alias in metric_aliases if alias in chart_df.columns]
        if fallback:
            y_fields = fallback
            missing_y = [col for col in y_fields if col not in chart_df.columns]
    if missing_y:
        raise ValueError(f"以下指标列不存在: {', '.join(missing_y)}")

    return x_field, y_fields


def _render_chart_image(chart_df, config, x_field, y_fields):
    """渲染图表并返回 base64 字符串及图表元数据"""
    chart_type = (config.get('chart_type') or 'bar').lower()
    width = float(config.get('width') or config.get('figure', {}).get('width') or 10)
    height = float(config.get('height') or config.get('figure', {}).get('height') or 6)

    style_config = config.get('style') or {}
    style_name = style_config.get('name')
    context_manager = nullcontext()

    if style_name:
        try:
            context_manager = plt.style.context(style_name)
        except OSError:
            context_manager = plt.rc_context()
    else:
        context_manager = plt.rc_context()

    with context_manager:
        fig, ax = plt.subplots(figsize=(width, height))

        if chart_type in {'line', 'bar', 'barh', 'area'}:
            chart_df.plot(kind=chart_type if chart_type != 'barh' else 'barh', x=x_field, y=y_fields, ax=ax)
        elif chart_type == 'scatter':
            if len(y_fields) != 1:
                raise ValueError('散点图需要单个 Y 轴字段')
            chart_df.plot.scatter(x=x_field, y=y_fields[0], ax=ax, color=style_config.get('color'))
        elif chart_type == 'hist':
            chart_df[y_fields].plot(kind='hist', bins=int(config.get('bins') or 20), alpha=0.7, ax=ax)
        elif chart_type == 'box':
            chart_df[y_fields].plot(kind='box', ax=ax)
        elif chart_type == 'pie':
            if len(y_fields) != 1:
                raise ValueError('饼图需要单个指标字段')
            pie_series = chart_df.set_index(x_field)[y_fields[0]] if x_field else chart_df[y_fields[0]]
            pie_series.plot(kind='pie', ax=ax, autopct=config.get('autopct', '%1.1f%%'))
            ax.set_ylabel('')
        else:
            raise ValueError(f'暂不支持的图表类型: {chart_type}')

        title = config.get('title') or '自定义图表'
        ax.set_title(title)

        if chart_type != 'pie':
            if x_field:
                ax.set_xlabel(config.get('x_label') or x_field)
            ax.set_ylabel(config.get('y_label') or ', '.join(y_fields))

        if config.get('grid', True):
            ax.grid(True, axis='both', linestyle='--', alpha=0.2)
        else:
            ax.grid(False)

        if not config.get('legend', True) and ax.get_legend():
            ax.get_legend().remove()

        if config.get('x_rotation') is not None and chart_type != 'pie':
            plt.setp(ax.get_xticklabels(), rotation=float(config.get('x_rotation')))

        plt.tight_layout()

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('ascii')

    plt.close(fig)

    metadata = {
        'chart_type': chart_type,
        'x_field': x_field,
        'y_fields': y_fields,
        'rows_plotted': int(chart_df.shape[0]),
        'columns_plotted': chart_df.columns.tolist()
    }

    return image_base64, metadata

@require_http_methods(["POST"])
def api_custom_chart_inspect(request):
    """API: 检查上传文件并返回可视化所需的列信息和数据概览"""
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            raise ValueError('请上传需要分析的数据文件')

        sheet_name = request.POST.get('sheet_name') or request.POST.get('sheet')
        preview_rows = int(request.POST.get('preview_rows') or 30)

        df = _read_dataframe_from_upload(uploaded_file, sheet_name=sheet_name)

        numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        datetime_columns = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]

        statistics = []
        if numeric_columns:
            stats_df = df[numeric_columns].describe().transpose()
            for column, stats_row in stats_df.to_dict(orient='index').items():
                record = {'column': column}
                record.update({key: _normalize_value_for_json(value) for key, value in stats_row.items()})
                statistics.append(record)

        response = {
            'success': True,
            'columns': df.columns.tolist(),
            'dtypes': {column: str(dtype) for column, dtype in df.dtypes.items()},
            'row_count': int(df.shape[0]),
            'column_count': int(df.shape[1]),
            'numeric_columns': numeric_columns,
            'datetime_columns': datetime_columns,
            'preview': _dataframe_preview(df, limit=preview_rows),
            'statistics': statistics
        }

        return JsonResponse(response)
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': f'数据预览失败: {exc}'}, status=500)


@require_http_methods(["POST"])
def api_generate_custom_chart(request):
    """API: 根据用户配置生成自定义图表"""
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            raise ValueError('请上传需要分析的数据文件')

        config_payload = request.POST.get('config')
        if not config_payload and request.body:
            try:
                config_payload = request.body.decode('utf-8')
            except UnicodeDecodeError:
                config_payload = None

        if not config_payload:
            raise ValueError('缺少图表配置参数')

        try:
            config = json.loads(config_payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f'图表配置解析失败: {exc}') from exc

        sheet_name = config.get('sheet_name') or request.POST.get('sheet_name') or request.POST.get('sheet')
        max_rows = config.get('max_rows')
        if isinstance(max_rows, str) and max_rows.isdigit():
            max_rows = int(max_rows)

        df = _read_dataframe_from_upload(uploaded_file, sheet_name=sheet_name, max_rows=max_rows)

        chart_df, metric_aliases, filter_count = _prepare_chart_dataframe(df, config)

        if chart_df.empty:
            raise ValueError('过滤或聚合后数据为空，无法生成图表')

        x_field, y_fields = _determine_chart_fields(chart_df, config, metric_aliases)

        required_columns = [col for col in ([x_field] if x_field else []) + y_fields if col]
        plot_df = chart_df.dropna(subset=required_columns) if required_columns else chart_df

        if plot_df.empty:
            raise ValueError('缺少有效数据点用于绘制图表')

        image_base64, chart_meta = _render_chart_image(plot_df, config, x_field, y_fields)

        preview_limit = int(config.get('preview_rows') or 30)
        preview_columns = []
        if x_field:
            preview_columns.append(x_field)
        preview_columns.extend([column for column in y_fields if column not in preview_columns])
        preview_df = plot_df[preview_columns] if preview_columns else plot_df

        statistics = []
        numeric_for_stats = [col for col in y_fields if pd.api.types.is_numeric_dtype(plot_df[col])]
        if numeric_for_stats:
            stats_df = plot_df[numeric_for_stats].describe().transpose()
            for column, stats_row in stats_df.to_dict(orient='index').items():
                record = {'column': column}
                record.update({key: _normalize_value_for_json(value) for key, value in stats_row.items()})
                statistics.append(record)

        response = {
            'success': True,
            'chart': {
                'image': f'data:image/png;base64,{image_base64}',
                'metadata': chart_meta
            },
            'data': {
                'columns': plot_df.columns.tolist(),
                'row_count': int(plot_df.shape[0]),
                'source_row_count': int(df.shape[0]),
                'preview': _dataframe_preview(preview_df, limit=preview_limit)
            },
            'statistics': statistics,
            'applied_filters': filter_count
        }

        dropped_rows = int(chart_df.shape[0] - plot_df.shape[0])
        if dropped_rows > 0:
            response['warnings'] = [f'有 {dropped_rows} 行数据因缺失值被忽略']

        return JsonResponse(response)
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': f'图表生成失败: {exc}'}, status=500)


@require_http_methods(["POST"])
def api_create_task(request):
    """API: 创建任务"""
    try:
        data = json.loads(request.body)
        task = MergeTask.objects.create(
            name=data.get('name', '未命名任务'),
            output_format=data.get('output_format', 'xlsx'),
            filter_mode=data.get('filter_mode', 'none'),
            filter_columns=data.get('filter_columns', []),
        )
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'message': '任务创建成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_upload_file(request, task_id):
    """API: 上传文件"""
    try:
        task = get_object_or_404(MergeTask, pk=task_id)
        
        files = request.FILES.getlist('files')
        uploaded_files = []
        
        for file in files:
            # 检查文件格式
            file_ext = file.name.split('.')[-1].lower()
            if file_ext not in ['xlsx', 'xls', 'csv', 'json']:
                continue
            
            uploaded_file = UploadedFile.objects.create(
                task=task,
                file=file,
                original_filename=file.name
            )
            uploaded_files.append({
                'id': uploaded_file.id,
                'name': uploaded_file.original_filename
            })
        
        return JsonResponse({
            'success': True,
            'files': uploaded_files,
            'message': f'成功上传 {len(uploaded_files)} 个文件'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_add_column_rule(request, task_id):
    """API: 添加列规则"""
    try:
        data = json.loads(request.body)
        task = get_object_or_404(MergeTask, pk=task_id)
        
        # 删除旧规则(如果存在)
        ColumnRule.objects.filter(task=task).delete()
        
        rule = ColumnRule.objects.create(
            task=task,
            name=data.get('name', '列规则'),
            source_column=data['source_column'],
            new_column=data['new_column'],
            extraction_start=data.get('extraction_start'),
            extraction_end=data.get('extraction_end'),
            extraction_one_indexed=data.get('extraction_one_indexed', True),
            mappings=data.get('mappings', [])
        )
        
        return JsonResponse({
            'success': True,
            'rule_id': rule.id,
            'message': '列规则添加成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_add_cell_operations(request, task_id):
    """API: 添加单元格操作"""
    try:
        data = json.loads(request.body)
        task = get_object_or_404(MergeTask, pk=task_id)
        
        operations = data.get('operations', [])
        created_ops = []
        
        for idx, op_data in enumerate(operations):
            operation = CellOperation.objects.create(
                task=task,
                column=op_data['column'],
                action=op_data['action'],
                value=op_data.get('value'),
                old_value=op_data.get('old_value'),
                new_value=op_data.get('new_value'),
                position=op_data.get('position'),
                length=op_data.get('length'),
                order=idx
            )
            created_ops.append({
                'id': operation.id,
                'column': operation.column,
                'action': operation.action
            })
        
        return JsonResponse({
            'success': True,
            'operations': created_ops,
            'message': f'成功添加 {len(created_ops)} 个操作'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_process_task(request, task_id):
    """API: 处理任务 - 使用通用数据处理器"""
    try:
        task = get_object_or_404(MergeTask, pk=task_id)
        
        # 更新任务状态
        task.status = 'processing'
        task.save()
        
        try:
            # 获取所有上传的文件路径
            file_paths = [f.file.path for f in task.files.all()]
            
            if not file_paths:
                raise Exception('没有可处理的文件')
            
            # 使用通用数据处理器合并文件
            combined_header, merged_rows, metadata = DataProcessor.merge_files(
                file_paths, 
                output_format=task.output_format
            )
            
            # 1. 应用数据清洗规则
            cleaning_rules = [{
                'action': rule.action,
                'columns': rule.columns,
                'parameters': rule.parameters,
                'order': rule.order
            } for rule in task.cleaning_rules.all()]
            
            if cleaning_rules:
                combined_header, merged_rows = DataCleaner.apply_cleaning_rules(
                    combined_header, 
                    merged_rows, 
                    cleaning_rules
                )
            
            # 2. 应用数据验证规则（如果有）
            validation_rules = [{
                'column': rule.column,
                'rule_type': rule.rule_type,
                'parameters': rule.parameters,
                'error_message': rule.error_message
            } for rule in task.validation_rules.all()]
            
            if validation_rules:
                validation_result = DataValidator.validate_data(
                    combined_header, 
                    merged_rows, 
                    validation_rules
                )
                
                # 保存验证结果
                ValidationResult.objects.update_or_create(
                    task=task,
                    defaults={
                        'is_valid': validation_result['is_valid'],
                        'errors': validation_result['errors'],
                        'warnings': validation_result['warnings'],
                        'statistics': validation_result['statistics']
                    }
                )
                
                # 如果验证失败，根据配置决定是否继续
                if not validation_result['is_valid']:
                    # 这里可以选择抛出异常或继续处理
                    # raise Exception(f"数据验证失败: {len(validation_result['errors'])} 个错误")
                    pass
            
            # 3. 应用列规则
            if hasattr(task, 'column_rule'):
                rule_dict = task.column_rule.to_dict()
                DataProcessor.create_derived_column(merged_rows, combined_header, rule_dict)
            
            # 4. 应用单元格操作
            operations = [op.to_dict() for op in task.cell_operations.all()]
            if operations:
                DataProcessor.apply_cell_operations(merged_rows, combined_header, operations)
            
            # 5. 应用列过滤
            if task.filter_mode != 'none' and task.filter_columns:
                combined_header, merged_rows = DataProcessor.filter_columns(
                    combined_header, 
                    merged_rows, 
                    task.filter_mode, 
                    task.filter_columns
                )
            
            # 生成输出文件
            output_filename = f"merged_{task.id}.{task.output_format}"
            output_path = Path(settings.MEDIA_ROOT) / 'results' / output_filename
            
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            DataProcessor.write_file(
                combined_header,
                merged_rows,
                output_path,
                metadata,
                task.output_format
            )
            
            # 保存结果文件
            with open(output_path, 'rb') as f:
                task.result_file.save(output_filename, ContentFile(f.read()))
            
            task.status = 'completed'
            task.save()
            
            return JsonResponse({
                'success': True,
                'message': '任务处理完成',
                'download_url': task.result_file.url,
                'validation': validation_result if validation_rules else None
            })
            
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            raise
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def api_download_result(request, task_id):
    """API: 下载结果文件"""
    task = get_object_or_404(MergeTask, pk=task_id)
    
    if not task.result_file:
        return HttpResponse('结果文件不存在', status=404)
    
    response = FileResponse(task.result_file.open('rb'))
    response['Content-Disposition'] = f'attachment; filename="{task.result_file.name}"'
    return response


@require_http_methods(["POST"])
def api_delete_file(request, file_id):
    """API: 删除上传的文件"""
    try:
        uploaded_file = get_object_or_404(UploadedFile, pk=file_id)
        task = uploaded_file.task
        
        # 删除文件
        if uploaded_file.file:
            uploaded_file.file.delete()
        
        uploaded_file.delete()
        
        return JsonResponse({
            'success': True,
            'message': '文件删除成功',
            'remaining_files': task.files.count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def api_delete_task(request, task_id):
    """API: 删除任务"""
    try:
        task = get_object_or_404(MergeTask, pk=task_id)
        
        # 删除关联文件
        for uploaded_file in task.files.all():
            if uploaded_file.file:
                uploaded_file.file.delete()
        
        if task.result_file:
            task.result_file.delete()
        
        task.delete()
        
        return JsonResponse({
            'success': True,
            'message': '任务删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def api_get_task_status(request, task_id):
    """API: 获取任务状态"""
    task = get_object_or_404(MergeTask, pk=task_id)
    
    # 获取文件列表
    files = [{
        'id': f.id,
        'name': f.original_filename
    } for f in task.files.all()]
    
    # 获取列规则
    column_rule = None
    if hasattr(task, 'column_rule'):
        rule = task.column_rule
        column_rule = {
            'source_column': rule.source_column,
            'new_column': rule.new_column,
            'extraction_start': rule.extraction_start,
            'extraction_end': rule.extraction_end,
            'extraction_one_indexed': rule.extraction_one_indexed,
            'mappings': rule.mappings
        }
    
    # 获取单元格操作
    operations = [{
        'column': op.column,
        'action': op.action,
        'value': op.value,
        'old_value': op.old_value,
        'new_value': op.new_value,
        'position': op.position,
        'length': op.length
    } for op in task.cell_operations.all()]
    
    return JsonResponse({
        'success': True,
        'task': {
            'id': task.id,
            'name': task.name,
            'status': task.status,
            'output_format': task.output_format,
            'filter_mode': task.filter_mode,
            'filter_columns': task.filter_columns,
            'files': files,
            'column_rule': column_rule,
            'operations': operations,
            'result_url': task.result_file.url if task.result_file else None,
            'error_message': task.error_message,
            'created_at': task.created_at.isoformat(),
        }
    })


@require_http_methods(["DELETE", "POST"])
def api_delete_file(request, file_id):
    """API: 删除上传的文件"""
    try:
        uploaded_file = get_object_or_404(UploadedFile, pk=file_id)
        
        # 删除物理文件
        if uploaded_file.file:
            uploaded_file.file.delete()
        
        # 删除数据库记录
        uploaded_file.delete()
        
        return JsonResponse({
            'success': True,
            'message': '文件删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ==================== 新增功能 API ====================

@require_http_methods(["GET"])
def api_preview_file(request, file_id):
    """API: 预览上传的文件"""
    try:
        uploaded_file = get_object_or_404(UploadedFile, pk=file_id)
        file_path = uploaded_file.file.path
        file_ext = Path(file_path).suffix.lower()
        
        # 检查文件类型是否支持预览
        supported_formats = ['.xlsx', '.xls', '.csv']
        if file_ext not in supported_formats:
            return JsonResponse({
                'success': False,
                'error': f'暂不支持 {file_ext} 格式的文件预览。支持的格式：Excel (.xlsx, .xls) 和 CSV (.csv)',
                'supported_formats': supported_formats
            }, status=400)
        
        # 检查是否已有预览缓存
        if hasattr(uploaded_file, 'preview'):
            preview = uploaded_file.preview
            return JsonResponse({
                'success': True,
                'preview': {
                    'headers': preview.headers,
                    'sample_rows': preview.sample_rows,
                    'total_rows': preview.total_rows,
                    'total_columns': preview.total_columns,
                    'file_size': preview.file_size,
                    'column_types': preview.column_types,
                    'null_counts': preview.null_counts
                }
            })
        
        # 读取文件数据
        headers, rows, metadata = DataProcessor.read_file(file_path)
        
        # 生成预览数据
        preview_data = DataPreviewGenerator.generate_preview(headers, rows, max_rows=100)
        
        # 保存预览到数据库
        file_preview = FilePreview.objects.create(
            uploaded_file=uploaded_file,
            headers=preview_data['headers'],
            sample_rows=preview_data['sample_rows'],
            total_rows=preview_data['total_rows'],
            total_columns=preview_data['total_columns'],
            file_size=os.path.getsize(file_path),
            column_types=preview_data['column_types'],
            null_counts=preview_data['null_counts']
        )
        
        return JsonResponse({
            'success': True,
            'preview': {
                'headers': file_preview.headers,
                'sample_rows': file_preview.sample_rows,
                'total_rows': file_preview.total_rows,
                'total_columns': file_preview.total_columns,
                'file_size': file_preview.file_size,
                'column_types': file_preview.column_types,
                'null_counts': file_preview.null_counts,
                'statistics': preview_data.get('statistics', {})
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_save_template(request):
    """API: 保存任务模板"""
    try:
        data = json.loads(request.body)
        
        template = TaskTemplate.objects.create(
            name=data.get('name', '未命名模板'),
            description=data.get('description', ''),
            output_format=data.get('output_format', 'xlsx'),
            filter_mode=data.get('filter_mode', 'none'),
            filter_columns=data.get('filter_columns', []),
            column_rule_config=data.get('column_rule_config'),
            cell_operations_config=data.get('cell_operations_config', []),
            cleaning_config=data.get('cleaning_config', {}),
            validation_config=data.get('validation_config', {})
        )
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'message': '模板保存成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["GET"])
def api_list_templates(request):
    """API: 获取模板列表"""
    try:
        templates = TaskTemplate.objects.all()
        
        template_list = [{
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'output_format': t.output_format,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat()
        } for t in templates]
        
        return JsonResponse({
            'success': True,
            'templates': template_list
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["GET"])
def api_get_template(request, template_id):
    """API: 获取模板详情"""
    try:
        template = get_object_or_404(TaskTemplate, pk=template_id)
        
        return JsonResponse({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'output_format': template.output_format,
                'filter_mode': template.filter_mode,
                'filter_columns': template.filter_columns,
                'column_rule_config': template.column_rule_config,
                'cell_operations_config': template.cell_operations_config,
                'cleaning_config': template.cleaning_config,
                'validation_config': template.validation_config
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_apply_template(request, task_id, template_id):
    """API: 应用模板到任务"""
    try:
        task = get_object_or_404(MergeTask, pk=task_id)
        template = get_object_or_404(TaskTemplate, pk=template_id)
        
        # 应用模板
        template.apply_to_task(task)
        
        return JsonResponse({
            'success': True,
            'message': '模板应用成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["DELETE", "POST"])
def api_delete_template(request, template_id):
    """API: 删除模板"""
    try:
        template = get_object_or_404(TaskTemplate, pk=template_id)
        template.delete()
        
        return JsonResponse({
            'success': True,
            'message': '模板删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_add_cleaning_rules(request, task_id):
    """API: 添加数据清洗规则"""
    try:
        data = json.loads(request.body)
        task = get_object_or_404(MergeTask, pk=task_id)
        
        rules = data.get('rules', [])
        created_rules = []
        
        for idx, rule_data in enumerate(rules):
            rule = DataCleaningRule.objects.create(
                task=task,
                action=rule_data['action'],
                columns=rule_data.get('columns', []),
                parameters=rule_data.get('parameters', {}),
                order=idx
            )
            created_rules.append({
                'id': rule.id,
                'action': rule.action,
                'columns': rule.columns
            })
        
        return JsonResponse({
            'success': True,
            'rules': created_rules,
            'message': f'成功添加 {len(created_rules)} 个清洗规则'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_add_validation_rules(request, task_id):
    """API: 添加数据验证规则"""
    try:
        data = json.loads(request.body)
        task = get_object_or_404(MergeTask, pk=task_id)
        
        rules = data.get('rules', [])
        created_rules = []
        
        for rule_data in rules:
            rule = DataValidationRule.objects.create(
                task=task,
                column=rule_data['column'],
                rule_type=rule_data['rule_type'],
                parameters=rule_data.get('parameters', {}),
                error_message=rule_data.get('error_message', '')
            )
            created_rules.append({
                'id': rule.id,
                'column': rule.column,
                'rule_type': rule.rule_type
            })
        
        return JsonResponse({
            'success': True,
            'rules': created_rules,
            'message': f'成功添加 {len(created_rules)} 个验证规则'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["POST"])
def api_validate_task_data(request, task_id):
    """API: 验证任务数据"""
    try:
        task = get_object_or_404(MergeTask, pk=task_id)
        
        # 获取所有上传的文件
        file_paths = [f.file.path for f in task.files.all()]
        
        if not file_paths:
            raise Exception('没有可验证的文件')
        
        # 合并文件数据
        combined_header, merged_rows, metadata = DataProcessor.merge_files(
            file_paths, 
            output_format=task.output_format
        )
        
        # 获取验证规则
        validation_rules = [{
            'column': rule.column,
            'rule_type': rule.rule_type,
            'parameters': rule.parameters,
            'error_message': rule.error_message
        } for rule in task.validation_rules.all()]
        
        # 执行验证
        validation_result = DataValidator.validate_data(
            combined_header, 
            merged_rows, 
            validation_rules
        )
        
        # 保存验证结果
        ValidationResult.objects.update_or_create(
            task=task,
            defaults={
                'is_valid': validation_result['is_valid'],
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'statistics': validation_result['statistics']
            }
        )
        
        return JsonResponse({
            'success': True,
            'validation': validation_result
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["GET"])
def api_generate_charts(request, task_id):
    """API: 生成统计图表"""
    try:
        task = get_object_or_404(MergeTask, pk=task_id)
        
        # 获取所有上传的文件
        files = task.files.all()
        if not files:
            raise Exception('没有可分析的文件')
        
        # 检查文件类型是否支持图表生成
        file_paths = []
        unsupported_files = []
        supported_formats = ['.xlsx', '.xls', '.csv']
        
        for f in files:
            file_ext = Path(f.file.path).suffix.lower()
            if file_ext in supported_formats:
                file_paths.append(f.file.path)
            else:
                unsupported_files.append(f.name)
        
        if not file_paths:
            return JsonResponse({
                'success': False,
                'error': f'所有文件都不支持图表生成。支持的格式：Excel (.xlsx, .xls) 和 CSV (.csv)',
                'unsupported_files': unsupported_files,
                'supported_formats': supported_formats
            }, status=400)
        
        # 如果有不支持的文件，给出警告但继续处理
        warning_message = None
        if unsupported_files:
            warning_message = f'以下文件不支持图表分析，已跳过：{", ".join(unsupported_files)}'
        
        # 合并文件数据
        combined_header, merged_rows, metadata = DataProcessor.merge_files(
            file_paths, 
            output_format=task.output_format
        )
        
        # 分析列类型
        preview_data = DataPreviewGenerator.generate_preview(combined_header, merged_rows)
        column_types = preview_data['column_types']
        
        # 生成图表数据
        charts = ChartGenerator.generate_statistics_charts(
            combined_header, 
            merged_rows, 
            column_types
        )
        
        response_data = {
            'success': True,
            'charts': charts,
            'statistics': preview_data.get('statistics', {}),
            'analyzed_files': len(file_paths),
            'total_files': len(files)
        }
        
        if warning_message:
            response_data['warning'] = warning_message
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

