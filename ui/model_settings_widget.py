"""
模型设置界面
提供全局模型设置和混合策略配置功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QCheckBox, QComboBox, QTabWidget, 
                            QGroupBox, QSpinBox, QDoubleSpinBox, QFormLayout,
                            QSlider, QRadioButton, QButtonGroup, QScrollArea,
                            QSplitter, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings

# 导入自定义模块
from core.model_manager import get_model_manager
from core.model_inference import get_model_service

class ModelSettingsWidget(QWidget):
    """模型设置界面，配置模型使用和混合策略"""
    
    # 自定义信号
    settings_changed = pyqtSignal()  # 设置变更信号
    
    def __init__(self, parent=None):
        """
        初始化模型设置界面
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self.model_manager = get_model_manager()
        self.model_service = get_model_service()
        self.settings = QSettings("ExcelDeduplication", "ModelSettings")
        self.initUI()
        self.load_settings()
    
    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 基本设置选项卡
        basic_tab = self.create_basic_settings_tab()
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 高级设置选项卡
        advanced_tab = self.create_advanced_settings_tab()
        tab_widget.addTab(advanced_tab, "高级设置")
        
        # 混合策略选项卡
        hybrid_tab = self.create_hybrid_strategy_tab()
        tab_widget.addTab(hybrid_tab, "混合策略")
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存设置")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.clicked.connect(self.reset_settings)
        
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.save_btn)
        
        # 添加到主布局
        layout.addWidget(tab_widget)
        layout.addLayout(buttons_layout)
    
    def create_basic_settings_tab(self):
        """创建基本设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 启用模型设置
        enable_group = QGroupBox("模型启用设置")
        enable_layout = QVBoxLayout(enable_group)
        
        self.enable_model_check = QCheckBox("启用模型功能")
        self.enable_model_check.setToolTip("启用后将使用模型进行相似度计算，禁用则仅使用简单算法")
        
        self.auto_load_model_check = QCheckBox("启动时自动加载最新模型")
        self.auto_load_model_check.setToolTip("启动程序时自动加载最近使用的模型")
        
        enable_layout.addWidget(self.enable_model_check)
        enable_layout.addWidget(self.auto_load_model_check)
        
        # 预设选择
        preset_group = QGroupBox("性能与准确度平衡")
        preset_layout = QVBoxLayout(preset_group)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("高性能（优先速度）", "performance")
        self.preset_combo.addItem("平衡（速度与准确度）", "balanced")
        self.preset_combo.addItem("高准确度（优先准确性）", "accuracy")
        
        preset_layout.addWidget(QLabel("选择预设:"))
        preset_layout.addWidget(self.preset_combo)
        
        # 阈值设置
        threshold_group = QGroupBox("相似度阈值设置")
        threshold_layout = QFormLayout(threshold_group)
        
        self.basic_threshold_spin = QDoubleSpinBox()
        self.basic_threshold_spin.setRange(0.0, 1.0)
        self.basic_threshold_spin.setSingleStep(0.05)
        self.basic_threshold_spin.setDecimals(2)
        
        self.model_threshold_spin = QDoubleSpinBox()
        self.model_threshold_spin.setRange(0.0, 1.0)
        self.model_threshold_spin.setSingleStep(0.05)
        self.model_threshold_spin.setDecimals(2)
        
        threshold_layout.addRow("基本算法阈值:", self.basic_threshold_spin)
        threshold_layout.addRow("模型算法阈值:", self.model_threshold_spin)
        
        # 默认模型选择
        model_group = QGroupBox("默认模型")
        model_layout = QVBoxLayout(model_group)
        
        self.model_combo = QComboBox()
        self.update_model_combo()
        
        model_layout.addWidget(QLabel("选择默认使用模型:"))
        model_layout.addWidget(self.model_combo)
        
        # 添加到主布局
        layout.addWidget(enable_group)
        layout.addWidget(preset_group)
        layout.addWidget(threshold_group)
        layout.addWidget(model_group)
        layout.addStretch(1)
        
        return tab
    
    def create_advanced_settings_tab(self):
        """创建高级设置选项卡"""
        tab = QScrollArea()
        tab.setWidgetResizable(True)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # 性能设置
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout(performance_group)
        
        self.use_gpu_check = QCheckBox("使用GPU加速")
        self.use_gpu_check.setToolTip("如果可用，使用GPU加速模型推理")
        
        self.use_quantized_check = QCheckBox("使用模型量化")
        self.use_quantized_check.setToolTip("使用量化模型减少内存占用，但可能降低准确度")
        
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 64)
        self.batch_size_spin.setSingleStep(1)
        self.batch_size_spin.setToolTip("批处理大小，值越大处理速度越快但内存占用越多")
        
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 16)
        self.max_workers_spin.setSingleStep(1)
        self.max_workers_spin.setToolTip("并行工作线程数量")
        
        performance_layout.addRow("", self.use_gpu_check)
        performance_layout.addRow("", self.use_quantized_check)
        performance_layout.addRow("批处理大小:", self.batch_size_spin)
        performance_layout.addRow("最大线程数:", self.max_workers_spin)
        
        # 内存管理
        memory_group = QGroupBox("内存管理")
        memory_layout = QVBoxLayout(memory_group)
        
        self.unload_idle_check = QCheckBox("自动卸载闲置模型")
        self.unload_idle_check.setToolTip("长时间不使用的模型将自动卸载以释放内存")
        
        self.idle_time_spin = QSpinBox()
        self.idle_time_spin.setRange(1, 60)
        self.idle_time_spin.setSingleStep(5)
        self.idle_time_spin.setSuffix(" 分钟")
        self.idle_time_spin.setToolTip("模型闲置多长时间后自动卸载")
        
        idle_layout = QHBoxLayout()
        idle_layout.addWidget(QLabel("闲置时间:"))
        idle_layout.addWidget(self.idle_time_spin)
        idle_layout.addStretch(1)
        
        memory_layout.addWidget(self.unload_idle_check)
        memory_layout.addLayout(idle_layout)
        
        # 模型路径
        path_group = QGroupBox("模型存储路径")
        path_layout = QHBoxLayout(path_group)
        
        self.model_path_label = QLabel()
        self.model_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.model_path_label.setWordWrap(True)
        
        self.change_path_btn = QPushButton("更改路径")
        
        path_layout.addWidget(self.model_path_label, 1)
        path_layout.addWidget(self.change_path_btn)
        
        # 添加到主布局
        layout.addWidget(performance_group)
        layout.addWidget(memory_group)
        layout.addWidget(path_group)
        layout.addStretch(1)
        
        tab.setWidget(content)
        return tab
    
    def create_hybrid_strategy_tab(self):
        """创建混合策略选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 策略选择
        strategy_group = QGroupBox("混合策略")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("始终使用模型", "always_model")
        self.strategy_combo.addItem("先简单算法后模型", "basic_then_model")
        self.strategy_combo.addItem("根据文本长度选择", "length_based")
        self.strategy_combo.addItem("自适应策略", "adaptive")
        self.strategy_combo.currentIndexChanged.connect(self.on_strategy_changed)
        
        strategy_desc = QLabel("选择不同的混合策略以平衡性能和准确度")
        strategy_desc.setWordWrap(True)
        
        strategy_layout.addWidget(QLabel("选择策略:"))
        strategy_layout.addWidget(self.strategy_combo)
        strategy_layout.addWidget(strategy_desc)
        
        # 策略参数
        params_group = QGroupBox("策略参数")
        self.params_layout = QVBoxLayout(params_group)
        
        # 添加策略参数控件（初始为空，会根据选择的策略动态更新）
        self.create_strategy_params()
        
        # 添加到主布局
        layout.addWidget(strategy_group)
        layout.addWidget(params_group)
        layout.addStretch(1)
        
        return tab
    
    def create_strategy_params(self):
        """根据当前选择的策略创建对应的参数控件"""
        # 清空现有控件
        self.clear_layout(self.params_layout)
        
        strategy = self.strategy_combo.currentData()
        
        if strategy == "always_model":
            # 始终使用模型策略没有参数
            label = QLabel("此策略无需额外参数，将始终使用模型进行相似度计算。")
            label.setWordWrap(True)
            self.params_layout.addWidget(label)
            
        elif strategy == "basic_then_model":
            # 先简单算法后模型策略
            form = QFormLayout()
            
            self.prefilter_threshold_spin = QDoubleSpinBox()
            self.prefilter_threshold_spin.setRange(0.0, 1.0)
            self.prefilter_threshold_spin.setSingleStep(0.05)
            self.prefilter_threshold_spin.setDecimals(2)
            self.prefilter_threshold_spin.setValue(0.5)
            self.prefilter_threshold_spin.setToolTip("基本算法筛选阈值，相似度高于此值的文本才会使用模型进一步判断")
            
            form.addRow("预筛选阈值:", self.prefilter_threshold_spin)
            self.params_layout.addLayout(form)
            
            desc = QLabel("此策略先使用基本算法（如编辑距离）快速筛选，只有相似度高于阈值的文本才会使用模型进一步判断，可提高处理速度。")
            desc.setWordWrap(True)
            self.params_layout.addWidget(desc)
            
        elif strategy == "length_based":
            # 根据文本长度选择策略
            form = QFormLayout()
            
            self.min_length_spin = QSpinBox()
            self.min_length_spin.setRange(0, 1000)
            self.min_length_spin.setSingleStep(10)
            self.min_length_spin.setValue(50)
            self.min_length_spin.setSuffix(" 字符")
            self.min_length_spin.setToolTip("文本长度大于此值时使用模型，否则使用基本算法")
            
            form.addRow("最小长度:", self.min_length_spin)
            self.params_layout.addLayout(form)
            
            desc = QLabel("此策略根据文本长度选择算法，较短的文本使用基本算法，较长的文本使用模型。对于短文本，基本算法通常足够准确且速度更快。")
            desc.setWordWrap(True)
            self.params_layout.addWidget(desc)
            
        elif strategy == "adaptive":
            # 自适应策略
            form = QFormLayout()
            
            self.complexity_threshold_spin = QDoubleSpinBox()
            self.complexity_threshold_spin.setRange(0.0, 1.0)
            self.complexity_threshold_spin.setSingleStep(0.05)
            self.complexity_threshold_spin.setDecimals(2)
            self.complexity_threshold_spin.setValue(0.6)
            self.complexity_threshold_spin.setToolTip("文本复杂度阈值，复杂度高于此值的文本将使用模型")
            
            self.use_dict_check = QCheckBox("使用词典辅助判断")
            self.use_dict_check.setChecked(True)
            self.use_dict_check.setToolTip("使用内置词典辅助判断文本是否包含特定术语")
            
            form.addRow("复杂度阈值:", self.complexity_threshold_spin)
            form.addRow("", self.use_dict_check)
            self.params_layout.addLayout(form)
            
            desc = QLabel("自适应策略会分析文本特征（长度、复杂度、特殊术语等），智能选择最合适的算法。适合处理多样化的文本数据。")
            desc.setWordWrap(True)
            self.params_layout.addWidget(desc)
    
    def on_strategy_changed(self, index):
        """策略选择变化处理"""
        self.create_strategy_params()
    
    def clear_layout(self, layout):
        """清空布局中的所有组件"""
        if layout is None:
            return
        
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            
            if widget is not None:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())
    
    def update_model_combo(self):
        """更新模型下拉列表"""
        self.model_combo.clear()
        
        # 获取已下载的模型
        models = self.model_manager.get_downloaded_models()
        
        if not models:
            self.model_combo.addItem("无可用模型", "")
            return
        
        # 添加模型到下拉列表
        for model in models:
            self.model_combo.addItem(model.name, model.model_id)
    
    def load_settings(self):
        """加载设置"""
        # 基本设置
        self.enable_model_check.setChecked(self.settings.value("enable_model", True, type=bool))
        self.auto_load_model_check.setChecked(self.settings.value("auto_load_model", True, type=bool))
        
        preset_index = self.preset_combo.findData(self.settings.value("preset", "balanced"))
        if preset_index >= 0:
            self.preset_combo.setCurrentIndex(preset_index)
        
        self.basic_threshold_spin.setValue(self.settings.value("basic_threshold", 0.7, type=float))
        self.model_threshold_spin.setValue(self.settings.value("model_threshold", 0.8, type=float))
        
        # 默认模型
        default_model = self.settings.value("default_model", "")
        model_index = self.model_combo.findData(default_model)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        
        # 高级设置
        self.use_gpu_check.setChecked(self.settings.value("use_gpu", True, type=bool))
        self.use_quantized_check.setChecked(self.settings.value("use_quantized", False, type=bool))
        self.batch_size_spin.setValue(self.settings.value("batch_size", 8, type=int))
        self.max_workers_spin.setValue(self.settings.value("max_workers", 4, type=int))
        
        self.unload_idle_check.setChecked(self.settings.value("unload_idle", True, type=bool))
        self.idle_time_spin.setValue(self.settings.value("idle_time", 15, type=int))
        
        # 显示模型路径
        self.model_path_label.setText(self.model_manager.models_dir)
        
        # 混合策略
        strategy_index = self.strategy_combo.findData(self.settings.value("strategy", "basic_then_model"))
        if strategy_index >= 0:
            self.strategy_combo.setCurrentIndex(strategy_index)
        
        # 加载策略参数（在create_strategy_params创建参数控件后设置）
        self.on_strategy_changed(self.strategy_combo.currentIndex())
        
        # 根据当前策略设置参数值
        strategy = self.strategy_combo.currentData()
        
        if strategy == "basic_then_model" and hasattr(self, "prefilter_threshold_spin"):
            self.prefilter_threshold_spin.setValue(self.settings.value("prefilter_threshold", 0.5, type=float))
        
        elif strategy == "length_based" and hasattr(self, "min_length_spin"):
            self.min_length_spin.setValue(self.settings.value("min_length", 50, type=int))
        
        elif strategy == "adaptive":
            if hasattr(self, "complexity_threshold_spin"):
                self.complexity_threshold_spin.setValue(self.settings.value("complexity_threshold", 0.6, type=float))
            
            if hasattr(self, "use_dict_check"):
                self.use_dict_check.setChecked(self.settings.value("use_dict", True, type=bool))
    
    def save_settings(self):
        """保存设置"""
        # 基本设置
        self.settings.setValue("enable_model", self.enable_model_check.isChecked())
        self.settings.setValue("auto_load_model", self.auto_load_model_check.isChecked())
        self.settings.setValue("preset", self.preset_combo.currentData())
        self.settings.setValue("basic_threshold", self.basic_threshold_spin.value())
        self.settings.setValue("model_threshold", self.model_threshold_spin.value())
        self.settings.setValue("default_model", self.model_combo.currentData())
        
        # 高级设置
        self.settings.setValue("use_gpu", self.use_gpu_check.isChecked())
        self.settings.setValue("use_quantized", self.use_quantized_check.isChecked())
        self.settings.setValue("batch_size", self.batch_size_spin.value())
        self.settings.setValue("max_workers", self.max_workers_spin.value())
        self.settings.setValue("unload_idle", self.unload_idle_check.isChecked())
        self.settings.setValue("idle_time", self.idle_time_spin.value())
        
        # 混合策略
        self.settings.setValue("strategy", self.strategy_combo.currentData())
        
        # 保存策略参数
        strategy = self.strategy_combo.currentData()
        
        if strategy == "basic_then_model" and hasattr(self, "prefilter_threshold_spin"):
            self.settings.setValue("prefilter_threshold", self.prefilter_threshold_spin.value())
        
        elif strategy == "length_based" and hasattr(self, "min_length_spin"):
            self.settings.setValue("min_length", self.min_length_spin.value())
        
        elif strategy == "adaptive":
            if hasattr(self, "complexity_threshold_spin"):
                self.settings.setValue("complexity_threshold", self.complexity_threshold_spin.value())
            
            if hasattr(self, "use_dict_check"):
                self.settings.setValue("use_dict", self.use_dict_check.isChecked())
        
        # 发出设置变更信号
        self.settings_changed.emit()
    
    def reset_settings(self):
        """重置为默认设置"""
        # 基本设置
        self.enable_model_check.setChecked(True)
        self.auto_load_model_check.setChecked(True)
        self.preset_combo.setCurrentIndex(self.preset_combo.findData("balanced"))
        self.basic_threshold_spin.setValue(0.7)
        self.model_threshold_spin.setValue(0.8)
        
        # 高级设置
        self.use_gpu_check.setChecked(True)
        self.use_quantized_check.setChecked(False)
        self.batch_size_spin.setValue(8)
        self.max_workers_spin.setValue(4)
        self.unload_idle_check.setChecked(True)
        self.idle_time_spin.setValue(15)
        
        # 混合策略
        self.strategy_combo.setCurrentIndex(self.strategy_combo.findData("basic_then_model"))
        
        # 根据当前策略重置参数
        strategy = self.strategy_combo.currentData()
        
        if strategy == "basic_then_model" and hasattr(self, "prefilter_threshold_spin"):
            self.prefilter_threshold_spin.setValue(0.5)
        
        elif strategy == "length_based" and hasattr(self, "min_length_spin"):
            self.min_length_spin.setValue(50)
        
        elif strategy == "adaptive":
            if hasattr(self, "complexity_threshold_spin"):
                self.complexity_threshold_spin.setValue(0.6)
            
            if hasattr(self, "use_dict_check"):
                self.use_dict_check.setChecked(True) 