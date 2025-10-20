"""
数据分析和处理工具模块
支持数据预览、清洗、验证和可视化
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import Counter
import statistics


class DataPreviewGenerator:
    """数据预览生成器"""
    
    @staticmethod
    def generate_preview(headers: List[str], rows: List[List[Any]], max_rows: int = 100) -> Dict[str, Any]:
        """
        生成数据预览
        
        Args:
            headers: 列头列表
            rows: 数据行列表
            max_rows: 最大预览行数
            
        Returns:
            包含预览信息的字典
        """
        total_rows = len(rows)
        total_columns = len(headers)
        
        # 获取示例数据
        sample_rows = rows[:max_rows]
        
        # 分析列类型
        column_types = DataPreviewGenerator._analyze_column_types(headers, rows)
        
        # 统计空值
        null_counts = DataPreviewGenerator._count_nulls(headers, rows)
        
        # 计算基本统计
        statistics_data = DataPreviewGenerator._calculate_statistics(headers, rows, column_types)
        
        return {
            'headers': headers,
            'sample_rows': sample_rows,
            'total_rows': total_rows,
            'total_columns': total_columns,
            'column_types': column_types,
            'null_counts': null_counts,
            'statistics': statistics_data
        }
    
    @staticmethod
    def _analyze_column_types(headers: List[str], rows: List[List[Any]]) -> Dict[str, str]:
        """分析每列的数据类型"""
        column_types = {}
        
        for idx, header in enumerate(headers):
            types = []
            for row in rows[:100]:  # 取前100行分析
                if idx < len(row) and row[idx] is not None and row[idx] != '':
                    value = row[idx]
                    types.append(DataPreviewGenerator._detect_type(value))
            
            # 统计最常见的类型
            if types:
                type_counter = Counter(types)
                column_types[header] = type_counter.most_common(1)[0][0]
            else:
                column_types[header] = 'unknown'
        
        return column_types
    
    @staticmethod
    def _detect_type(value: Any) -> str:
        """检测单个值的类型"""
        if isinstance(value, (int, float)):
            return 'number'
        
        if isinstance(value, str):
            # 尝试检测日期
            if DataPreviewGenerator._is_date(value):
                return 'date'
            # 尝试检测数字
            if DataPreviewGenerator._is_numeric(value):
                return 'number'
            # 尝试检测邮箱
            if DataPreviewGenerator._is_email(value):
                return 'email'
            # 尝试检测电话
            if DataPreviewGenerator._is_phone(value):
                return 'phone'
            return 'text'
        
        return 'unknown'
    
    @staticmethod
    def _is_date(value: str) -> bool:
        """检测是否为日期"""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}',
        ]
        return any(re.match(pattern, str(value)) for pattern in date_patterns)
    
    @staticmethod
    def _is_numeric(value: str) -> bool:
        """检测是否为数字"""
        try:
            float(value)
            return True
        except:
            return False
    
    @staticmethod
    def _is_email(value: str) -> bool:
        """检测是否为邮箱"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, str(value)))
    
    @staticmethod
    def _is_phone(value: str) -> bool:
        """检测是否为电话号码"""
        pattern = r'^\d{11}$|^\d{3}-\d{8}$|^\d{4}-\d{7}$'
        return bool(re.match(pattern, str(value)))
    
    @staticmethod
    def _count_nulls(headers: List[str], rows: List[List[Any]]) -> Dict[str, int]:
        """统计每列的空值数量"""
        null_counts = {header: 0 for header in headers}
        
        for row in rows:
            for idx, header in enumerate(headers):
                if idx >= len(row) or row[idx] is None or row[idx] == '':
                    null_counts[header] += 1
        
        return null_counts
    
    @staticmethod
    def _calculate_statistics(headers: List[str], rows: List[List[Any]], 
                             column_types: Dict[str, str]) -> Dict[str, Dict]:
        """计算统计信息"""
        stats = {}
        
        for idx, header in enumerate(headers):
            col_type = column_types.get(header, 'unknown')
            
            if col_type == 'number':
                values = []
                for row in rows:
                    if idx < len(row) and row[idx] is not None and row[idx] != '':
                        try:
                            values.append(float(row[idx]))
                        except:
                            pass
                
                if values:
                    stats[header] = {
                        'min': min(values),
                        'max': max(values),
                        'mean': statistics.mean(values),
                        'median': statistics.median(values),
                        'count': len(values)
                    }
            elif col_type == 'text':
                values = []
                for row in rows:
                    if idx < len(row) and row[idx] is not None and row[idx] != '':
                        values.append(str(row[idx]))
                
                if values:
                    stats[header] = {
                        'unique_count': len(set(values)),
                        'total_count': len(values),
                        'most_common': Counter(values).most_common(5)
                    }
        
        return stats


