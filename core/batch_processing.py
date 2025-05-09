# 批处理功能核心模块
import os
import pandas as pd
from core.deduplication import deduplicate_dataframe, deduplicate_with_similarity

class BatchProcessor:
    """批量Excel文件处理器"""
    
    def __init__(self):
        self.file_paths = []
        self.results = {}
        self.total_files = 0
        self.processed_files = 0
        
    def add_files(self, file_paths):
        """添加要处理的文件路径"""
        self.file_paths.extend(file_paths)
        self.total_files = len(self.file_paths)
        
    def clear_files(self):
        """清空文件列表"""
        self.file_paths = []
        self.results = {}
        self.total_files = 0
        self.processed_files = 0
        
    def get_progress_percentage(self):
        """获取处理进度百分比"""
        if self.total_files == 0:
            return 0
        return int((self.processed_files / self.total_files) * 100)
    
    def process_file(self, file_path, dedup_config):
        """处理单个文件的多个工作表
        
        Args:
            file_path: Excel文件路径
            dedup_config: 去重配置，格式为:
                {
                    "sheet_name1": {
                        "key_columns": ["col1", "col2"],
                        "keep_option": "first",
                        "use_model": true,  # 是否使用模型
                        "model_id": "model_id"  # 模型ID
                    },
                    "sheet_name2": {
                        "key_columns": ["col3"],
                        "keep_option": "last"
                    }
                }
        """
        try:
            # 初始化结果
            sheets_results = {}
            total_rows = 0
            total_remaining = 0
            total_removed = 0
            
            # 处理每个工作表
            for sheet_name, config in dedup_config.items():
                if not config.get('key_columns'):
                    # 跳过未配置列的工作表
                    continue
                    
                # 读取Excel工作表
                df_original = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_rows = len(df_original)
                total_rows += sheet_rows
                
                # 获取配置
                keep_option = config.get('keep_option', 'first')
                use_model = config.get('use_model', False)
                model_id = config.get('model_id', None)
                
                # 获取要进行相似度比较的列
                similarity_columns = {}
                for col in config.get('key_columns', []):
                    # 如果列名包含文本(如名称、描述等)，使用相似度比较
                    is_text_column = False
                    for keyword in ['name', 'title', 'desc', 'text', 'content', 'addr', '名', '称', '标题', '内容', '描述', '地址']:
                        if keyword in col.lower():
                            is_text_column = True
                            break
                    
                    # 检测数据类型，如果有对象型(包含字符串)类型，视为文本列
                    if df_original[col].dtype == 'object':
                        # 抽样检查，如果有50%以上是字符串且长度>3，视为文本列
                        sample = df_original[col].sample(min(100, len(df_original))).astype(str)
                        text_ratio = sum(sample.str.len() > 3) / len(sample)
                        if text_ratio > 0.5:
                            is_text_column = True
                    
                    # 添加到相似度列配置
                    if is_text_column:
                        similarity_columns[col] = 'word_based'  # 默认使用分词相似度
                
                # 执行去重操作
                if similarity_columns and use_model:
                    # 有文本列且启用模型，使用相似度去重
                    exact_columns = [col for col in config.get('key_columns', []) if col not in similarity_columns]
                    df_deduplicated, _ = deduplicate_with_similarity(
                        df_original,
                        exact_key_columns=exact_columns,
                        similarity_columns=similarity_columns,
                        keep_option=keep_option,
                        use_model=use_model,
                        model_id=model_id
                    )
                else:
                    # 无文本列或未启用模型，使用精确去重
                    df_deduplicated = deduplicate_dataframe(
                        df_original, 
                        config['key_columns'],
                        keep_option
                    )
                
                # 计算结果统计
                sheet_remaining = len(df_deduplicated)
                sheet_removed = sheet_rows - sheet_remaining
                total_remaining += sheet_remaining
                total_removed += sheet_removed
                
                # 存储工作表结果
                sheets_results[sheet_name] = {
                    'original': df_original,
                    'deduplicated': df_deduplicated,
                    'stats': {
                        'total_rows': sheet_rows,
                        'remaining_rows': sheet_remaining,
                        'duplicates_removed': sheet_removed
                    }
                }
            
            # 存储文件级结果
            self.results[file_path] = {
                'sheets': sheets_results,
                'stats': {
                    'total_rows': total_rows,
                    'remaining_rows': total_remaining,
                    'duplicates_removed': total_removed,
                    'success': True
                }
            }
            
            return True, file_path, None
            
        except Exception as e:
            # 处理错误
            self.results[file_path] = {
                'sheets': {},
                'stats': {
                    'total_rows': 0,
                    'remaining_rows': 0,
                    'duplicates_removed': 0,
                    'success': False,
                    'error': str(e)
                }
            }
            
            return False, file_path, str(e)
    
    def save_results(self, output_dir, file_suffix="_去重"):
        """保存所有处理结果
        
        Args:
            output_dir: 输出目录路径
            file_suffix: 文件后缀，默认为"_去重"
            
        Returns:
            tuple: (已保存文件列表, 错误列表)
        """
        saved_files = []
        errors = []
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        for file_path, result in self.results.items():
            if not result['stats']['success']:
                errors.append((file_path, result['stats'].get('error', '未知错误')))
                continue
                
            try:
                # 生成输出文件名（使用后缀而非前缀）
                original_filename = os.path.basename(file_path)
                name, ext = os.path.splitext(original_filename)
                new_filename = f"{name}{file_suffix}{ext}"
                output_path = os.path.join(output_dir, new_filename)
                
                # 创建Excel writer
                with pd.ExcelWriter(output_path) as writer:
                    # 保存每个工作表
                    for sheet_name, sheet_result in result['sheets'].items():
                        # 只保存实际处理过的工作表
                        if 'deduplicated' in sheet_result:
                            sheet_result['deduplicated'].to_excel(
                                writer, 
                                sheet_name=sheet_name,
                                index=False
                            )
                
                saved_files.append((file_path, output_path))
                
            except Exception as e:
                errors.append((file_path, str(e)))
        
        return saved_files, errors
    
    def generate_report(self):
        """生成批处理结果报告"""
        report = {
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'success_count': 0,
            'error_count': 0,
            'total_rows_processed': 0,
            'total_duplicates_removed': 0,
            'file_details': {}
        }
        
        for file_path, result in self.results.items():
            stats = result['stats']
            file_name = os.path.basename(file_path)
            
            if stats['success']:
                report['success_count'] += 1
                report['total_rows_processed'] += stats['total_rows']
                report['total_duplicates_removed'] += stats['duplicates_removed']
            else:
                report['error_count'] += 1
                
            # 构建文件详情
            file_detail = {
                'path': file_path,
                'success': stats['success'],
                'total_rows': stats['total_rows'],
                'remaining_rows': stats['remaining_rows'],
                'duplicates_removed': stats['duplicates_removed'],
                'error': stats.get('error', None),
                'sheets': {}
            }
            
            # 添加工作表详情
            if 'sheets' in result:
                for sheet_name, sheet_result in result['sheets'].items():
                    if 'stats' in sheet_result:
                        file_detail['sheets'][sheet_name] = sheet_result['stats']
            
            report['file_details'][file_name] = file_detail
            
        return report 