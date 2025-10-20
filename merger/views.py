from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
from pathlib import Path
import json
import os

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