class DataCleaner:
    """数据清洗工具"""
    
    @staticmethod
    def apply_cleaning_rules(headers: List[str], rows: List[List[Any]], 
                            rules: List[Dict]) -> Tuple[List[str], List[List[Any]]]:
        """
        应用数据清洗规则
        
        Args:
            headers: 列头
            rows: 数据行
            rules: 清洗规则列表
            
        Returns:
            清洗后的 (headers, rows)
        """
        # 按顺序执行规则
        for rule in sorted(rules, key=lambda x: x.get('order', 0)):
            action = rule.get('action')
            
            if action == 'remove_duplicates':
                rows = DataCleaner._remove_duplicates(headers, rows, rule)
            elif action == 'fill_null':
                rows = DataCleaner._fill_null(headers, rows, rule)
            elif action == 'convert_type':
                rows = DataCleaner._convert_type(headers, rows, rule)
            elif action == 'trim_spaces':
                rows = DataCleaner._trim_spaces(headers, rows, rule)
            elif action == 'standardize_date':
                rows = DataCleaner._standardize_date(headers, rows, rule)
            elif action == 'uppercase':
                rows = DataCleaner._uppercase(headers, rows, rule)
            elif action == 'lowercase':
                rows = DataCleaner._lowercase(headers, rows, rule)
        
        return headers, rows
    
    @staticmethod
    def _remove_duplicates(headers: List[str], rows: List[List[Any]], rule: Dict) -> List[List[Any]]:
        """删除重复行"""
        columns = rule.get('columns', [])
        
        if not columns:
            # 删除完全重复的行
            seen = set()
            unique_rows = []
            for row in rows:
                row_tuple = tuple(row)
                if row_tuple not in seen:
                    seen.add(row_tuple)
                    unique_rows.append(row)
            return unique_rows
        else:
            # 根据指定列删除重复
            col_indices = [headers.index(col) for col in columns if col in headers]
            seen = set()
            unique_rows = []
            for row in rows:
                key = tuple(row[idx] if idx < len(row) else None for idx in col_indices)
                if key not in seen:
                    seen.add(key)
                    unique_rows.append(row)
            return unique_rows
    
    @staticmethod
    def _fill_null(headers: List[str], rows: List[List[Any]], rule: Dict) -> List[List[Any]]:
        """填充空值"""
        columns = rule.get('columns', [])
        method = rule.get('parameters', {}).get('method', 'forward')
        fill_value = rule.get('parameters', {}).get('value', '')
        
        for col in columns:
            if col not in headers:
                continue
            
            col_idx = headers.index(col)
            
            if method == 'forward':
                # 向前填充
                last_value = None
                for row in rows:
                    if col_idx >= len(row):
                        row.extend([None] * (col_idx - len(row) + 1))
                    
                    if row[col_idx] is None or row[col_idx] == '':
                        row[col_idx] = last_value
                    else:
                        last_value = row[col_idx]
            
            elif method == 'backward':
                # 向后填充
                next_value = None
                for row in reversed(rows):
                    if col_idx >= len(row):
                        row.extend([None] * (col_idx - len(row) + 1))
                    
                    if row[col_idx] is None or row[col_idx] == '':
                        row[col_idx] = next_value
                    else:
                        next_value = row[col_idx]
            
            elif method == 'value':
                # 固定值填充
                for row in rows:
                    if col_idx >= len(row):
                        row.extend([None] * (col_idx - len(row) + 1))
                    
                    if row[col_idx] is None or row[col_idx] == '':
                        row[col_idx] = fill_value
            
            elif method == 'mean':
                # 均值填充（仅数值）
                values = [float(row[col_idx]) for row in rows 
                         if col_idx < len(row) and row[col_idx] is not None 
                         and row[col_idx] != '' and str(row[col_idx]).replace('.', '').replace('-', '').isdigit()]
                
                if values:
                    mean_value = statistics.mean(values)
                    for row in rows:
                        if col_idx >= len(row):
                            row.extend([None] * (col_idx - len(row) + 1))
                        if row[col_idx] is None or row[col_idx] == '':
                            row[col_idx] = mean_value
            
            elif method == 'median':
                # 中位数填充（仅数值）
                values = [float(row[col_idx]) for row in rows 
                         if col_idx < len(row) and row[col_idx] is not None 
                         and row[col_idx] != '' and str(row[col_idx]).replace('.', '').replace('-', '').isdigit()]
                
                if values:
                    median_value = statistics.median(values)
                    for row in rows:
                        if col_idx >= len(row):
                            row.extend([None] * (col_idx - len(row) + 1))
                        if row[col_idx] is None or row[col_idx] == '':
                            row[col_idx] = median_value
        
        return rows
    
    @staticmethod
    def _convert_type(headers: List[str], rows: List[List[Any]], rule: Dict) -> List[List[Any]]:
        """转换数据类型"""
        columns = rule.get('columns', [])
        target_type = rule.get('parameters', {}).get('type', 'string')
        
        for col in columns:
            if col not in headers:
                continue
            
            col_idx = headers.index(col)
            
            for row in rows:
                if col_idx >= len(row):
                    continue
                
                try:
                    if target_type == 'integer':
                        row[col_idx] = int(float(str(row[col_idx])))
                    elif target_type == 'float':
                        row[col_idx] = float(row[col_idx])
                    elif target_type == 'string':
                        row[col_idx] = str(row[col_idx])
                except:
                    pass
        
        return rows
    
    @staticmethod
    def _trim_spaces(headers: List[str], rows: List[List[Any]], rule: Dict) -> List[List[Any]]:
        """去除空格"""
        columns = rule.get('columns', [])
        
        for col in columns:
            if col not in headers:
                continue
            
            col_idx = headers.index(col)
            
            for row in rows:
                if col_idx < len(row) and isinstance(row[col_idx], str):
                    row[col_idx] = row[col_idx].strip()
        
        return rows
    
    @staticmethod
    def _standardize_date(headers: List[str], rows: List[List[Any]], rule: Dict) -> List[List[Any]]:
        """标准化日期格式"""
        columns = rule.get('columns', [])
        target_format = rule.get('parameters', {}).get('format', '%Y-%m-%d')
        
        for col in columns:
            if col not in headers:
                continue
            
            col_idx = headers.index(col)
            
            for row in rows:
                if col_idx >= len(row) or not row[col_idx]:
                    continue
                
                # 尝试多种日期格式
                date_formats = [
                    '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y',
                    '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'
                ]
                
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(str(row[col_idx]), fmt)
                        row[col_idx] = dt.strftime(target_format)
                        break
                    except:
                        continue
        
        return rows
    
    @staticmethod
    def _uppercase(headers: List[str], rows: List[List[Any]], rule: Dict) -> List[List[Any]]:
        """转大写"""
        columns = rule.get('columns', [])
        
        for col in columns:
            if col not in headers:
                continue
            
            col_idx = headers.index(col)
            
            for row in rows:
                if col_idx < len(row) and isinstance(row[col_idx], str):
                    row[col_idx] = row[col_idx].upper()
        
        return rows
    
    @staticmethod
    def _lowercase(headers: List[str], rows: List[List[Any]], rule: Dict) -> List[List[Any]]:
        """转小写"""
        columns = rule.get('columns', [])
        
        for col in columns:
            if col not in headers:
                continue
            
            col_idx = headers.index(col)
            
            for row in rows:
                if col_idx < len(row) and isinstance(row[col_idx], str):
                    row[col_idx] = row[col_idx].lower()
        
        return rows


