from django.urls import path
from . import views

urlpatterns = [
    # 页面路由
    path('', views.index, name='index'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    
    # API 路由 - 任务相关
    path('api/tasks/create/', views.api_create_task, name='api_create_task'),
    path('api/tasks/<int:task_id>/upload/', views.api_upload_file, name='api_upload_file'),
    path('api/tasks/<int:task_id>/column-rule/', views.api_add_column_rule, name='api_add_column_rule'),
    path('api/tasks/<int:task_id>/cell-operations/', views.api_add_cell_operations, name='api_add_cell_operations'),
    path('api/tasks/<int:task_id>/process/', views.api_process_task, name='api_process_task'),
    path('api/tasks/<int:task_id>/download/', views.api_download_result, name='api_download_result'),
    path('api/tasks/<int:task_id>/delete/', views.api_delete_task, name='api_delete_task'),
    path('api/tasks/<int:task_id>/status/', views.api_get_task_status, name='api_get_task_status'),
    
    # API 路由 - 文件相关
    path('api/files/<int:file_id>/delete/', views.api_delete_file, name='api_delete_file'),
    path('api/files/<int:file_id>/preview/', views.api_preview_file, name='api_preview_file'),
    
    # API 路由 - 模板相关
    path('api/templates/', views.api_list_templates, name='api_list_templates'),
    path('api/templates/save/', views.api_save_template, name='api_save_template'),
    path('api/templates/<int:template_id>/', views.api_get_template, name='api_get_template'),
    path('api/templates/<int:template_id>/delete/', views.api_delete_template, name='api_delete_template'),
    path('api/tasks/<int:task_id>/apply-template/<int:template_id>/', views.api_apply_template, name='api_apply_template'),
    
    # API 路由 - 数据清洗和验证
    path('api/tasks/<int:task_id>/cleaning-rules/', views.api_add_cleaning_rules, name='api_add_cleaning_rules'),
    path('api/tasks/<int:task_id>/validation-rules/', views.api_add_validation_rules, name='api_add_validation_rules'),
    path('api/tasks/<int:task_id>/validate/', views.api_validate_task_data, name='api_validate_task_data'),
    
    # API 路由 - 可视化图表
    path('api/tasks/<int:task_id>/charts/', views.api_generate_charts, name='api_generate_charts'),
]
