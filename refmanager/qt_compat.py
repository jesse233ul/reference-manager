try:
    from PyQt5.QtCore import QMimeData, Qt, QUrl, pyqtSignal as Signal
    from PyQt5.QtGui import QColor, QDesktopServices, QDrag, QIcon, QPainter, QPixmap
    from PyQt5.QtWidgets import (
        QAction,
        QApplication,
        QAbstractItemView,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QSizePolicy,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTableWidgetSelectionRange,
        QToolBar,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    QT_BACKEND = "PyQt5"
except ImportError:
    from PySide6.QtCore import QMimeData, Qt, QUrl, Signal
    from PySide6.QtGui import QAction, QColor, QDesktopServices, QDrag, QIcon, QPainter, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QSizePolicy,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTableWidgetSelectionRange,
        QToolBar,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    QT_BACKEND = "PySide6"


def exec_qt_dialog(dialog: QDialog) -> int:
    if hasattr(dialog, "exec"):
        return dialog.exec()
    return dialog.exec_()


def exec_qt_app(app: QApplication) -> int:
    if hasattr(app, "exec"):
        return app.exec()
    return app.exec_()


def exec_qt_menu(menu: QMenu, position):
    if hasattr(menu, "exec"):
        return menu.exec(position)
    return menu.exec_(position)
