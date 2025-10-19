from django.urls import path
from . import views

urlpatterns = [
    # 页面路由
    path('', views.index, name='index'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    
    # API 路由
    path('api/tasks/create/', views.api_create_task, name='api_create_task'),
    path('api/tasks/<int:task_id>/upload/', views.api_upload_file, name='api_upload_file'),
    path('api/tasks/<int:task_id>/column-rule/', views.api_add_column_rule, name='api_add_column_rule'),
    path('api/tasks/<int:task_id>/cell-operations/', views.api_add_cell_operations, name='api_add_cell_operations'),
    path('api/tasks/<int:task_id>/process/', views.api_process_task, name='api_process_task'),
    path('api/tasks/<int:task_id>/download/', views.api_download_result, name='api_download_result'),
    path('api/tasks/<int:task_id>/delete/', views.api_delete_task, name='api_delete_task'),
    path('api/tasks/<int:task_id>/status/', views.api_get_task_status, name='api_get_task_status'),
    path('api/files/<int:file_id>/delete/', views.api_delete_file, name='api_delete_file'),
]
