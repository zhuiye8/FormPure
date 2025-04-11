# UI样式定义文件
STYLE_SHEET = """
QMainWindow {
    background-color: #f5f5f5;
}

QLabel {
    font-size: 14px;
}

QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:disabled {
    background-color: #BDBDBD;
}

QToolButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-size: 14px;
}

QToolButton:hover {
    background-color: #1976D2;
}

QComboBox {
    border: 1px solid #BDBDBD;
    border-radius: 4px;
    padding: 6px;
    min-width: 150px;
    background-color: white;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QGroupBox {
    font-size: 16px;
    font-weight: bold;
    border: 2px solid #E0E0E0;
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 10px;
    color: #2196F3;
}

QTableWidget {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    background-color: white;
    alternate-background-color: #f0f0f0;
    gridline-color: #E0E0E0;
}

QTableWidget::item:selected {
    background-color: #E3F2FD;
    color: black;
}

QHeaderView::section {
    background-color: #E3F2FD;
    padding: 6px;
    border: 1px solid #E0E0E0;
    border-radius: 0px;
    font-weight: bold;
}

QProgressBar {
    border: 1px solid #BDBDBD;
    border-radius: 4px;
    text-align: center;
    background-color: white;
}

QProgressBar::chunk {
    background-color: #4CAF50;
    width: 10px;
    margin: 0px;
}

QCheckBox {
    font-size: 14px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QSplitter::handle {
    background-color: #E0E0E0;
}

QScrollBar:vertical {
    border: none;
    background: #f5f5f5;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #BDBDBD;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar:horizontal {
    border: none;
    background: #f5f5f5;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #BDBDBD;
    min-width: 20px;
    border-radius: 4px;
}
""" 