class DataValidator:
    """数据验证工具"""
    
    @staticmethod
    def validate_data(headers: List[str], rows: List[List[Any]], 
                     rules: List[Dict]) -> Dict[str, Any]:
        """
        验证数据
        
        Args:
            headers: 列头
            rows: 数据行
            rules: 验证规则列表
            
        Returns:
            验证结果字典
        """
        errors = []
        warnings = []
        
        for rule in rules:
            rule_type = rule.get('rule_type')
            column = rule.get('column')
            
            if column not in headers:
                warnings.append({
                    'column': column,
                    'message': f"列 '{column}' 不存在"
                })
                continue
            
            col_idx = headers.index(column)
            
            if rule_type == 'required':
                errors.extend(DataValidator._validate_required(column, col_idx, rows, rule))
            elif rule_type == 'type':
                errors.extend(DataValidator._validate_type(column, col_idx, rows, rule))
            elif rule_type == 'range':
                errors.extend(DataValidator._validate_range(column, col_idx, rows, rule))
            elif rule_type == 'length':
                errors.extend(DataValidator._validate_length(column, col_idx, rows, rule))
            elif rule_type == 'regex':
                errors.extend(DataValidator._validate_regex(column, col_idx, rows, rule))
            elif rule_type == 'unique':
                errors.extend(DataValidator._validate_unique(column, col_idx, rows, rule))
            elif rule_type == 'enum':
                errors.extend(DataValidator._validate_enum(column, col_idx, rows, rule))
        
        is_valid = len(errors) == 0
        
        # 计算统计信息
        statistics_data = {
            'total_rows': len(rows),
            'total_errors': len(errors),
            'total_warnings': len(warnings),
            'error_rate': len(errors) / max(len(rows), 1)
        }
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'statistics': statistics_data
        }
    
    @staticmethod
    def _validate_required(column: str, col_idx: int, rows: List[List[Any]], rule: Dict) -> List[Dict]:
        """验证必填字段"""
        errors = []
        for row_idx, row in enumerate(rows):
            if col_idx >= len(row) or row[col_idx] is None or row[col_idx] == '':
                errors.append({
                    'row': row_idx + 1,
                    'column': column,
                    'value': row[col_idx] if col_idx < len(row) else None,
                    'message': rule.get('error_message', f"'{column}' 不能为空")
                })
        return errors
    
    @staticmethod
    def _validate_type(column: str, col_idx: int, rows: List[List[Any]], rule: Dict) -> List[Dict]:
        """验证数据类型"""
        errors = []
        expected_type = rule.get('parameters', {}).get('type', 'string')
        
        for row_idx, row in enumerate(rows):
            if col_idx >= len(row) or row[col_idx] is None or row[col_idx] == '':
                continue
            
            value = row[col_idx]
            is_valid = False
            
            if expected_type == 'number':
                try:
                    float(value)
                    is_valid = True
                except:
                    pass
            elif expected_type == 'integer':
                try:
                    int(float(value))
                    is_valid = True
                except:
                    pass
            elif expected_type == 'email':
                is_valid = bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(value)))
            elif expected_type == 'phone':
                is_valid = bool(re.match(r'^\d{11}$|^\d{3}-\d{8}$|^\d{4}-\d{7}$', str(value)))
            elif expected_type == 'date':
                date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y']
                for fmt in date_formats:
                    try:
                        datetime.strptime(str(value), fmt)
                        is_valid = True
                        break
                    except:
                        pass
            
            if not is_valid:
                errors.append({
                    'row': row_idx + 1,
                    'column': column,
                    'value': value,
                    'message': rule.get('error_message', f"'{column}' 类型错误，期望 {expected_type}")
                })
        
        return errors
    
    @staticmethod
    def _validate_range(column: str, col_idx: int, rows: List[List[Any]], rule: Dict) -> List[Dict]:
        """验证数值范围"""
        errors = []
        params = rule.get('parameters', {})
        min_value = params.get('min')
        max_value = params.get('max')
        
        for row_idx, row in enumerate(rows):
            if col_idx >= len(row) or row[col_idx] is None or row[col_idx] == '':
                continue
            
            try:
                value = float(row[col_idx])
                if min_value is not None and value < min_value:
                    errors.append({
                        'row': row_idx + 1,
                        'column': column,
                        'value': value,
                        'message': rule.get('error_message', f"'{column}' 值 {value} 小于最小值 {min_value}")
                    })
                if max_value is not None and value > max_value:
                    errors.append({
                        'row': row_idx + 1,
                        'column': column,
                        'value': value,
                        'message': rule.get('error_message', f"'{column}' 值 {value} 大于最大值 {max_value}")
                    })
            except:
                pass
        
        return errors
    
    @staticmethod
    def _validate_length(column: str, col_idx: int, rows: List[List[Any]], rule: Dict) -> List[Dict]:
        """验证长度限制"""
        errors = []
        params = rule.get('parameters', {})
        min_length = params.get('min')
        max_length = params.get('max')
        
        for row_idx, row in enumerate(rows):
            if col_idx >= len(row) or row[col_idx] is None or row[col_idx] == '':
                continue
            
            length = len(str(row[col_idx]))
            
            if min_length is not None and length < min_length:
                errors.append({
                    'row': row_idx + 1,
                    'column': column,
                    'value': row[col_idx],
                    'message': rule.get('error_message', f"'{column}' 长度 {length} 小于最小长度 {min_length}")
                })
            if max_length is not None and length > max_length:
                errors.append({
                    'row': row_idx + 1,
                    'column': column,
                    'value': row[col_idx],
                    'message': rule.get('error_message', f"'{column}' 长度 {length} 大于最大长度 {max_length}")
                })
        
        return errors
    
    @staticmethod
    def _validate_regex(column: str, col_idx: int, rows: List[List[Any]], rule: Dict) -> List[Dict]:
        """验证正则表达式"""
        errors = []
        pattern = rule.get('parameters', {}).get('pattern', '')
        
        if not pattern:
            return errors
        
        for row_idx, row in enumerate(rows):
            if col_idx >= len(row) or row[col_idx] is None or row[col_idx] == '':
                continue
            
            if not re.match(pattern, str(row[col_idx])):
                errors.append({
                    'row': row_idx + 1,
                    'column': column,
                    'value': row[col_idx],
                    'message': rule.get('error_message', f"'{column}' 不匹配正则表达式 {pattern}")
                })
        
        return errors
    
    @staticmethod
    def _validate_unique(column: str, col_idx: int, rows: List[List[Any]], rule: Dict) -> List[Dict]:
        """验证唯一性"""
        errors = []
        seen = set()
        
        for row_idx, row in enumerate(rows):
            if col_idx >= len(row) or row[col_idx] is None or row[col_idx] == '':
                continue
            
            value = row[col_idx]
            if value in seen:
                errors.append({
                    'row': row_idx + 1,
                    'column': column,
                    'value': value,
                    'message': rule.get('error_message', f"'{column}' 值 '{value}' 重复")
                })
            else:
                seen.add(value)
        
        return errors
    
    @staticmethod
    def _validate_enum(column: str, col_idx: int, rows: List[List[Any]], rule: Dict) -> List[Dict]:
        """验证枚举值"""
        errors = []
        allowed_values = rule.get('parameters', {}).get('values', [])
        
        for row_idx, row in enumerate(rows):
            if col_idx >= len(row) or row[col_idx] is None or row[col_idx] == '':
                continue
            
            if row[col_idx] not in allowed_values:
                errors.append({
                    'row': row_idx + 1,
                    'column': column,
                    'value': row[col_idx],
                    'message': rule.get('error_message', 
                                      f"'{column}' 值 '{row[col_idx]}' 不在允许的值列表中: {allowed_values}")
                })
        
        return errors


