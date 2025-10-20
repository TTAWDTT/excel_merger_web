from django.db import models
from django.utils import timezone
import json


class MergeTask(models.Model):
    """合并任务模型"""
    STATUS_CHOICES = [
        ('pending', '等待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    OUTPUT_FORMAT_CHOICES = [
        ('xlsx', 'XLSX'),
        ('xls', 'XLS'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    FILTER_MODE_CHOICES = [
        ('none', '不过滤'),
        ('keep', '只保留指定列'),
        ('remove', '删除指定列'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='任务名称')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    output_format = models.CharField(max_length=10, choices=OUTPUT_FORMAT_CHOICES, default='xlsx', verbose_name='输出格式')
    filter_mode = models.CharField(max_length=10, choices=FILTER_MODE_CHOICES, default='none', verbose_name='列过滤模式')
    filter_columns = models.JSONField(default=list, verbose_name='过滤列列表')
    result_file = models.FileField(upload_to='results/', null=True, blank=True, verbose_name='结果文件')
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '合并任务'
        verbose_name_plural = '合并任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"


class UploadedFile(models.Model):
    """上传文件模型"""
    task = models.ForeignKey(MergeTask, on_delete=models.CASCADE, related_name='files', verbose_name='所属任务')
    file = models.FileField(upload_to='uploads/', verbose_name='文件')
    original_filename = models.CharField(max_length=255, verbose_name='原始文件名')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    
    class Meta:
        verbose_name = '上传文件'
        verbose_name_plural = '上传文件'
        ordering = ['uploaded_at']
    
    def __str__(self):
        return self.original_filename


class ColumnRule(models.Model):
    """列派生规则模型"""
    task = models.OneToOneField(MergeTask, on_delete=models.CASCADE, related_name='column_rule', null=True, blank=True, verbose_name='所属任务')
    name = models.CharField(max_length=200, verbose_name='规则名称')
    source_column = models.CharField(max_length=100, verbose_name='源列名')
    new_column = models.CharField(max_length=100, verbose_name='新列名')
    extraction_start = models.IntegerField(null=True, blank=True, verbose_name='提取起始位置')
    extraction_end = models.IntegerField(null=True, blank=True, verbose_name='提取结束位置')
    extraction_one_indexed = models.BooleanField(default=True, verbose_name='使用1索引')
    mappings = models.JSONField(default=list, verbose_name='映射规则')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '列规则'
        verbose_name_plural = '列规则'
    
    def __str__(self):
        return self.name
    
    def to_dict(self):
        """转换为字典格式"""
        rule = {
            'source_column': self.source_column,
            'new_column': self.new_column,
            'mappings': self.mappings,
        }
        if self.extraction_start is not None and self.extraction_end is not None:
            rule['extraction'] = {
                'start': self.extraction_start,
                'end': self.extraction_end,
                'one_indexed': self.extraction_one_indexed,
            }
        return rule


class CellOperation(models.Model):
    """单元格操作模型"""
    ACTION_CHOICES = [
        ('add_prefix', '添加前缀'),
        ('add_suffix', '添加后缀'),
        ('remove_prefix', '删除前缀'),
        ('remove_suffix', '删除后缀'),
        ('replace', '替换文本'),
        ('insert_at', '指定位置插入'),
        ('delete_at', '指定位置删除'),
    ]
    
    task = models.ForeignKey(MergeTask, on_delete=models.CASCADE, related_name='cell_operations', verbose_name='所属任务')
    column = models.CharField(max_length=100, verbose_name='列名')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='操作类型')
    value = models.CharField(max_length=200, null=True, blank=True, verbose_name='值')
    old_value = models.CharField(max_length=200, null=True, blank=True, verbose_name='旧值(替换用)')
    new_value = models.CharField(max_length=200, null=True, blank=True, verbose_name='新值(替换用)')
    position = models.IntegerField(null=True, blank=True, verbose_name='位置')
    length = models.IntegerField(null=True, blank=True, verbose_name='长度(删除用)')
    order = models.IntegerField(default=0, verbose_name='执行顺序')
    
    class Meta:
        verbose_name = '单元格操作'
        verbose_name_plural = '单元格操作'
        ordering = ['task', 'order']
    
    def __str__(self):
        return f"{self.column} - {self.get_action_display()}"
    
    def to_dict(self):
        """转换为字典格式"""
        op = {
            'column': self.column,
            'action': self.action,
        }
        if self.value:
            op['value'] = self.value
        if self.old_value:
            op['old_value'] = self.old_value
        if self.new_value:
            op['new_value'] = self.new_value
        if self.position is not None:
            op['position'] = self.position
        if self.length is not None:
            op['length'] = self.length
        return op


class TaskTemplate(models.Model):
    """任务模板模型"""
    name = models.CharField(max_length=200, verbose_name='模板名称')
    description = models.TextField(blank=True, verbose_name='模板描述')
    output_format = models.CharField(max_length=10, choices=MergeTask.OUTPUT_FORMAT_CHOICES, default='xlsx', verbose_name='输出格式')
    filter_mode = models.CharField(max_length=10, choices=MergeTask.FILTER_MODE_CHOICES, default='none', verbose_name='列过滤模式')
    filter_columns = models.JSONField(default=list, verbose_name='过滤列列表')
    
    # 列规则配置
    column_rule_config = models.JSONField(null=True, blank=True, verbose_name='列规则配置')
    
    # 单元格操作配置
    cell_operations_config = models.JSONField(default=list, verbose_name='单元格操作配置')
    
    # 数据清洗配置
    cleaning_config = models.JSONField(default=dict, verbose_name='数据清洗配置')
    
    # 数据验证配置
    validation_config = models.JSONField(default=dict, verbose_name='数据验证配置')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '任务模板'
        verbose_name_plural = '任务模板'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def apply_to_task(self, task):
        """将模板应用到任务"""
        task.output_format = self.output_format
        task.filter_mode = self.filter_mode
        task.filter_columns = self.filter_columns
        task.save()
        
        # 应用列规则
        if self.column_rule_config:
            ColumnRule.objects.filter(task=task).delete()
            ColumnRule.objects.create(
                task=task,
                name=self.column_rule_config.get('name', '列规则'),
                source_column=self.column_rule_config['source_column'],
                new_column=self.column_rule_config['new_column'],
                extraction_start=self.column_rule_config.get('extraction_start'),
                extraction_end=self.column_rule_config.get('extraction_end'),
                extraction_one_indexed=self.column_rule_config.get('extraction_one_indexed', True),
                mappings=self.column_rule_config.get('mappings', [])
            )
        
        # 应用单元格操作
        CellOperation.objects.filter(task=task).delete()
        for idx, op in enumerate(self.cell_operations_config):
            CellOperation.objects.create(
                task=task,
                column=op['column'],
                action=op['action'],
                value=op.get('value'),
                old_value=op.get('old_value'),
                new_value=op.get('new_value'),
                position=op.get('position'),
                length=op.get('length'),
                order=idx
            )


class FilePreview(models.Model):
    """文件预览数据模型"""
    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE, related_name='preview', verbose_name='上传文件')
    headers = models.JSONField(verbose_name='列头')
    sample_rows = models.JSONField(verbose_name='示例数据(前100行)')
    total_rows = models.IntegerField(verbose_name='总行数')
    total_columns = models.IntegerField(verbose_name='总列数')
    file_size = models.BigIntegerField(verbose_name='文件大小(字节)')
    
    # 数据统计
    column_types = models.JSONField(default=dict, verbose_name='列类型分析')
    null_counts = models.JSONField(default=dict, verbose_name='空值统计')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '文件预览'
        verbose_name_plural = '文件预览'
    
    def __str__(self):
        return f"Preview of {self.uploaded_file.original_filename}"


class DataCleaningRule(models.Model):
    """数据清洗规则模型"""
    ACTION_CHOICES = [
        ('remove_duplicates', '删除重复行'),
        ('fill_null', '填充空值'),
        ('convert_type', '转换数据类型'),
        ('trim_spaces', '去除空格'),
        ('standardize_date', '标准化日期'),
        ('uppercase', '转大写'),
        ('lowercase', '转小写'),
    ]
    
    FILL_METHOD_CHOICES = [
        ('forward', '向前填充'),
        ('backward', '向后填充'),
        ('value', '固定值填充'),
        ('mean', '均值填充'),
        ('median', '中位数填充'),
    ]
    
    task = models.ForeignKey(MergeTask, on_delete=models.CASCADE, related_name='cleaning_rules', verbose_name='所属任务')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name='清洗动作')
    columns = models.JSONField(default=list, verbose_name='应用列')
    parameters = models.JSONField(default=dict, verbose_name='参数')
    order = models.IntegerField(default=0, verbose_name='执行顺序')
    
    class Meta:
        verbose_name = '数据清洗规则'
        verbose_name_plural = '数据清洗规则'
        ordering = ['task', 'order']
    
    def __str__(self):
        return f"{self.task.name} - {self.get_action_display()}"


class DataValidationRule(models.Model):
    """数据验证规则模型"""
    RULE_TYPE_CHOICES = [
        ('required', '必填字段'),
        ('type', '数据类型'),
        ('range', '数值范围'),
        ('length', '长度限制'),
        ('regex', '正则表达式'),
        ('unique', '唯一性'),
        ('enum', '枚举值'),
    ]
    
    task = models.ForeignKey(MergeTask, on_delete=models.CASCADE, related_name='validation_rules', verbose_name='所属任务')
    column = models.CharField(max_length=100, verbose_name='列名')
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES, verbose_name='规则类型')
    parameters = models.JSONField(default=dict, verbose_name='验证参数')
    error_message = models.CharField(max_length=200, blank=True, verbose_name='错误提示')
    
    class Meta:
        verbose_name = '数据验证规则'
        verbose_name_plural = '数据验证规则'
    
    def __str__(self):
        return f"{self.column} - {self.get_rule_type_display()}"


class ValidationResult(models.Model):
    """验证结果模型"""
    task = models.OneToOneField(MergeTask, on_delete=models.CASCADE, related_name='validation_result', verbose_name='所属任务')
    is_valid = models.BooleanField(default=True, verbose_name='验证通过')
    errors = models.JSONField(default=list, verbose_name='错误列表')
    warnings = models.JSONField(default=list, verbose_name='警告列表')
    statistics = models.JSONField(default=dict, verbose_name='统计信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '验证结果'
        verbose_name_plural = '验证结果'
    
    def __str__(self):
        return f"Validation of {self.task.name}"
