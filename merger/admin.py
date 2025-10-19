from django.contrib import admin
from .models import MergeTask, UploadedFile, ColumnRule, CellOperation


@admin.register(MergeTask)
class MergeTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'output_format', 'created_at', 'updated_at')
    list_filter = ('status', 'output_format', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'task', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('original_filename',)


@admin.register(ColumnRule)
class ColumnRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_column', 'new_column', 'task', 'created_at')
    search_fields = ('name', 'source_column', 'new_column')


@admin.register(CellOperation)
class CellOperationAdmin(admin.ModelAdmin):
    list_display = ('column', 'action', 'task', 'order')
    list_filter = ('action',)
    search_fields = ('column',)
