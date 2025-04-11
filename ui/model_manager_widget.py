"""
模型管理界面组件
提供模型下载、删除和配置功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QListWidget, QListWidgetItem, QProgressBar,
                            QMessageBox, QDialog, QFormLayout, QLineEdit, QCheckBox,
                            QComboBox, QTabWidget, QGroupBox, QSpinBox, QDoubleSpinBox,
                            QFrame, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QFont

# 导入自定义模块
from core.model_manager import ModelInfo, get_model_manager
from core.model_inference import get_model_service

class ModelListItem(QListWidgetItem):
    """模型列表项，展示模型信息"""
    
    def __init__(self, model_info: ModelInfo):
        """
        初始化模型列表项
        
        Args:
            model_info: 模型信息
        """
        super().__init__()
        self.model_info = model_info
        self.update_display()
    
    def update_display(self):
        """更新显示内容"""
        # 设置主文本
        status = "✓ 已下载" if self.model_info.is_downloaded else "未下载"
        self.setText(f"{self.model_info.name} ({status})")
        
        # 设置提示文本
        tooltip = (
            f"ID: {self.model_info.model_id}\n"
            f"版本: {self.model_info.version}\n"
            f"来源: {self.model_info.source}\n"
            f"大小: {self.model_info.size_mb} MB\n"
            f"描述: {self.model_info.description}\n"
            f"标签: {', '.join(self.model_info.tags)}"
        )
        self.setToolTip(tooltip)
        
        # 设置图标（可以根据模型类型或状态设置不同图标）
        # self.setIcon(QIcon("path/to/icon.png"))


class ModelDetailWidget(QWidget):
    """模型详细信息和操作组件"""
    
    # 自定义信号
    download_requested = pyqtSignal(str)  # model_id
    delete_requested = pyqtSignal(str)  # model_id
    
    def __init__(self, parent=None):
        """
        初始化模型详细信息组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self.model_info = None
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标题标签
        self.title_label = QLabel("模型详情")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        # 信息区域
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_frame.setStyleSheet("background-color: #f9f9f9; padding: 10px;")
        info_layout = QFormLayout(info_frame)
        
        self.name_label = QLabel("")
        self.id_label = QLabel("")
        self.version_label = QLabel("")
        self.source_label = QLabel("")
        self.size_label = QLabel("")
        self.status_label = QLabel("")
        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        
        info_layout.addRow("名称:", self.name_label)
        info_layout.addRow("ID:", self.id_label)
        info_layout.addRow("版本:", self.version_label)
        info_layout.addRow("来源:", self.source_label)
        info_layout.addRow("大小:", self.size_label)
        info_layout.addRow("状态:", self.status_label)
        info_layout.addRow("描述:", self.desc_label)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("下载模型")
        self.download_btn.clicked.connect(self.on_download_clicked)
        
        self.delete_btn = QPushButton("删除模型")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        
        buttons_layout.addWidget(self.download_btn)
        buttons_layout.addWidget(self.delete_btn)
        
        # 将组件添加到主布局
        layout.addWidget(self.title_label)
        layout.addWidget(info_frame)
        layout.addLayout(buttons_layout)
        layout.addStretch(1)
        
        # 初始状态
        self.update_ui_state(None)
    
    def set_model_info(self, model_info: ModelInfo):
        """
        设置要显示的模型信息
        
        Args:
            model_info: 模型信息
        """
        self.model_info = model_info
        self.update_ui_state(model_info)
    
    def update_ui_state(self, model_info: ModelInfo = None):
        """
        更新UI状态
        
        Args:
            model_info: 模型信息，如果为None则显示空状态
        """
        if model_info is None:
            self.name_label.setText("")
            self.id_label.setText("")
            self.version_label.setText("")
            self.source_label.setText("")
            self.size_label.setText("")
            self.status_label.setText("")
            self.desc_label.setText("")
            
            self.download_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return
        
        # 更新信息
        self.name_label.setText(model_info.name)
        self.id_label.setText(model_info.model_id)
        self.version_label.setText(model_info.version)
        self.source_label.setText(model_info.source)
        self.size_label.setText(f"{model_info.size_mb} MB")
        
        if model_info.is_downloaded:
            self.status_label.setText("已下载")
            self.status_label.setStyleSheet("color: green;")
            self.download_btn.setEnabled(False)
            self.delete_btn.setEnabled(True)
        else:
            self.status_label.setText("未下载")
            self.status_label.setStyleSheet("color: red;")
            self.download_btn.setEnabled(True)
            self.delete_btn.setEnabled(False)
        
        self.desc_label.setText(model_info.description)
    
    def on_download_clicked(self):
        """下载按钮点击处理"""
        if self.model_info:
            self.download_requested.emit(self.model_info.model_id)
    
    def on_delete_clicked(self):
        """删除按钮点击处理"""
        if self.model_info:
            # 弹出确认对话框
            reply = QMessageBox.question(
                self, 
                "确认删除", 
                f"确定要删除模型 {self.model_info.name} 吗？\n这将删除本地文件。",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.delete_requested.emit(self.model_info.model_id)


class ModelDownloadProgressWidget(QWidget):
    """模型下载进度组件"""
    
    # 自定义信号
    cancel_requested = pyqtSignal(str)  # model_id
    
    def __init__(self, model_info: ModelInfo, parent=None):
        """
        初始化下载进度组件
        
        Args:
            model_info: 模型信息
            parent: 父组件
        """
        super().__init__(parent)
        self.model_info = model_info
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 模型名称
        self.name_label = QLabel(self.model_info.name)
        self.name_label.setStyleSheet("font-weight: bold;")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 状态标签
        self.status_label = QLabel("准备下载...")
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        
        # 水平布局放置进度条和取消按钮
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.cancel_btn)
        
        # 添加到主布局
        layout.addWidget(self.name_label)
        layout.addLayout(progress_layout)
        layout.addWidget(self.status_label)
    
    def update_progress(self, current: int, total: int):
        """
        更新下载进度
        
        Args:
            current: 当前已下载字节数
            total: 总字节数
        """
        if total <= 0:
            percentage = 0
        else:
            percentage = int((current / total) * 100)
        
        self.progress_bar.setValue(percentage)
        
        # 计算下载速度和剩余时间（这里简化处理）
        # 在实际应用中，应该记录时间戳和已下载字节数，然后计算速度
        self.status_label.setText(f"已下载: {self._format_size(current)} / {self._format_size(total)}")
    
    def _format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 字节数
            
        Returns:
            str: 格式化后的文件大小
        """
        # 转换为KB、MB或GB
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def set_completed(self, success: bool, message: str = ""):
        """
        设置下载完成状态
        
        Args:
            success: 是否成功
            message: 附加消息
        """
        if success:
            self.status_label.setText("下载完成")
            self.status_label.setStyleSheet("color: green;")
            self.progress_bar.setValue(100)
        else:
            self.status_label.setText(f"下载失败: {message}")
            self.status_label.setStyleSheet("color: red;")
        
        self.cancel_btn.setText("关闭")
    
    def on_cancel_clicked(self):
        """取消按钮点击处理"""
        # 如果下载已完成，直接关闭
        if self.cancel_btn.text() == "关闭":
            self.hide()
            self.deleteLater()
            return
        
        # 否则发送取消信号
        self.cancel_requested.emit(self.model_info.model_id)
        self.cancel_btn.setText("关闭")


class ModelManagerWidget(QWidget):
    """模型管理器界面组件"""
    
    def __init__(self, parent=None):
        """
        初始化模型管理器界面
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self.model_manager = get_model_manager()
        self.model_service = get_model_service()
        self.download_widgets = {}  # {model_id: ModelDownloadProgressWidget}
        self.initUI()
        self.load_models()
    
    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("模型管理")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧模型列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 模型列表和按钮
        list_layout = QVBoxLayout()
        
        list_label = QLabel("可用模型")
        list_label.setStyleSheet("font-weight: bold;")
        
        self.model_list = QListWidget()
        self.model_list.setAlternatingRowColors(True)
        self.model_list.currentItemChanged.connect(self.on_model_selected)
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_models)
        
        list_layout.addWidget(list_label)
        list_layout.addWidget(self.model_list)
        list_layout.addWidget(refresh_btn)
        
        left_layout.addLayout(list_layout)
        
        # 右侧模型详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.detail_widget = ModelDetailWidget()
        self.detail_widget.download_requested.connect(self.download_model)
        self.detail_widget.delete_requested.connect(self.delete_model)
        
        # 下载进度区域
        self.downloads_group = QGroupBox("下载进度")
        downloads_layout = QVBoxLayout(self.downloads_group)
        downloads_layout.setContentsMargins(10, 15, 10, 10)
        downloads_layout.setSpacing(10)
        
        # 提示标签
        self.downloads_label = QLabel("无下载任务")
        downloads_layout.addWidget(self.downloads_label)
        
        # 添加到右侧布局
        right_layout.addWidget(self.detail_widget)
        right_layout.addWidget(self.downloads_group)
        right_layout.addStretch(1)
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 400])  # 设置初始宽度比例
        
        # 添加到主布局
        layout.addWidget(title_label)
        layout.addWidget(splitter)
    
    def load_models(self):
        """加载模型列表"""
        self.model_list.clear()
        
        models = self.model_manager.get_available_models()
        for model_info in models:
            item = ModelListItem(model_info)
            self.model_list.addItem(item)
        
        if models:
            self.model_list.setCurrentRow(0)
    
    def refresh_models(self):
        """刷新模型列表和状态"""
        # 刷新模型状态
        self.model_manager.refresh_models_status()
        
        # 记住当前选中的模型ID
        current_model_id = None
        if self.model_list.currentItem():
            current_model_id = self.model_list.currentItem().model_info.model_id
        
        # 重新加载模型列表
        self.load_models()
        
        # 恢复选中状态
        if current_model_id:
            for i in range(self.model_list.count()):
                item = self.model_list.item(i)
                if item.model_info.model_id == current_model_id:
                    self.model_list.setCurrentItem(item)
                    break
    
    def on_model_selected(self, current, previous):
        """
        处理模型选择变化
        
        Args:
            current: 当前选中的项
            previous: 之前选中的项
        """
        if current:
            self.detail_widget.set_model_info(current.model_info)
        else:
            self.detail_widget.set_model_info(None)
    
    def download_model(self, model_id: str):
        """
        下载模型
        
        Args:
            model_id: 模型ID
        """
        model_info = self.model_manager.get_model_info(model_id)
        if not model_info:
            return
        
        # 启动下载
        success = self.model_manager.download_model(model_id)
        if not success:
            QMessageBox.warning(self, "下载失败", f"无法启动下载: {model_info.name}")
            return
        
        # 创建下载进度组件
        progress_widget = ModelDownloadProgressWidget(model_info)
        progress_widget.cancel_requested.connect(self.cancel_download)
        
        # 保存并显示
        self.download_widgets[model_id] = progress_widget
        
        # 更新下载组区域
        if self.downloads_label.isVisible():
            self.downloads_label.hide()
        
        # 添加到下载组
        self.downloads_group.layout().addWidget(progress_widget)
        
        # 连接下载器的信号
        downloader = self.model_manager.downloader
        downloader.download_progress.connect(self.on_download_progress)
        downloader.download_complete.connect(self.on_download_complete)
    
    @pyqtSlot(str, int, int)
    def on_download_progress(self, model_id: str, current: int, total: int):
        """
        处理下载进度更新
        
        Args:
            model_id: 模型ID
            current: 当前已下载字节数
            total: 总字节数
        """
        if model_id in self.download_widgets:
            self.download_widgets[model_id].update_progress(current, total)
    
    @pyqtSlot(str, bool, str)
    def on_download_complete(self, model_id: str, success: bool, message: str):
        """
        处理下载完成
        
        Args:
            model_id: 模型ID
            success: 是否成功
            message: 附加消息
        """
        if model_id in self.download_widgets:
            self.download_widgets[model_id].set_completed(success, message)
        
        # 刷新模型状态
        self.refresh_models()
    
    def cancel_download(self, model_id: str):
        """
        取消下载
        
        Args:
            model_id: 模型ID
        """
        # 调用下载器取消下载
        self.model_manager.downloader.cancel_download(model_id)
        
        # 从列表中移除
        # 注意下载组件会自行删除，不需要在这里删除
    
    def delete_model(self, model_id: str):
        """
        删除模型
        
        Args:
            model_id: 模型ID
        """
        # 卸载模型（如果已加载）
        self.model_service.unload_model(model_id)
        
        # 删除模型文件
        success = self.model_manager.delete_model(model_id)
        
        if success:
            # 刷新模型列表
            self.refresh_models()
        else:
            QMessageBox.warning(self, "删除失败", f"无法删除模型文件")


