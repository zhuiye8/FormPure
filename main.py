import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, 
                            QLabel, QVBoxLayout, QHBoxLayout, QWidget, QComboBox,
                            QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                            QProgressBar, QCheckBox, QGroupBox, QGridLayout, 
                            QSplitter, QFrame, QStyleFactory, QToolButton, QStyle,
                            QTabWidget, QListWidget, QListWidgetItem, QStackedWidget,
                            QRadioButton, QSettings)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette

# 导入自定义模块
from ui.styles import STYLE_SHEET
from ui.column_selector import ColumnSelector
from ui.model_manager_widget import ModelManagerWidget
from ui.model_settings_widget import ModelSettingsWidget
from core.deduplication import deduplicate_dataframe
from core.batch_thread import BatchProcessingThread, ExcelInspectionThread
from core.model_manager import get_model_manager
from core.model_inference import get_model_service

# 工具线程
class DeduplicationThread(QThread):
    """单文件去重线程（批处理模式下不再使用此线程）"""
    progress_signal = pyqtSignal(int)
    completed_signal = pyqtSignal(pd.DataFrame, pd.DataFrame, int)
    error_signal = pyqtSignal(str)
    
    def __init__(self, file_path, key_columns, keep_option):
        super().__init__()
        self.file_path = file_path
        self.key_columns = key_columns
        self.keep_option = keep_option
        
    def run(self):
        try:
            # 读取Excel文件
            df_original = pd.read_excel(self.file_path)
            total_rows = len(df_original)
            
            # 进度通知
            self.progress_signal.emit(30)
            
            # 执行去重操作 - 使用核心模块
            df_deduplicated = deduplicate_dataframe(
                df_original, 
                self.key_columns, 
                self.keep_option
            )
            
            # 进度通知
            self.progress_signal.emit(80)
            
            duplicates_removed = total_rows - len(df_deduplicated)
            
            # 发出完成信号
            self.completed_signal.emit(df_original, df_deduplicated, duplicates_removed)
            
        except Exception as e:
            self.error_signal.emit(str(e))

