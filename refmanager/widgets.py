from pathlib import Path

from .qt_compat import (
    QAbstractItemView,
    QColor,
    QDialog,
    QDrag,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMimeData,
    QPainter,
    QPixmap,
    QPushButton,
    QTableWidget,
    Qt,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    Signal,
    exec_qt_menu,
)

class DropTable(QTableWidget):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def selected_id(self) -> int | None:
        ids = self.selected_ids()
        if not ids:
            return None
        return ids[0]

    def selected_ids(self) -> list[int]:
        ids = []
        for item in self.selectedItems():
            value = item.data(Qt.UserRole)
            if value is not None and int(value) not in ids:
                ids.append(int(value))
        return ids

    def startDrag(self, supported_actions) -> None:
        ref_ids = self.selected_ids()
        if not ref_ids:
            return
        ref_id = ref_ids[0]
        row = self.currentRow()
        title_item = self.item(row, 1)
        title = title_item.text() if title_item else ""

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(",".join(str(value) for value in ref_ids))
        drag.setMimeData(mime_data)
        drag.setPixmap(self.drag_preview_pixmap(ref_ids, title))
        drag.setHotSpot(drag.pixmap().rect().center())
        drag.exec_(Qt.MoveAction) if hasattr(drag, "exec_") else drag.exec(Qt.MoveAction)

    def drag_preview_pixmap(self, ref_ids, title: str) -> QPixmap:
        ids = list(ref_ids) if isinstance(ref_ids, (list, tuple, set)) else [int(ref_ids)]
        pixmap = QPixmap(260, 42)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1f6feb"))
        painter.setPen(QColor("#1f6feb"))
        painter.drawRoundedRect(0, 0, 259, 41, 8, 8)
        painter.setPen(QColor("white"))
        if len(ids) == 1:
            text = f"R{ids[0]:04d}  {title}"
        else:
            text = f"{len(ids)} 条文献"
        elided = painter.fontMetrics().elidedText(text, Qt.ElideRight, 240)
        painter.drawText(12, 26, elided)
        painter.end()
        return pixmap

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(Path(url.toLocalFile()))
        if files:
            self.files_dropped.emit(files)
        event.acceptProposedAction()


class CategoryTree(QTreeWidget):
    category_selected = Signal(object)
    category_dropped = Signal(str)
    files_dropped = Signal(list, object)
    delete_category_requested = Signal(str)

    ALL_KEY = None
    UNCATEGORIZED_KEY = ""
    CATEGORY_ROLE = Qt.UserRole

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setMinimumWidth(140)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.itemClicked.connect(self.emit_selected_category)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def refresh(self, categories: list[str], selected_category: str | None) -> None:
        self.blockSignals(True)
        try:
            self.clear()
            all_item = QTreeWidgetItem(["全部文献"])
            all_item.setData(0, self.CATEGORY_ROLE, self.ALL_KEY)
            self.addTopLevelItem(all_item)

            uncategorized_item = QTreeWidgetItem(["未分类"])
            uncategorized_item.setData(0, self.CATEGORY_ROLE, self.UNCATEGORIZED_KEY)
            self.addTopLevelItem(uncategorized_item)

            for category in categories:
                item = QTreeWidgetItem([category])
                item.setData(0, self.CATEGORY_ROLE, category)
                self.addTopLevelItem(item)

            for index in range(self.topLevelItemCount()):
                item = self.topLevelItem(index)
                if item.data(0, self.CATEGORY_ROLE) == selected_category:
                    self.setCurrentItem(item)
                    break
        finally:
            self.blockSignals(False)

    def category_at_position(self, position):
        item = self.itemAt(position)
        if item is None:
            return None, False
        key = item.data(0, self.CATEGORY_ROLE)
        if key is self.ALL_KEY:
            return None, False
        return key, True

    def emit_selected_category(self, item: QTreeWidgetItem) -> None:
        self.category_selected.emit(item.data(0, self.CATEGORY_ROLE))

    def show_context_menu(self, position) -> None:
        item = self.itemAt(position)
        if item is None:
            return
        category = item.data(0, self.CATEGORY_ROLE)
        if category in (self.ALL_KEY, self.UNCATEGORIZED_KEY):
            return
        menu = QMenu(self)
        delete_action = menu.addAction("删除分类")
        action = exec_qt_menu(menu, self.viewport().mapToGlobal(position))
        if action == delete_action:
            self.delete_category_requested.emit(category)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        if isinstance(event.source(), DropTable) and event.source().selected_ids():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        category, ok = self.category_at_position(
            event.position().toPoint() if hasattr(event, "position") else event.pos()
        )
        item = self.itemAt(event.position().toPoint() if hasattr(event, "position") else event.pos())
        if item is not None:
            self.setCurrentItem(item)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        if isinstance(event.source(), DropTable) and ok:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        category, ok = self.category_at_position(
            event.position().toPoint() if hasattr(event, "position") else event.pos()
        )
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    files.append(Path(url.toLocalFile()))
            if files:
                self.files_dropped.emit(files, category if ok else None)
            event.acceptProposedAction()
            return
        if isinstance(event.source(), DropTable) and ok:
            self.category_dropped.emit(category)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def dragLeaveEvent(self, event) -> None:
        self.clearSelection()
        super().dragLeaveEvent(event)


class ColumnDialog(QDialog):
    def __init__(self, settings: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("显示列")
        self.resize(360, 430)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        for setting in settings:
            item = QListWidgetItem(setting["label"])
            item.setData(Qt.UserRole, setting["key"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if setting["visible"] else Qt.Unchecked)
            self.list_widget.addItem(item)

        up_button = QPushButton("上移")
        down_button = QPushButton("下移")
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        buttons = QHBoxLayout()
        buttons.addWidget(up_button)
        buttons.addWidget(down_button)
        buttons.addStretch(1)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("勾选要显示的列，使用上移/下移调整顺序。"))
        layout.addWidget(self.list_widget)
        layout.addLayout(buttons)

        up_button.clicked.connect(lambda: self.move_current(-1))
        down_button.clicked.connect(lambda: self.move_current(1))
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def move_current(self, direction: int) -> None:
        row = self.list_widget.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if new_row < 0 or new_row >= self.list_widget.count():
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(new_row, item)
        self.list_widget.setCurrentRow(new_row)

    def settings(self) -> list[dict]:
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            result.append(
                {
                    "key": item.data(Qt.UserRole),
                    "label": item.text(),
                    "visible": item.checkState() == Qt.Checked,
                }
            )
        return result


