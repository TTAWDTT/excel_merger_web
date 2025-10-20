from django.contrib import admin
from .models import (MergeTask, UploadedFile, ColumnRule, CellOperation,
                     TaskTemplate, FilePreview, DataCleaningRule,
                     DataValidationRule, ValidationResult)


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


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'output_format', 'created_at', 'updated_at')
    list_filter = ('output_format', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FilePreview)
class FilePreviewAdmin(admin.ModelAdmin):
    list_display = ('uploaded_file', 'total_rows', 'total_columns', 'file_size', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(DataCleaningRule)
class DataCleaningRuleAdmin(admin.ModelAdmin):
    list_display = ('task', 'action', 'order')
    list_filter = ('action',)
    search_fields = ('task__name',)


@admin.register(DataValidationRule)
class DataValidationRuleAdmin(admin.ModelAdmin):
    list_display = ('task', 'column', 'rule_type')
    list_filter = ('rule_type',)
    search_fields = ('task__name', 'column')


@admin.register(ValidationResult)
class ValidationResultAdmin(admin.ModelAdmin):
    list_display = ('task', 'is_valid', 'created_at')
    list_filter = ('is_valid', 'created_at')
    readonly_fields = ('created_at',)