# 主应用窗口
class ExcelDeduplicationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        # 批处理相关的属性
        self.batch_files = []
        self.batch_thread = None
        self.batch_results = {}
        self.inspection_thread = None
        self.file_infos = {}  # 文件信息字典，存储每个文件的工作表和列
        
        self.initUI()
        
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle('Excel去重工具')
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet(STYLE_SHEET)

        # 创建主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建选项卡小部件
        tab_widget = QTabWidget()
        
        # 创建批处理选项卡
        batch_processing_tab = QWidget()
        self.setup_batch_processing_tab(batch_processing_tab)
        
        # 创建模型管理选项卡
        model_management_tab = self.create_model_management_tab()
        
        # 创建模型设置选项卡
        model_settings_tab = self.create_model_settings_tab()
        
        # 将选项卡添加到选项卡小部件
        tab_widget.addTab(batch_processing_tab, "批量处理")
        tab_widget.addTab(model_management_tab, "模型管理")
        tab_widget.addTab(model_settings_tab, "模型设置")
        
        # 添加选项卡小部件到主布局
        main_layout.addWidget(tab_widget)
        
        # 设置主窗口部件
        self.setCentralWidget(main_widget)
    
    def setup_batch_processing_tab(self, tab_widget):
        """设置批处理选项卡，使用步骤式分页面的方式"""
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(15)
        
        # 顶部步骤指示区域
        steps_widget = QWidget()
        steps_layout = QHBoxLayout(steps_widget)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建步骤按钮
        self.step_buttons = []
        
        step1_btn = QPushButton("1. 选择文件")
        step1_btn.setCheckable(True)
        step1_btn.setChecked(True)
        step1_btn.clicked.connect(lambda: self.switch_to_step(0))
        
        step2_btn = QPushButton("2. 选择列")
        step2_btn.setCheckable(True)
        step2_btn.clicked.connect(lambda: self.switch_to_step(1))
        
        step3_btn = QPushButton("3. 预览结果")
        step3_btn.setCheckable(True)
        step3_btn.clicked.connect(lambda: self.switch_to_step(2))
        
        step4_btn = QPushButton("4. 执行去重")
        step4_btn.setCheckable(True)
        step4_btn.clicked.connect(lambda: self.switch_to_step(3))
        
        self.step_buttons = [step1_btn, step2_btn, step3_btn, step4_btn]
        
        # 设置步骤按钮样式
        for btn in self.step_buttons:
            btn.setMinimumWidth(150)
            steps_layout.addWidget(btn)
        
        # 创建堆叠式页面容器
        self.steps_stack = QStackedWidget()
        
        # 第一步：选择文件页面
        file_selection_page = self.create_file_selection_page()
        
        # 第二步：选择列页面
        column_selection_page = self.create_column_selection_page()
        
        # 第三步：预览结果页面
        preview_page = self.create_preview_page()
        
        # 第四步：执行去重页面
        execution_page = self.create_execution_page()
        
        # 添加页面到堆叠式容器
        self.steps_stack.addWidget(file_selection_page)
        self.steps_stack.addWidget(column_selection_page)
        self.steps_stack.addWidget(preview_page)
        self.steps_stack.addWidget(execution_page)
        
        # 底部导航按钮区域
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        self.prev_step_btn = QPushButton("上一步")
        self.prev_step_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft))
        self.prev_step_btn.clicked.connect(self.go_to_prev_step)
        self.prev_step_btn.setEnabled(False)  # 第一步不能返回
        
        self.next_step_btn = QPushButton("下一步")
        self.next_step_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight))
        self.next_step_btn.clicked.connect(self.go_to_next_step)
        
        nav_layout.addStretch(1)
        nav_layout.addWidget(self.prev_step_btn)
        nav_layout.addWidget(self.next_step_btn)
        
        # 添加所有组件到主布局
        layout.addWidget(steps_widget)
        layout.addWidget(self.steps_stack, 1)
        layout.addWidget(nav_widget)
        
        # 初始化为第一步
        self.current_step = 0
        self.update_step_buttons()
        
    def create_file_selection_page(self):
        """创建第一步：选择文件页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 文件选择区域
        file_group = QGroupBox('文件选择')
        file_layout = QVBoxLayout()
        file_layout.setContentsMargins(15, 20, 15, 15)
        file_layout.setSpacing(10)
        
        # 文件列表
        self.batch_file_list = QListWidget()
        self.batch_file_list.setAlternatingRowColors(True)
        self.batch_file_list.setSelectionMode(QListWidget.ExtendedSelection)  # 允许多选
        self.batch_file_list.itemSelectionChanged.connect(self.update_remove_button_state)  # 添加选择变化信号连接
        
        # 文件选择按钮
        buttons_layout = QHBoxLayout()
        
        self.add_files_button = QPushButton('添加文件')
        self.add_files_button.setIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.add_files_button.clicked.connect(self.add_batch_files)
        
        self.add_dir_button = QPushButton('添加目录')
        self.add_dir_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.add_dir_button.clicked.connect(self.add_directory)
        
        self.clear_files_button = QPushButton('清空列表')
        self.clear_files_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton))
        self.clear_files_button.clicked.connect(self.clear_batch_files)
        
        self.remove_file_button = QPushButton('删除选中')
        self.remove_file_button.setIcon(QApplication.style().standardIcon(QStyle.SP_TrashIcon))
        self.remove_file_button.clicked.connect(self.remove_selected_files)
        self.remove_file_button.setEnabled(False)  # 默认禁用
        
        self.inspect_files_button = QPushButton('检查文件')
        self.inspect_files_button.setIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.inspect_files_button.clicked.connect(self.inspect_batch_files)
        
        buttons_layout.addWidget(self.add_files_button)
        buttons_layout.addWidget(self.add_dir_button)
        buttons_layout.addWidget(self.clear_files_button)
        buttons_layout.addWidget(self.remove_file_button)
        buttons_layout.addWidget(self.inspect_files_button)
        buttons_layout.addStretch(1)
        
        # 状态显示
        self.file_status_label = QLabel('请添加Excel文件并点击"检查文件"按钮')
        
        file_layout.addWidget(self.batch_file_list)
        file_layout.addLayout(buttons_layout)
        file_layout.addWidget(self.file_status_label)
        file_group.setLayout(file_layout)
        
        # 添加到页面
        layout.addWidget(file_group)
        layout.addStretch(1)
        
        return page
        
    def create_column_selection_page(self):
        """创建第二步：选择列页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 批处理设置区域
        settings_group = QGroupBox('去重设置')
        settings_layout = QVBoxLayout()
        settings_layout.setContentsMargins(15, 20, 15, 15)
        
        # 保留重复项设置
        keep_frame = QFrame()
        keep_layout = QHBoxLayout(keep_frame)
        keep_layout.setContentsMargins(0, 0, 0, 0)
        
        keep_label = QLabel('保留重复项:')
        self.keep_option_combo = QComboBox()
        self.keep_option_combo.addItem('保留首次出现的记录', 'first')
        self.keep_option_combo.addItem('保留最后出现的记录', 'last')
        self.keep_option_combo.currentIndexChanged.connect(self.update_column_selector_keep_option)
        
        keep_layout.addWidget(keep_label)
        keep_layout.addWidget(self.keep_option_combo)
        keep_layout.addStretch(1)
        
        # 模型相似度设置
        model_frame = QFrame()
        model_layout = QHBoxLayout(model_frame)
        model_layout.setContentsMargins(0, 0, 0, 0)
        
        self.use_model_check = QCheckBox('使用模型进行相似度计算')
        self.use_model_check.setToolTip('启用后将使用深度学习模型计算文本相似度，提高准确性但会降低处理速度')
        
        # 检查模型功能是否启用
        settings = QSettings("ExcelDeduplication", "ModelSettings")
        enable_model = settings.value("enable_model", False, type=bool)
        
        self.use_model_check.setChecked(enable_model)
        self.use_model_check.setEnabled(enable_model)  # 如果全局设置禁用，则禁用勾选框
        
        # 如果模型功能被禁用，添加提示
        if not enable_model:
            self.use_model_check.setToolTip('模型功能已在设置中被禁用，请在"模型设置"选项卡中启用')
        
        # 模型选择下拉框
        model_select_label = QLabel('使用模型:')
        self.model_select_combo = QComboBox()
        self.update_model_select_combo()
        self.model_select_combo.setEnabled(enable_model and self.use_model_check.isChecked())
        
        # 连接信号
        self.use_model_check.toggled.connect(self.on_use_model_toggled)
        
        model_layout.addWidget(self.use_model_check)
        model_layout.addStretch(1)
        model_layout.addWidget(model_select_label)
        model_layout.addWidget(self.model_select_combo)
        
        # 列选择组件
        self.column_selector = ColumnSelector()
        self.column_selector.on_config_changed.connect(self.on_dedup_config_changed)
        
        # 将所有组件添加到设置区域
        settings_layout.addWidget(keep_frame)
        settings_layout.addWidget(model_frame)
        settings_layout.addWidget(self.column_selector)
        settings_group.setLayout(settings_layout)
        
        # 添加到页面
        layout.addWidget(settings_group)
        
        return page
        
    def create_preview_page(self):
        """创建第三步：预览结果页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 预览控制区域
        control_group = QGroupBox('预览控制')
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(15, 20, 15, 15)
        
        # 文件选择下拉框
        file_label = QLabel('选择文件:')
        self.preview_file_combo = QComboBox()
        self.preview_file_combo.currentIndexChanged.connect(self.update_sheet_combo)
        
        # 工作表选择下拉框
        sheet_label = QLabel('选择工作表:')
        self.preview_sheet_combo = QComboBox()
        self.preview_sheet_combo.currentIndexChanged.connect(self.load_preview_data)
        
        # 生成预览按钮
        self.generate_preview_btn = QPushButton('生成预览')
        self.generate_preview_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        self.generate_preview_btn.clicked.connect(self.generate_deduplication_preview)
        
        control_layout.addWidget(file_label)
        control_layout.addWidget(self.preview_file_combo, 1)
        control_layout.addWidget(sheet_label)
        control_layout.addWidget(self.preview_sheet_combo, 1)
        control_layout.addWidget(self.generate_preview_btn)
        
        control_group.setLayout(control_layout)
        
        # 预览结果区域
        preview_group = QGroupBox('数据预览')
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(15, 20, 15, 15)
        
        # 预览结果标签
        self.preview_stats_label = QLabel('请生成预览')
        
        # 预览选项
        preview_options = QFrame()
        preview_options_layout = QHBoxLayout(preview_options)
        preview_options_layout.setContentsMargins(0, 0, 0, 0)
        
        self.show_all_data_radio = QRadioButton('显示所有数据')
        self.show_all_data_radio.setChecked(True)
        self.show_all_data_radio.toggled.connect(self.update_preview_display)
        
        self.show_duplicates_radio = QRadioButton('只显示重复数据（将被移除）')
        self.show_duplicates_radio.toggled.connect(self.update_preview_display)
        
        self.show_unique_radio = QRadioButton('只显示唯一数据（将被保留）')
        self.show_unique_radio.toggled.connect(self.update_preview_display)
        
        preview_options_layout.addWidget(self.show_all_data_radio)
        preview_options_layout.addWidget(self.show_duplicates_radio)
        preview_options_layout.addWidget(self.show_unique_radio)
        preview_options_layout.addStretch(1)
        
        # 数据表格
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        preview_layout.addWidget(self.preview_stats_label)
        preview_layout.addWidget(preview_options)
        preview_layout.addWidget(self.preview_table, 1)
        
        preview_group.setLayout(preview_layout)
        
        # 添加到页面
        layout.addWidget(control_group)
        layout.addWidget(preview_group, 1)
        
        return page
        
    def create_execution_page(self):
        """创建第四步：执行去重页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 输出设置区域
        output_group = QGroupBox('输出设置')
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(15, 20, 15, 15)
        output_layout.setSpacing(10)
        
        # 输出目录设置
        output_dir_frame = QFrame()
        output_dir_layout = QHBoxLayout(output_dir_frame)
        output_dir_layout.setContentsMargins(0, 0, 0, 0)
        
        output_dir_label = QLabel('输出目录:')
        self.output_dir_edit = QLabel('未选择')
        self.output_dir_edit.setWordWrap(True)
        
        self.browse_output_button = QPushButton('选择')
        self.browse_output_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.browse_output_button.clicked.connect(self.browse_output_dir)
        
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_edit, 1)
        output_dir_layout.addWidget(self.browse_output_button)
        
        # 输出文件后缀设置
        suffix_frame = QFrame()
        suffix_layout = QHBoxLayout(suffix_frame)
        suffix_layout.setContentsMargins(0, 0, 0, 0)
        
        suffix_label = QLabel('输出文件后缀:')
        self.suffix_input = QComboBox()
        self.suffix_input.setEditable(True)
        self.suffix_input.addItems(['_去重', '_dedup', '_cleaned', '_no_duplicates'])
        
        suffix_layout.addWidget(suffix_label)
        suffix_layout.addWidget(self.suffix_input, 1)
        
        # 添加到输出设置布局
        output_layout.addWidget(output_dir_frame)
        output_layout.addWidget(suffix_frame)
        
        output_group.setLayout(output_layout)
        
        # 执行区域
        execution_group = QGroupBox('执行去重')
        execution_layout = QVBoxLayout()
        execution_layout.setContentsMargins(15, 20, 15, 15)
        
        # 执行按钮
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        self.batch_start_button = QPushButton('开始批量去重')
        self.batch_start_button.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.batch_start_button.clicked.connect(self.start_batch_processing)
        self.batch_start_button.setEnabled(False)  # 默认禁用，需要先检查文件
        
        self.batch_stop_button = QPushButton('停止')
        self.batch_stop_button.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.batch_stop_button.clicked.connect(self.stop_batch_processing)
        self.batch_stop_button.setEnabled(False)
        
        buttons_layout.addWidget(self.batch_start_button)
        buttons_layout.addWidget(self.batch_stop_button)
        buttons_layout.addStretch(1)
        
        # 状态显示
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # 当前文件和进度
        file_status_frame = QFrame()
        file_status_layout = QHBoxLayout(file_status_frame)
        file_status_layout.setContentsMargins(0, 0, 0, 0)
        
        file_status_label = QLabel('当前文件:')
        self.batch_current_file_label = QLabel('无')
        
        file_status_layout.addWidget(file_status_label)
        file_status_layout.addWidget(self.batch_current_file_label, 1)
        
        # 批处理总进度
        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setRange(0, 100)
        self.batch_progress_bar.setValue(0)
        
        # 结果统计
        self.batch_stats_label = QLabel('未开始处理')
        
        # 结果列表
        self.batch_results_list = QListWidget()
        self.batch_results_list.setAlternatingRowColors(True)
        
        status_layout.addWidget(file_status_frame)
        status_layout.addWidget(self.batch_progress_bar)
        status_layout.addWidget(self.batch_stats_label)
        status_layout.addWidget(self.batch_results_list, 1)
        
        execution_layout.addWidget(buttons_frame)
        execution_layout.addWidget(status_frame, 1)
        
        execution_group.setLayout(execution_layout)
        
        # 添加到页面
        layout.addWidget(output_group)
        layout.addWidget(execution_group, 1)
        
        return page
        
    def switch_to_step(self, step_index):
        """切换到指定步骤"""
        # 检查步骤转换的有效性
        if step_index == 1 and not self.file_infos:  # 如果要切换到第二步但没有检查文件
            QMessageBox.warning(self, '警告', '请先添加文件并点击"检查文件"按钮')
            self.step_buttons[0].setChecked(True)  # 保持在第一步
            return
            
        if step_index == 2:  # 如果要切换到第三步，准备预览数据
            dedup_configs = self.column_selector.get_deduplication_configs()
            if not dedup_configs:
                QMessageBox.warning(self, '警告', '请至少选择一个列作为去重依据')
                self.step_buttons[1].setChecked(True)  # 保持在第二步
                return
            self.prepare_preview_data()
            
        # 切换步骤
        self.current_step = step_index
        self.steps_stack.setCurrentIndex(step_index)
        self.update_step_buttons()
        
    def update_step_buttons(self):
        """更新步骤按钮状态"""
        for i, btn in enumerate(self.step_buttons):
            btn.setChecked(i == self.current_step)
            
        # 更新导航按钮
        self.prev_step_btn.setEnabled(self.current_step > 0)
        self.next_step_btn.setEnabled(self.current_step < len(self.step_buttons) - 1)
        
    def go_to_prev_step(self):
        """转到上一步"""
        if self.current_step > 0:
            self.switch_to_step(self.current_step - 1)
            
    def go_to_next_step(self):
        """转到下一步"""
        if self.current_step < len(self.step_buttons) - 1:
            self.switch_to_step(self.current_step + 1)

    def add_batch_files(self):
        """添加批量处理文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            '选择Excel文件',
            '',
            'Excel文件 (*.xlsx *.xls)'
        )
        
        if file_paths:
            # 添加到文件列表
            for file_path in file_paths:
                if file_path not in self.batch_files:
                    self.batch_files.append(file_path)
                    item = QListWidgetItem(os.path.basename(file_path))
                    item.setToolTip(file_path)
                    self.batch_file_list.addItem(item)
    
    def add_directory(self):
        """添加目录中的所有Excel文件"""
        directory = QFileDialog.getExistingDirectory(
            self,
            '选择包含Excel文件的目录',
            ''
        )
        
        if directory:
            # 获取目录中所有Excel文件
            excel_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith(('.xlsx', '.xls')):
                        excel_files.append(os.path.join(root, file))
            
            # 添加到文件列表
            if excel_files:
                for file_path in excel_files:
                    if file_path not in self.batch_files:
                        self.batch_files.append(file_path)
                        item = QListWidgetItem(os.path.basename(file_path))
                        item.setToolTip(file_path)
                        self.batch_file_list.addItem(item)
                
                # 提示用户
                QMessageBox.information(
                    self, 
                    '添加成功', 
                    f'已添加 {len(excel_files)} 个Excel文件'
                )
            else:
                QMessageBox.warning(
                    self, 
                    '未找到文件', 
                    f'在所选目录中未找到Excel文件'
                )
                
        # 更新删除按钮状态
        self.update_remove_button_state()
        
        # 如果已经检查过文件，则需要清空之前的检查结果
        if self.file_infos:
            self.file_infos = {}
            self.column_selector.clear()
            self.batch_start_button.setEnabled(False)

    def remove_selected_files(self):
        """删除选中的文件"""
        selected_items = self.batch_file_list.selectedItems()
        if not selected_items:
            return
            
        # 移除选中的文件
        for item in selected_items:
            file_path = item.toolTip()
            row = self.batch_file_list.row(item)
            
            # 从列表控件中移除
            self.batch_file_list.takeItem(row)
            
            # 从文件列表中移除
            if file_path in self.batch_files:
                self.batch_files.remove(file_path)
                
            # 从文件信息字典中移除
            if file_path in self.file_infos:
                del self.file_infos[file_path]
        
        # 更新列选择器
        if self.file_infos:
            self.column_selector.load_file_infos(self.file_infos)
        else:
            self.column_selector.clear()
            self.batch_start_button.setEnabled(False)
            
        # 更新删除按钮状态
        self.update_remove_button_state()
        
    def update_remove_button_state(self):
        """更新删除按钮状态"""
        has_selected = len(self.batch_file_list.selectedItems()) > 0
        self.remove_file_button.setEnabled(has_selected)
        
    def clear_batch_files(self):
        """清空批处理文件列表"""
        self.batch_files = []
        self.batch_file_list.clear()
        self.file_infos = {}
        self.column_selector.clear()
        self.batch_start_button.setEnabled(False)
        self.remove_file_button.setEnabled(False)
    
    def browse_output_dir(self):
        """选择批处理输出目录"""
        output_dir = QFileDialog.getExistingDirectory(
            self,
            '选择输出目录',
            ''
        )
        
        if output_dir:
            self.output_dir_edit.setText(output_dir)
    
    def start_batch_processing(self):
        """开始批处理"""
        # 检查是否有文件
        if not self.batch_files:
            QMessageBox.warning(self, "错误", "请先添加要处理的文件")
            return
        
        # 检查是否配置了去重列
        if not self.column_selector.has_selections():
            QMessageBox.warning(self, "错误", "请至少为一个工作表选择去重依据列")
            return
        
        # 获取输出目录
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            # 如果未指定输出目录，弹出选择对话框
            output_dir = QFileDialog.getExistingDirectory(
                self, 
                "选择输出目录",
                os.path.dirname(self.batch_files[0]) if self.batch_files else ""
            )
            
            if not output_dir:
                return  # 用户取消了选择
                
            self.output_dir_edit.setText(output_dir)
        
        # 获取去重配置
        dedup_configs = self.column_selector.get_deduplication_configs()
        keep_option = self.keep_option_combo.currentData()
        
        # 获取模型设置
        use_model = self.use_model_check.isChecked()
        model_id = self.model_select_combo.currentData() if use_model else None
        
        # 更新配置中的模型设置
        for file_path, file_config in dedup_configs.items():
            for sheet_name, sheet_config in file_config.items():
                sheet_config['keep_option'] = keep_option
                sheet_config['use_model'] = use_model
                sheet_config['model_id'] = model_id
        
        # 禁用界面元素
        self.batch_start_button.setEnabled(False)
        self.batch_stop_button.setEnabled(True)
        
        # 创建并启动处理线程
        self.batch_thread = BatchProcessingThread(self.batch_files, dedup_configs)
        
        # 连接信号
        self.batch_thread.progress_signal.connect(self.update_batch_progress)
        self.batch_thread.file_progress_signal.connect(self.update_batch_file_progress)
        self.batch_thread.file_completed_signal.connect(self.handle_batch_file_completed)
        self.batch_thread.batch_completed_signal.connect(self.handle_batch_completed)
        self.batch_thread.error_signal.connect(self.handle_batch_error)
        
        # 开始处理
        self.batch_thread.start()
        
        # 清空结果区域
        self.batch_results_list.clear()
        
        # 显示处理中消息
        self.batch_stats_label.setText("批处理进行中...")
        self.batch_stats_label.setStyleSheet("color: blue;")
        
        # 更新进度条
        self.batch_progress_bar.setValue(0)
        self.batch_progress_bar.setVisible(True)
    
    def stop_batch_processing(self):
        """停止批量处理"""
        if self.batch_thread and self.batch_thread.isRunning():
            # 停止线程
            self.batch_thread.stop()
            self.batch_thread.wait()  # 等待线程结束
            
            # 更新状态
            self.batch_stats_label.setText('处理已中止')
            
            # 恢复按钮状态
            self.batch_start_button.setEnabled(True)
            self.batch_stop_button.setEnabled(False)
            self.add_files_button.setEnabled(True)
            self.add_dir_button.setEnabled(True)
            self.clear_files_button.setEnabled(True)
            self.inspect_files_button.setEnabled(True)
            self.update_remove_button_state()  # 根据选择状态更新删除按钮
    
    def update_batch_progress(self, progress):
        """更新批处理总进度"""
        self.batch_progress_bar.setValue(progress)
    
    def update_batch_file_progress(self, file_name, progress):
        """更新当前处理文件的进度"""
        self.batch_current_file_label.setText(file_name)
    
    def handle_batch_file_completed(self, success, file_path, error):
        """处理单个文件完成的事件"""
        file_name = os.path.basename(file_path)
        
        # 添加到结果列表
        if success:
            item = QListWidgetItem(f"✓ {file_name}")
            item.setForeground(QColor('#4CAF50'))  # 绿色
        else:
            item = QListWidgetItem(f"✗ {file_name} - 错误: {error}")
            item.setForeground(QColor('#F44336'))  # 红色
            
        item.setToolTip(file_path)
        self.batch_results_list.addItem(item)
        self.batch_results_list.scrollToBottom()
    
    def handle_batch_completed(self, report):
        """处理批处理完成的事件"""
        # 保存结果
        try:
            if report['success_count'] > 0:
                # 获取输出目录
                output_dir = self.output_dir_edit.text()
                
                # 获取文件后缀
                file_suffix = self.suffix_input.currentText()
                
                # 保存处理后的文件
                processor = self.batch_thread.processor
                saved_files, errors = processor.save_results(output_dir, file_suffix)
                
                # 更新结果列表
                for original, saved in saved_files:
                    item = QListWidgetItem(f"📄 已保存: {os.path.basename(saved)}")
                    item.setToolTip(saved)
                    self.batch_results_list.addItem(item)
                
                for file_path, error in errors:
                    item = QListWidgetItem(f"❌ 保存失败: {os.path.basename(file_path)} - {error}")
                    item.setForeground(QColor('#F44336'))  # 红色
                    item.setToolTip(file_path)
                    self.batch_results_list.addItem(item)
        except Exception as e:
            self.handle_batch_error(f"保存结果时出错: {str(e)}")
        
        # 更新统计信息
        stats_text = (
            f"处理完成: 共 {report['total_files']} 个文件, "
            f"成功 {report['success_count']} 个, "
            f"失败 {report['error_count']} 个, "
            f"共处理 {report['total_rows_processed']} 行数据, "
            f"移除 {report['total_duplicates_removed']} 行重复数据"
        )
        self.batch_stats_label.setText(stats_text)
        
        # 恢复按钮状态
        self.batch_start_button.setEnabled(True)
        self.batch_stop_button.setEnabled(False)
        
        # 显示完成消息
        QMessageBox.information(
            self,
            '批处理完成',
            f"批量去重处理已完成!\n\n"
            f"处理文件数: {report['total_files']}\n"
            f"成功: {report['success_count']}\n"
            f"失败: {report['error_count']}\n"
            f"总处理行数: {report['total_rows_processed']}\n"
            f"总移除重复行: {report['total_duplicates_removed']}"
        )
    
    def handle_batch_error(self, error_message):
        """处理批处理过程中的错误"""
        # 区分当前所在的步骤
        if self.current_step == 0:  # 文件选择页面
            self.file_status_label.setText(f"错误: {error_message}")
            
            # 启用按钮
            self.add_files_button.setEnabled(True)
            self.add_dir_button.setEnabled(True)
            self.clear_files_button.setEnabled(True)
            self.inspect_files_button.setEnabled(True)
            self.update_remove_button_state()
        elif self.current_step == 3:  # 执行去重页面
            # 添加到结果列表
            item = QListWidgetItem(f"⚠️ 错误: {error_message}")
            item.setForeground(QColor('#F44336'))  # 红色
            self.batch_results_list.addItem(item)
            
            # 更新状态
            self.batch_stats_label.setText(f"处理出错: {error_message}")
            
            # 恢复按钮状态
            self.batch_start_button.setEnabled(True)
            self.batch_stop_button.setEnabled(False)
        
        # 显示错误消息
        QMessageBox.critical(self, '错误', f"处理过程中出错: {error_message}")

    def inspect_batch_files(self):
        """检查批量处理文件，获取所有工作表和列信息"""
        if not self.batch_files:
            QMessageBox.warning(self, '警告', '请先添加文件')
            return
            
        # 禁用按钮
        self.add_files_button.setEnabled(False)
        self.add_dir_button.setEnabled(False)
        self.clear_files_button.setEnabled(False)
        self.inspect_files_button.setEnabled(False)
        self.remove_file_button.setEnabled(False)
        
        # 更新状态
        self.file_status_label.setText('正在检查文件...')
        
        # 创建并启动检查线程
        self.inspection_thread = ExcelInspectionThread(self.batch_files)
        
        # 连接信号
        self.inspection_thread.progress_signal.connect(lambda x: self.file_status_label.setText(f'检查进度: {x}%'))
        self.inspection_thread.file_progress_signal.connect(self.update_file_inspection_progress)
        self.inspection_thread.inspection_completed_signal.connect(self.handle_inspection_completed)
        self.inspection_thread.error_signal.connect(self.handle_batch_error)
        
        # 启动线程
        self.inspection_thread.start()
        
    def update_file_inspection_progress(self, file_name, progress, error):
        """更新文件检查进度"""
        self.file_status_label.setText(f'正在检查: {file_name} ({progress}%)')
        
    def handle_inspection_completed(self, file_infos):
        """处理文件检查完成"""
        self.file_infos = file_infos
        
        # 加载文件信息到列选择器
        self.column_selector.load_file_infos(file_infos)
        
        # 设置一个默认的保留选项
        self.update_column_selector_keep_option()
        
        # 更新状态
        total_files = len(file_infos)
        total_sheets = sum(len(info.sheets) for info in file_infos.values())
        
        # 启用按钮
        self.add_files_button.setEnabled(True)
        self.add_dir_button.setEnabled(True)
        self.clear_files_button.setEnabled(True)
        self.inspect_files_button.setEnabled(True)
        self.update_remove_button_state()  # 根据选择状态更新删除按钮
        
        # 更新状态信息
        self.file_status_label.setText(f'检查完成: 共 {total_files} 个文件，{total_sheets} 个工作表')
        
        # 自动进入下一步
        QMessageBox.information(self, '文件检查完成', 
                              f'已成功检查 {total_files} 个文件，包含 {total_sheets} 个工作表。\n现在可以进行去重列选择。')
        
        # 使用计时器延迟切换，确保消息框关闭后再切换
        QTimer.singleShot(500, lambda: self.switch_to_step(1))

    def update_column_selector_keep_option(self):
        """根据当前选择的保留选项更新列选择器配置"""
        keep_option = self.keep_option_combo.currentData()
        self.column_selector.set_keep_option(keep_option)
    
    def update_model_select_combo(self):
        """更新模型选择下拉框"""
        self.model_select_combo.clear()
        
        # 获取所有已下载的模型
        model_manager = get_model_manager()
        models = model_manager.get_downloaded_models()
        
        if models:
            # 添加所有可用模型
            for model in models:
                self.model_select_combo.addItem(model.name, model.model_id)
        else:
            # 如果没有可用模型，添加提示项
            self.model_select_combo.addItem("未找到可用模型", "")
            self.model_select_combo.setEnabled(False)
    
    def on_use_model_toggled(self, checked):
        """模型使用选项变更处理"""
        self.model_select_combo.setEnabled(checked)

    def on_dedup_config_changed(self, configs):
        """处理去重配置变化"""
        # 配置变化时，可以在这里更新UI或存储配置
        has_valid_config = bool(configs)
        self.batch_start_button.setEnabled(has_valid_config)

    def create_vertical_layout(self, widgets, stretch_index=-1):
        """创建一个垂直布局，并添加小部件
        
        Args:
            widgets: 要添加的小部件列表
            stretch_index: 指定哪个索引的小部件应该拉伸，默认为-1（无）
            
        Returns:
            QVBoxLayout: 垂直布局
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        for i, widget in enumerate(widgets):
            if i == stretch_index:
                layout.addWidget(widget, 1)
            else:
                layout.addWidget(widget)
                
        return layout

    def prepare_preview_data(self):
        """准备预览数据，填充文件和工作表下拉框"""
        self.preview_file_combo.clear()
        self.preview_sheet_combo.clear()
        
        # 获取所选配置
        dedup_configs = self.column_selector.get_deduplication_configs()
        if not dedup_configs:
            return
            
        # 填充文件下拉框
        for file_path in dedup_configs.keys():
            file_name = os.path.basename(file_path)
            self.preview_file_combo.addItem(file_name, file_path)
            
        # 初始化工作表下拉框
        if self.preview_file_combo.count() > 0:
            self.update_sheet_combo()
            
    def update_sheet_combo(self):
        """根据选择的文件更新工作表下拉框"""
        self.preview_sheet_combo.clear()
        
        # 获取选中的文件路径
        current_index = self.preview_file_combo.currentIndex()
        if current_index < 0:
            return
            
        file_path = self.preview_file_combo.itemData(current_index)
        if not file_path or file_path not in self.file_infos:
            return
            
        # 获取该文件的去重配置
        dedup_configs = self.column_selector.get_deduplication_configs()
        if file_path not in dedup_configs:
            return
            
        # 获取配置了去重的工作表
        file_config = dedup_configs[file_path]
        for sheet_name in file_config.keys():
            self.preview_sheet_combo.addItem(sheet_name)
            
    def load_preview_data(self):
        """加载选中工作表的数据到预览表格"""
        # 清空预览表格
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        
        # 获取当前选择
        file_index = self.preview_file_combo.currentIndex()
        sheet_index = self.preview_sheet_combo.currentIndex()
        
        if file_index < 0 or sheet_index < 0:
            self.preview_stats_label.setText('请选择文件和工作表')
            return
            
        file_path = self.preview_file_combo.itemData(file_index)
        sheet_name = self.preview_sheet_combo.currentText()
        
        # 检查是否已有预览数据
        if hasattr(self, 'preview_data') and file_path in self.preview_data and sheet_name in self.preview_data[file_path]:
            self.display_preview_data(file_path, sheet_name)
        else:
            self.preview_stats_label.setText('请点击"生成预览"按钮')
            
    def generate_deduplication_preview(self):
        """生成去重预览"""
        # 获取当前选择
        file_index = self.preview_file_combo.currentIndex()
        sheet_index = self.preview_sheet_combo.currentIndex()
        
        if file_index < 0 or sheet_index < 0:
            QMessageBox.warning(self, '警告', '请选择文件和工作表')
            return
            
        file_path = self.preview_file_combo.itemData(file_index)
        sheet_name = self.preview_sheet_combo.currentText()
        
        # 获取去重配置
        dedup_configs = self.column_selector.get_deduplication_configs()
        if file_path not in dedup_configs or sheet_name not in dedup_configs[file_path]:
            QMessageBox.warning(self, '警告', '所选文件或工作表没有有效的去重配置')
            return
            
        sheet_config = dedup_configs[file_path][sheet_name]
        key_columns = sheet_config.get('key_columns', [])
        keep_option = sheet_config.get('keep_option', 'first')
        
        if not key_columns:
            QMessageBox.warning(self, '警告', '请为所选工作表选择至少一个去重列')
            return
            
        # 显示处理中状态
        self.preview_stats_label.setText('正在生成预览...')
        QApplication.processEvents()
        
        try:
            # 读取Excel数据
            df_original = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # 标记重复项
            # 注：keep=False表示将所有重复项标记为True
            df_duplicated = df_original.copy()
            duplicate_mask = df_duplicated.duplicated(subset=key_columns, keep=False)
            
            # 找出要保留的行
            if keep_option == 'first':
                keep_mask = ~df_duplicated.duplicated(subset=key_columns, keep='first')
            elif keep_option == 'last':
                keep_mask = ~df_duplicated.duplicated(subset=key_columns, keep='last')
            else:  # False - 删除所有重复项
                keep_mask = ~duplicate_mask
                
            # 添加标记列
            df_with_marks = df_original.copy()
            df_with_marks['_is_duplicate'] = duplicate_mask
            df_with_marks['_will_keep'] = keep_mask
            
            # 初始化或更新预览数据
            if not hasattr(self, 'preview_data'):
                self.preview_data = {}
                
            if file_path not in self.preview_data:
                self.preview_data[file_path] = {}
                
            # 存储预览数据
            self.preview_data[file_path][sheet_name] = {
                'original': df_original,
                'with_marks': df_with_marks,
                'duplicates': df_with_marks[duplicate_mask],
                'to_keep': df_with_marks[keep_mask],
                'to_remove': df_with_marks[~keep_mask],
                'key_columns': key_columns,
                'keep_option': keep_option
            }
            
            # 显示预览
            self.display_preview_data(file_path, sheet_name)
            
        except Exception as e:
            self.preview_stats_label.setText(f'生成预览出错: {str(e)}')
            QMessageBox.critical(self, '错误', f'生成预览时出错：{str(e)}')
            
    def display_preview_data(self, file_path, sheet_name):
        """显示预览数据"""
        if not hasattr(self, 'preview_data') or file_path not in self.preview_data or sheet_name not in self.preview_data[file_path]:
            self.preview_stats_label.setText('没有可用的预览数据')
            return
            
        preview_info = self.preview_data[file_path][sheet_name]
        
        # 根据选择的显示模式选择要显示的数据
        if self.show_all_data_radio.isChecked():
            display_df = preview_info['with_marks']
            display_mode = "全部"
        elif self.show_duplicates_radio.isChecked():
            display_df = preview_info['duplicates']
            display_mode = "重复数据"
        else:  # 显示将保留的行
            display_df = preview_info['to_keep']
            display_mode = "唯一数据"
            
        # 计算统计信息
        total_rows = len(preview_info['original'])
        duplicate_rows = len(preview_info['duplicates'])
        unique_rows = total_rows - duplicate_rows
        to_remove_rows = len(preview_info['to_remove'])
        
        # 更新统计标签
        stats_text = (
            f"总行数: {total_rows} | "
            f"重复行数: {duplicate_rows} | "
            f"唯一行数: {unique_rows} | "
            f"将删除行数: {to_remove_rows} | "
            f"当前显示: {display_mode} ({len(display_df)}行)"
        )
        self.preview_stats_label.setText(stats_text)
        
        # 更新表格内容
        self.preview_table.clear()
        
        # 如果没有数据，直接返回
        if len(display_df) == 0:
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            return
            
        # 设置表格列
        columns = list(display_df.columns)
        if '_is_duplicate' in columns:
            columns.remove('_is_duplicate')
        if '_will_keep' in columns:
            columns.remove('_will_keep')
            
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setHorizontalHeaderLabels(columns)
        
        # 填充数据
        self.preview_table.setRowCount(len(display_df))
        
        for row_idx, (_, row_data) in enumerate(display_df.iterrows()):
            is_duplicate = row_data.get('_is_duplicate', False)
            will_keep = row_data.get('_will_keep', True)
            
            for col_idx, col_name in enumerate(columns):
                value = str(row_data[col_name])
                item = QTableWidgetItem(value)
                
                # 设置单元格样式
                if col_name in preview_info['key_columns']:
                    # 标记关键列
                    item.setBackground(QColor(230, 255, 230))  # 浅绿色
                
                if is_duplicate:
                    if will_keep:
                        # 将保留的重复项
                        item.setForeground(QColor(0, 120, 0))  # 深绿色
                    else:
                        # 将删除的重复项
                        item.setForeground(QColor(255, 0, 0))  # 红色
                        item.setBackground(QColor(255, 230, 230))  # 浅红色
                
                self.preview_table.setItem(row_idx, col_idx, item)
    
    def update_preview_display(self):
        """根据选择的显示选项更新预览显示"""
        # 获取当前选择
        file_index = self.preview_file_combo.currentIndex()
        sheet_index = self.preview_sheet_combo.currentIndex()
        
        if file_index < 0 or sheet_index < 0:
            return
            
        file_path = self.preview_file_combo.itemData(file_index)
        sheet_name = self.preview_sheet_combo.currentText()
        
        # 刷新显示
        self.display_preview_data(file_path, sheet_name)

    def create_model_management_tab(self):
        """创建模型管理选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建模型管理器组件
        self.model_manager_widget = ModelManagerWidget()
        
        # 添加到布局
        layout.addWidget(self.model_manager_widget)
        
        return tab
    
    def create_model_settings_tab(self):
        """创建模型设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建模型设置组件
        self.model_settings_widget = ModelSettingsWidget()
        
        # 添加到布局
        layout.addWidget(self.model_settings_widget)
        
        return tab

# 程序入口
def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName('Excel去重工具')
    app.setApplicationVersion('1.0.0')
    
    # 设置样式
    app.setStyle('Fusion')
    
    window = ExcelDeduplicationTool()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 