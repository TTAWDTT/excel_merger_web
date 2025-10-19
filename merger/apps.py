from django.apps import AppConfig


class MergerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'merger'
    verbose_name = 'Excel 合并工具'