class ChartGenerator:
    """图表生成器"""
    
    @staticmethod
    def generate_statistics_charts(headers: List[str], rows: List[List[Any]], 
                                  column_types: Dict[str, str]) -> Dict[str, Any]:
        """
        生成统计图表数据
        
        Args:
            headers: 列头
            rows: 数据行
            column_types: 列类型映射
            
        Returns:
            图表数据字典
        """
        charts = {}
        
        # 1. 数据分布图（柱状图）
        charts['data_distribution'] = ChartGenerator._generate_distribution_chart(headers, rows)
        
        # 2. 列类型饼图
        charts['column_types'] = ChartGenerator._generate_type_pie_chart(column_types)
        
        # 3. 空值分析
        charts['null_analysis'] = ChartGenerator._generate_null_chart(headers, rows)
        
        # 4. 数值列统计（箱线图数据）
        charts['numeric_stats'] = ChartGenerator._generate_numeric_stats(headers, rows, column_types)
        
        # 5. 文本列词云数据
        charts['text_frequency'] = ChartGenerator._generate_text_frequency(headers, rows, column_types)
        
        return charts
    
    @staticmethod
    def _generate_distribution_chart(headers: List[str], rows: List[List[Any]]) -> Dict:
        """生成数据分布图"""
        return {
            'type': 'bar',
            'title': '数据行列分布',
            'data': {
                'categories': ['总行数', '总列数'],
                'values': [len(rows), len(headers)]
            }
        }
    
    @staticmethod
    def _generate_type_pie_chart(column_types: Dict[str, str]) -> Dict:
        """生成列类型饼图"""
        type_counter = Counter(column_types.values())
        
        return {
            'type': 'pie',
            'title': '列类型分布',
            'data': {
                'labels': list(type_counter.keys()),
                'values': list(type_counter.values())
            }
        }
    
    @staticmethod
    def _generate_null_chart(headers: List[str], rows: List[List[Any]]) -> Dict:
        """生成空值分析图"""
        null_counts = []
        
        for idx, header in enumerate(headers):
            null_count = sum(1 for row in rows 
                           if idx >= len(row) or row[idx] is None or row[idx] == '')
            null_counts.append(null_count)
        
        return {
            'type': 'bar',
            'title': '各列空值统计',
            'data': {
                'categories': headers,
                'values': null_counts,
                'total_rows': len(rows)
            }
        }
    
    @staticmethod
    def _generate_numeric_stats(headers: List[str], rows: List[List[Any]], 
                               column_types: Dict[str, str]) -> Dict:
        """生成数值列统计"""
        numeric_stats = []
        
        for idx, header in enumerate(headers):
            if column_types.get(header) != 'number':
                continue
            
            values = []
            for row in rows:
                if idx < len(row) and row[idx] is not None and row[idx] != '':
                    try:
                        values.append(float(row[idx]))
                    except:
                        pass
            
            if values:
                numeric_stats.append({
                    'column': header,
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'q1': statistics.quantiles(values, n=4)[0] if len(values) >= 4 else min(values),
                    'q3': statistics.quantiles(values, n=4)[2] if len(values) >= 4 else max(values)
                })
        
        return {
            'type': 'boxplot',
            'title': '数值列统计分析',
            'data': numeric_stats
        }
    
    @staticmethod
    def _generate_text_frequency(headers: List[str], rows: List[List[Any]], 
                                column_types: Dict[str, str]) -> Dict:
        """生成文本列词频"""
        text_frequency = {}
        
        for idx, header in enumerate(headers):
            if column_types.get(header) != 'text':
                continue
            
            values = []
            for row in rows:
                if idx < len(row) and row[idx] is not None and row[idx] != '':
                    values.append(str(row[idx]))
            
            if values:
                counter = Counter(values)
                text_frequency[header] = {
                    'most_common': counter.most_common(10),
                    'total_count': len(values),
                    'unique_count': len(set(values))
                }
        
        return {
            'type': 'wordcloud',
            'title': '文本列频率分析',
            'data': text_frequency
        }
