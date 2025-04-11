from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QCheckBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal

class ColumnSelector(QWidget):
    """树形列选择器，支持选择文件、工作表和列"""
    
    # 自定义信号
    on_config_changed = pyqtSignal(dict)  # 选择变化时发出的信号，参数为当前选择的配置
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.file_infos = {}  # 文件信息字典 {file_path: ExcelFileInfo}
        self.sheet_items = {}  # 工作表项字典 {file_path: {sheet_name: QTreeWidgetItem}}
        self.column_items = {}  # 列项字典 {file_path: {sheet_name: {column_name: QTreeWidgetItem}}}
        
    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建树形视图
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['名称'])
        self.tree.setSelectionMode(QTreeWidget.NoSelection)  # 不允许选择项目
        self.tree.itemChanged.connect(self.handle_item_changed)
        
        # 设置树形视图样式
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f0f0f0;
            }
            
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            
            QTreeWidget::item:selected {
                background-color: transparent;
                color: black;
            }
        """)
        
        # 快速选择按钮
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        self.select_all_button = QPushButton('全选')
        self.select_all_button.clicked.connect(self.select_all)
        
        self.deselect_all_button = QPushButton('取消全选')
        self.deselect_all_button.clicked.connect(self.deselect_all)
        
        buttons_layout.addWidget(self.select_all_button)
        buttons_layout.addWidget(self.deselect_all_button)
        buttons_layout.addStretch(1)
        
        # 添加组件到布局
        layout.addWidget(self.tree)
        layout.addWidget(buttons_frame)
    
    def load_file_infos(self, file_infos):
        """加载文件信息并构建树形视图
        
        Args:
            file_infos: 文件信息字典 {file_path: ExcelFileInfo}
        """
        # 清空当前树
        self.tree.clear()
        self.file_infos = file_infos
        self.sheet_items = {}
        self.column_items = {}
        
        # 对于每个文件，创建文件节点
        for file_path, file_info in file_infos.items():
            file_item = QTreeWidgetItem(self.tree)
            file_item.setText(0, file_info.file_name)
            file_item.setCheckState(0, Qt.Unchecked)
            file_item.setFlags(file_item.flags() | Qt.ItemIsAutoTristate)
            
            # 存储每个文件的工作表项和列项
            self.sheet_items[file_path] = {}
            self.column_items[file_path] = {}
            
            # 对于每个工作表，创建工作表节点
            for sheet_name, columns in file_info.sheets.items():
                sheet_item = QTreeWidgetItem(file_item)
                sheet_item.setText(0, sheet_name)
                sheet_item.setCheckState(0, Qt.Unchecked)
                sheet_item.setFlags(sheet_item.flags() | Qt.ItemIsAutoTristate)
                
                # 存储工作表项
                self.sheet_items[file_path][sheet_name] = sheet_item
                self.column_items[file_path][sheet_name] = {}
                
                # 对于每个列，创建列节点
                for column in columns:
                    column_item = QTreeWidgetItem(sheet_item)
                    column_item.setText(0, column)
                    column_item.setCheckState(0, Qt.Unchecked)
                    
                    # 存储列项
                    self.column_items[file_path][sheet_name][column] = column_item
        
        # 展开所有节点
        self.tree.expandAll()
    
    def handle_item_changed(self, item, column):
        """处理项目选择状态变化"""
        # 如果状态改变，发出信号
        configs = self.get_deduplication_configs()
        self.on_config_changed.emit(configs)
    
    def select_all(self):
        """选择所有文件和列"""
        # 遍历所有顶级项（文件）
        for i in range(self.tree.topLevelItemCount()):
            file_item = self.tree.topLevelItem(i)
            file_item.setCheckState(0, Qt.Checked)
    
    def deselect_all(self):
        """取消选择所有文件和列"""
        # 遍历所有顶级项（文件）
        for i in range(self.tree.topLevelItemCount()):
            file_item = self.tree.topLevelItem(i)
            file_item.setCheckState(0, Qt.Unchecked)
    
    def get_deduplication_configs(self):
        """获取当前选择的去重配置
        
        Returns:
            dict: 去重配置字典，格式为:
                {
                    "file_path1": {
                        "sheet_name1": {
                            "key_columns": ["col1", "col2"]
                        },
                        "sheet_name2": {
                            "key_columns": ["col3"]
                        }
                    },
                    "file_path2": {
                        ...
                    }
                }
        """
        configs = {}
        
        # 遍历所有文件
        for file_path, sheet_items in self.sheet_items.items():
            file_config = {}
            
            # 遍历文件的所有工作表
            for sheet_name, sheet_item in sheet_items.items():
                # 获取此工作表中选中的列
                key_columns = []
                for column, column_item in self.column_items[file_path][sheet_name].items():
                    if column_item.checkState(0) == Qt.Checked:
                        key_columns.append(column)
                
                # 如果有选中的列，添加到配置中
                if key_columns:
                    file_config[sheet_name] = {
                        "key_columns": key_columns
                    }
            
            # 如果此文件有配置，添加到结果中
            if file_config:
                configs[file_path] = file_config
        
        return configs
    
    def set_keep_option(self, keep_option):
        """设置所有选中工作表的保留选项
        
        Args:
            keep_option: 保留选项，如'first', 'last', 'False'等
        """
        configs = self.get_deduplication_configs()
        
        # 对所有已配置的工作表设置保留选项
        for file_config in configs.values():
            for sheet_config in file_config.values():
                sheet_config["keep_option"] = keep_option
        
        return configs
    
    def clear(self):
        """清空树形视图和数据"""
        self.tree.clear()
        self.file_infos = {}
        self.sheet_items = {}
        self.column_items = {}
    
    def has_selections(self):
        """检查是否有选择的列
        
        Returns:
            bool: 如果至少有一个列被选择，返回True，否则返回False
        """
        # 遍历所有文件
        for file_path, sheet_items in self.sheet_items.items():
            # 遍历文件的所有工作表
            for sheet_name, sheet_item in sheet_items.items():
                # 检查此工作表中是否有选中的列
                for column, column_item in self.column_items[file_path][sheet_name].items():
                    if column_item.checkState(0) == Qt.Checked:
                        return True
        
        return False 