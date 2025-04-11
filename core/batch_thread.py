import os
from PyQt5.QtCore import QThread, pyqtSignal
from core.batch_processing import BatchProcessor
from core.excel_inspector import ExcelInspector

class BatchProcessingThread(QThread):
    """批处理线程类，用于后台处理多个Excel文件"""
    
    # 信号定义
    progress_signal = pyqtSignal(int)  # 进度百分比
    file_progress_signal = pyqtSignal(str, int)  # 当前文件和进度
    file_completed_signal = pyqtSignal(bool, str, str)  # 文件处理结果：成功/失败，文件路径，错误信息
    batch_completed_signal = pyqtSignal(dict)  # 批处理完成后的报告
    error_signal = pyqtSignal(str)  # 全局错误信息
    
    def __init__(self, file_paths, dedup_configs):
        """
        Args:
            file_paths: 要处理的文件路径列表
            dedup_configs: 每个文件的去重配置，格式为:
                {
                    "file_path1": {
                        "sheet_name1": {
                            "key_columns": ["col1", "col2"],
                            "keep_option": "first"
                        },
                        "sheet_name2": {
                            "key_columns": ["col3"],
                            "keep_option": "last"
                        }
                    },
                    "file_path2": {
                        ...
                    }
                }
        """
        super().__init__()
        self.file_paths = file_paths
        self.dedup_configs = dedup_configs
        self.processor = BatchProcessor()
        self.is_running = True
        
    def run(self):
        try:
            # 初始化处理器
            self.processor.clear_files()
            self.processor.add_files(self.file_paths)
            
            # 处理每个文件
            for index, file_path in enumerate(self.file_paths):
                # 检查是否中断执行
                if not self.is_running:
                    break
                    
                # 更新进度
                file_name = os.path.basename(file_path)
                self.file_progress_signal.emit(file_name, 0)
                total_progress = int((index / len(self.file_paths)) * 100)
                self.progress_signal.emit(total_progress)
                
                # 获取此文件的去重配置
                dedup_config = self.dedup_configs.get(file_path, {})
                
                # 处理文件
                success, path, error = self.processor.process_file(
                    file_path, 
                    dedup_config
                )
                
                # 更新文件进度
                self.file_progress_signal.emit(file_name, 100)
                self.processor.processed_files += 1
                
                # 发送文件结果信号
                error_message = error if error else ""
                self.file_completed_signal.emit(success, path, error_message)
                
                # 更新总进度
                self.progress_signal.emit(self.processor.get_progress_percentage())
            
            # 发送最终结果报告
            if self.is_running:
                report = self.processor.generate_report()
                self.batch_completed_signal.emit(report)
                
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def stop(self):
        """停止批处理"""
        self.is_running = False

class ExcelInspectionThread(QThread):
    """Excel文件检查线程，用于获取文件的工作表和列信息"""
    
    # 信号定义
    progress_signal = pyqtSignal(int)  # 进度百分比
    file_progress_signal = pyqtSignal(str, int, str)  # 当前文件、进度和错误(如有)
    inspection_completed_signal = pyqtSignal(dict)  # 检查完成后的文件信息
    error_signal = pyqtSignal(str)  # 全局错误信息
    
    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.is_running = True
        
    def run(self):
        try:
            def progress_callback(percentage, file_path, error=None):
                if not self.is_running:
                    return
                
                file_name = os.path.basename(file_path)
                self.progress_signal.emit(percentage)
                self.file_progress_signal.emit(file_name, percentage, error or "")
            
            # 批量检查文件
            file_infos = ExcelInspector.batch_inspect_files(
                self.file_paths,
                progress_callback
            )
            
            # 发送检查结果
            if self.is_running:
                self.inspection_completed_signal.emit(file_infos)
                
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def stop(self):
        """停止检查"""
        self.is_running = False 