class ModelConfigDialog(QDialog):
    """模型配置对话框"""
    
    def __init__(self, model_info: ModelInfo, parent=None):
        """
        初始化模型配置对话框
        
        Args:
            model_info: 模型信息
            parent: 父组件
        """
        super().__init__(parent)
        self.model_info = model_info
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        self.setWindowTitle(f"配置模型 - {self.model_info.name}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form = QFormLayout()
        
        # 阈值设置
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(self.model_info.config.get("threshold", 0.7))
        self.threshold_spin.setDecimals(2)
        form.addRow("相似度阈值:", self.threshold_spin)
        
        # 批处理大小
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 64)
        self.batch_size_spin.setValue(self.model_info.config.get("batch_size", 8))
        form.addRow("批处理大小:", self.batch_size_spin)
        
        # 是否使用GPU
        self.use_gpu_check = QCheckBox("使用GPU加速")
        self.use_gpu_check.setChecked(self.model_info.config.get("use_gpu", True))
        form.addRow("", self.use_gpu_check)
        
        # 使用量化版本
        self.use_quantized_check = QCheckBox("使用量化版本")
        self.use_quantized_check.setChecked(self.model_info.config.get("use_quantized", False))
        self.use_quantized_check.setToolTip("量化模型可减少内存占用，但可能影响精度")
        form.addRow("", self.use_quantized_check)
        
        layout.addLayout(form)
        
        # 按钮
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_config)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(buttons_layout)
    
    def save_config(self):
        """保存配置"""
        # 更新模型配置
        self.model_info.config["threshold"] = self.threshold_spin.value()
        self.model_info.config["batch_size"] = self.batch_size_spin.value()
        self.model_info.config["use_gpu"] = self.use_gpu_check.isChecked()
        self.model_info.config["use_quantized"] = self.use_quantized_check.isChecked()
        
        # 保存到模型管理器
        model_manager = get_model_manager()
        model_manager.update_model_metadata(
            self.model_info.model_id, 
            config=self.model_info.config
        )
        
        self.accept() 