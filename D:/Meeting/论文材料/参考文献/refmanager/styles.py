APP_STYLE = """
QMainWindow {
    background: #f4f6f8;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 10.5pt;
}
QToolBar {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #d9dee7;
    spacing: 8px;
    padding: 8px 12px;
}
QToolButton, QPushButton {
    background: #1f6feb;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 12px;
}
QToolButton:hover, QPushButton:hover {
    background: #185abc;
}
QToolButton:pressed, QPushButton:pressed {
    background: #123f86;
}
QLineEdit, QPlainTextEdit, QComboBox, QListWidget {
    background: #ffffff;
    border: 1px solid #ccd3dd;
    border-radius: 6px;
    padding: 7px;
    selection-background-color: #cfe3ff;
}
QTableWidget {
    background: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #d9dee7;
    border-radius: 8px;
    gridline-color: #edf0f4;
}
QTreeWidget {
    background: #ffffff;
    border: 1px solid #d9dee7;
    border-radius: 8px;
    padding: 4px;
}
QTreeWidget::item {
    min-height: 28px;
    padding: 4px 6px;
    border-radius: 5px;
}
QTreeWidget::item:selected {
    background: #dbeafe;
    color: #172033;
}
QHeaderView::section {
    background: #eef2f7;
    color: #263445;
    border: none;
    border-right: 1px solid #d9dee7;
    padding: 8px;
    font-weight: 600;
}
QTableWidget::item {
    padding: 7px;
}
QTableWidget::item:selected {
    background: #dbeafe;
    color: #172033;
}
#detailPanel {
    background: #ffffff;
    border-left: 1px solid #d9dee7;
}
#panelTitle {
    font-size: 15pt;
    font-weight: 700;
    color: #172033;
}
#sideTitle {
    font-size: 11pt;
    font-weight: 700;
    color: #172033;
}
#pathLabel {
    color: #667085;
    font-size: 9pt;
}
QLabel {
    color: #344054;
}
"""
