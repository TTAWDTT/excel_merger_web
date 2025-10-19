from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
from pathlib import Path
import json
import os

from .models import MergeTask, UploadedFile, ColumnRule, CellOperation
from .core import excel_processor


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
            if not file.name.endswith('.xlsx'):
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
    """API: 处理任务"""
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
            
            # 合并文件
            combined_header, merged_rows, all_images = excel_processor.merge_excel_files(file_paths)
            
            # 应用列规则
            if hasattr(task, 'column_rule'):
                rule_dict = task.column_rule.to_dict()
                excel_processor.create_derived_column(merged_rows, combined_header, rule_dict)
            
            # 应用单元格操作
            operations = [op.to_dict() for op in task.cell_operations.all()]
            if operations:
                excel_processor.apply_cell_operations(merged_rows, combined_header, operations)
            
            # 应用列过滤
            if task.filter_mode != 'none' and task.filter_columns:
                combined_header, merged_rows = excel_processor.filter_columns(
                    combined_header, 
                    merged_rows, 
                    task.filter_mode, 
                    task.filter_columns
                )
            
            # 生成输出文件
            output_filename = f"merged_{task.id}.{task.output_format}"
            output_path = Path(settings.MEDIA_ROOT) / 'results' / output_filename
            
            excel_processor.write_merged_excel(
                combined_header,
                merged_rows,
                output_path,
                all_images,
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
                'download_url': task.result_file.url
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
