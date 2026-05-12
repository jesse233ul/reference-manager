import csv
import ctypes
import json
from pathlib import Path

from .paths import (
    APP_ICON_PATH,
    APP_NAME,
    APP_SETTINGS,
    APP_VERSION,
    COLUMN_PATH,
    DB_PATH,
    get_export_dir,
    get_papers_dir,
    now_text,
    resolve_reference_path,
    save_app_settings,
)
from .qt_compat import (
    QAction,
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDesktopServices,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
    QToolBar,
    Qt,
    QUrl,
    QVBoxLayout,
    QWidget,
    exec_qt_dialog,
    exec_qt_menu,
)
from .store import COLUMNS, ReferenceStore
from .styles import APP_STYLE
from .widgets import CategoryTree, ColumnDialog, DropTable
from .windows_context import show_windows_file_context_menu

class ReferenceManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = ReferenceStore(DB_PATH)
        self.metadata_backfill_count = self.store.backfill_missing_metadata()
        self.current_id: int | None = None
        self.active_category_filter: str | None = None
        self.loading = False
        self.applying_column_settings = False
        self.column_settings = self.load_column_settings()

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(1280, 780)
        self.setMinimumSize(840, 520)
        self.setAcceptDrops(True)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索题名、DOI、期刊、出版社、类别、摘要、原文、备注")
        self.category_tree = CategoryTree()
        self.table = DropTable()
        self.title_edit = QLineEdit()
        self.doi_edit = QLineEdit()
        self.doi_edit.setPlaceholderText("自动读取 DOI，也可手动修改")
        self.journal_edit = QLineEdit()
        self.journal_edit.setPlaceholderText("自动读取期刊，也可手动修改")
        self.publisher_edit = QLineEdit()
        self.publisher_edit.setPlaceholderText("自动读取出版社，也可手动修改")
        self.category_edit = QComboBox()
        self.category_edit.setEditable(True)
        self.category_edit.setInsertPolicy(QComboBox.NoInsert)
        self.category_edit.lineEdit().setPlaceholderText("输入或选择类别")
        self.abstract_edit = QPlainTextEdit()
        self.abstract_edit.setPlaceholderText("自动读取 PDF 摘要，也可手动修改")
        self.manuscript_edit = QPlainTextEdit()
        self.notes_edit = QPlainTextEdit()
        self.path_label = QLabel("")
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_label.setWordWrap(True)
        self.path_label.setMinimumWidth(0)
        self.status = QLabel("拖入文献文件即可添加")

        self.build_ui()
        self.apply_style()
        self.connect_signals()
        self.refresh_table()

    def build_ui(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setMinimumWidth(0)
        toolbar.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.addToolBar(toolbar)

        add_action = QAction("添加文件", self)
        manual_action = QAction("新增文献", self)
        open_action = QAction("打开文件", self)
        delete_action = QAction("删除文献", self)
        save_action = QAction("保存", self)
        export_action = QAction("导出", self)
        columns_action = QAction("显示列", self)
        papers_dir_action = QAction("论文目录", self)
        export_dir_action = QAction("导出目录", self)
        toolbar.addAction(add_action)
        toolbar.addAction(manual_action)
        toolbar.addAction(open_action)
        toolbar.addAction(delete_action)
        toolbar.addSeparator()
        toolbar.addAction(save_action)
        toolbar.addAction(export_action)
        toolbar.addAction(columns_action)
        toolbar.addSeparator()
        toolbar.addAction(papers_dir_action)
        toolbar.addAction(export_dir_action)

        self.add_action = add_action
        self.manual_action = manual_action
        self.open_action = open_action
        self.delete_action = delete_action
        self.save_action = save_action
        self.export_action = export_action
        self.columns_action = columns_action
        self.papers_dir_action = papers_dir_action
        self.export_dir_action = export_dir_action

        left = QWidget()
        left.setMinimumWidth(460)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 8, 16)
        left_layout.setSpacing(10)

        category_panel = QFrame()
        category_panel.setObjectName("categoryPanel")
        category_panel.setMinimumWidth(150)
        category_layout = QVBoxLayout(category_panel)
        category_layout.setContentsMargins(0, 0, 8, 0)
        category_layout.setSpacing(8)
        category_title = QLabel("分类")
        category_title.setObjectName("sideTitle")
        category_layout.addWidget(category_title)
        category_layout.addWidget(self.category_tree, 1)

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(10)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索"))
        search_row.addWidget(self.search_box, 1)
        table_layout.addLayout(search_row)

        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c.label for c in COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.setDragEnabled(True)
        self.table.setDragDropMode(QAbstractItemView.DragDrop)
        self.table.setDefaultDropAction(Qt.MoveAction)
        table_layout.addWidget(self.table, 1)
        table_layout.addWidget(self.status)

        left_splitter = QSplitter()
        left_splitter.addWidget(category_panel)
        left_splitter.addWidget(table_panel)
        left_splitter.setSizes([170, 590])
        left_splitter.setChildrenCollapsible(False)
        left_layout.addWidget(left_splitter, 1)

        right = QFrame()
        right.setObjectName("detailPanel")
        right.setMinimumWidth(300)
        right.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(10)

        title = QLabel("文献信息")
        title.setObjectName("panelTitle")
        right_layout.addWidget(title)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setColumnStretch(1, 1)
        form.addWidget(QLabel("题名"), 0, 0)
        form.addWidget(self.title_edit, 0, 1)
        form.addWidget(QLabel("DOI"), 1, 0)
        form.addWidget(self.doi_edit, 1, 1)
        form.addWidget(QLabel("期刊"), 2, 0)
        form.addWidget(self.journal_edit, 2, 1)
        form.addWidget(QLabel("出版社"), 3, 0)
        form.addWidget(self.publisher_edit, 3, 1)
        form.addWidget(QLabel("类别"), 4, 0)
        form.addWidget(self.category_edit, 4, 1)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("摘要"))
        self.abstract_edit.setMinimumHeight(130)
        self.abstract_edit.setMaximumHeight(220)
        right_layout.addWidget(self.abstract_edit)

        right_layout.addWidget(QLabel("对应我论文中原文"))
        self.manuscript_edit.setPlaceholderText("把这篇文献对应支撑的论文原句写在这里")
        right_layout.addWidget(self.manuscript_edit, 2)

        right_layout.addWidget(QLabel("备注"))
        self.notes_edit.setPlaceholderText("可记录引用理由、页码、待核查事项等")
        right_layout.addWidget(self.notes_edit, 1)

        self.path_label.setObjectName("pathLabel")
        right_layout.addWidget(self.path_label)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([760, 420])
        splitter.setChildrenCollapsible(False)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        self.setCentralWidget(splitter)

    def apply_style(self) -> None:
        QApplication.instance().setStyleSheet(APP_STYLE)

    def connect_signals(self) -> None:
        self.add_action.triggered.connect(self.add_files_dialog)
        self.manual_action.triggered.connect(self.add_manual_reference)
        self.open_action.triggered.connect(self.open_current_file)
        self.delete_action.triggered.connect(self.delete_current_record)
        self.save_action.triggered.connect(self.save_current)
        self.export_action.triggered.connect(self.export_files)
        self.columns_action.triggered.connect(self.show_column_dialog)
        self.papers_dir_action.triggered.connect(self.choose_papers_dir)
        self.export_dir_action.triggered.connect(self.choose_export_dir)
        self.search_box.textChanged.connect(self.refresh_table)
        self.category_tree.category_selected.connect(self.set_category_filter)
        self.category_tree.category_dropped.connect(self.move_selected_reference_to_category)
        self.category_tree.files_dropped.connect(self.add_files_to_category)
        self.category_tree.delete_category_requested.connect(self.delete_category)
        self.table.files_dropped.connect(self.add_files)
        self.table.itemSelectionChanged.connect(self.load_selected)
        self.table.cellDoubleClicked.connect(lambda *_: self.open_current_file())
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        header = self.table.horizontalHeader()
        header.sectionMoved.connect(lambda *_: self.save_column_settings())
        header.sectionResized.connect(lambda *_: self.save_column_settings())

        self.title_edit.textChanged.connect(self.mark_dirty)
        self.doi_edit.textChanged.connect(self.mark_dirty)
        self.journal_edit.textChanged.connect(self.mark_dirty)
        self.publisher_edit.textChanged.connect(self.mark_dirty)
        self.category_edit.currentTextChanged.connect(self.mark_dirty)
        self.abstract_edit.textChanged.connect(self.mark_dirty)
        self.manuscript_edit.textChanged.connect(self.mark_dirty)
        self.notes_edit.textChanged.connect(self.mark_dirty)

    def load_column_settings(self) -> list[dict]:
        defaults = [
            {"key": c.key, "label": c.label, "visible": c.visible, "width": c.width, "order": i}
            for i, c in enumerate(COLUMNS)
        ]
        if not COLUMN_PATH.exists():
            return defaults
        try:
            saved = json.loads(COLUMN_PATH.read_text(encoding="utf-8"))
            by_key = {item["key"]: item for item in saved}
            merged = []
            for default in defaults:
                value = dict(default)
                if default["key"] in by_key:
                    old = by_key[default["key"]]
                    value["visible"] = bool(old.get("visible", value["visible"]))
                    old_width = int(old.get("width", value["width"]))
                    value["width"] = old_width if old_width >= 40 else value["width"]
                    value["order"] = int(old.get("order", value["order"]))
                merged.append(value)
            return sorted(merged, key=lambda x: x["order"])
        except Exception:
            return defaults

    def apply_column_settings(self) -> None:
        by_key = {c.key: i for i, c in enumerate(COLUMNS)}
        self.applying_column_settings = True
        try:
            ordered = sorted(self.column_settings, key=lambda x: x["order"])
            for setting in ordered:
                index = by_key[setting["key"]]
                self.table.setColumnHidden(index, False)
                self.table.setColumnWidth(index, max(40, int(setting["width"])))
            for order, setting in enumerate(ordered):
                index = by_key[setting["key"]]
                visual = self.table.horizontalHeader().visualIndex(index)
                if visual != order:
                    self.table.horizontalHeader().moveSection(visual, order)
            for setting in ordered:
                index = by_key[setting["key"]]
                self.table.setColumnHidden(index, not setting["visible"])
        finally:
            self.applying_column_settings = False

    def save_column_settings(self) -> None:
        if self.applying_column_settings:
            return
        by_key = {c.key: i for i, c in enumerate(COLUMNS)}
        existing_widths = {s["key"]: max(40, int(s.get("width", 0) or 0)) for s in self.column_settings}
        default_widths = {c.key: c.width for c in COLUMNS}
        settings = []
        for c in COLUMNS:
            index = by_key[c.key]
            visible = not self.table.isColumnHidden(index)
            current_width = self.table.columnWidth(index)
            if current_width < 40:
                current_width = existing_widths.get(c.key, default_widths[c.key])
            settings.append(
                {
                    "key": c.key,
                    "label": c.label,
                    "visible": visible,
                    "width": current_width,
                    "order": self.table.horizontalHeader().visualIndex(index),
                }
            )
        self.column_settings = sorted(settings, key=lambda x: x["order"])
        self.persist_column_settings()

    def persist_column_settings(self) -> None:
        COLUMN_PATH.write_text(json.dumps(self.column_settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def choose_papers_dir(self) -> None:
        current = str(get_papers_dir())
        selected = QFileDialog.getExistingDirectory(self, "选择论文存储目录", current)
        if not selected:
            return
        path = Path(selected)
        path.mkdir(parents=True, exist_ok=True)
        APP_SETTINGS["papers_dir"] = str(path)
        save_app_settings()
        self.status.setText(f"论文存储目录已设置为：{path}")

    def choose_export_dir(self) -> None:
        current = str(get_export_dir())
        selected = QFileDialog.getExistingDirectory(self, "选择默认导出目录", current)
        if not selected:
            return
        path = Path(selected)
        path.mkdir(parents=True, exist_ok=True)
        APP_SETTINGS["export_dir"] = str(path)
        save_app_settings()
        self.status.setText(f"默认导出目录已设置为：{path}")

    def show_column_dialog(self) -> None:
        self.save_column_settings()
        dialog = ColumnDialog(self.column_settings, self)
        if exec_qt_dialog(dialog) != QDialog.Accepted:
            return
        default_widths = {c.key: c.width for c in COLUMNS}
        old_widths = {
            s["key"]: max(40, int(s.get("width", 0) or default_widths.get(s["key"], 120)))
            for s in self.column_settings
        }
        self.column_settings = []
        for order, setting in enumerate(dialog.settings()):
            setting["order"] = order
            setting["width"] = old_widths.get(setting["key"], 120)
            self.column_settings.append(setting)
        self.apply_column_settings()
        self.persist_column_settings()

    def refresh_table(self) -> None:
        selected_id = self.current_id
        rows = self.store.all(self.search_box.text().strip(), self.active_category_filter)
        self.update_category_options()
        self.update_category_tree()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = {
                "ref_id": f"R{row['id']:04d}",
                "title": row["title"],
                "doi": row["doi"],
                "journal": row["journal"],
                "publisher": row["publisher"],
                "category": row["category"],
                "abstract_text": row["abstract_text"],
                "manuscript_text": row["manuscript_text"],
                "file_name": row["file_name"],
                "notes": row["notes"],
                "added_at": row["added_at"],
                "size_mb": str(row["size_mb"]),
            }
            for col_index, column in enumerate(COLUMNS):
                item = QTableWidgetItem(values[column.key])
                item.setData(Qt.UserRole, row["id"])
                self.table.setItem(row_index, col_index, item)

        self.apply_column_settings()
        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True)

        if selected_id is not None:
            self.select_row_by_id(selected_id)
        elif rows:
            self.table.selectRow(0)
        if self.active_category_filter is None:
            scope = "全部文献"
        elif self.active_category_filter == "":
            scope = "未分类"
        else:
            scope = self.active_category_filter
        backfill_text = ""
        if getattr(self, "metadata_backfill_count", 0):
            backfill_text = f" 已自动补全 {self.metadata_backfill_count} 条元数据。"
            self.metadata_backfill_count = 0
        self.status.setText(f"{scope}：共 {len(rows)} 条记录。拖入文件可继续添加。{backfill_text}")

    def update_category_options(self) -> None:
        current = self.category_edit.currentText()
        was_loading = self.loading
        self.loading = True
        self.category_edit.blockSignals(True)
        try:
            self.category_edit.clear()
            categories = self.store.categories()
            if categories:
                self.category_edit.addItems(categories)
            self.category_edit.setCurrentText(current)
        finally:
            self.category_edit.blockSignals(False)
            self.loading = was_loading

    def update_category_tree(self) -> None:
        self.category_tree.refresh(self.store.categories(), self.active_category_filter)

    def set_category_filter(self, category: str | None) -> None:
        self.save_current(silent=True)
        self.active_category_filter = category
        self.current_id = None
        self.refresh_table()

    def move_selected_reference_to_category(self, category: str) -> None:
        ref_ids = self.selected_ids()
        if not ref_ids:
            return
        self.save_current(silent=True)
        self.change_references_category(ref_ids, category)

    def change_reference_category(self, ref_id: int, category: str) -> None:
        self.change_references_category([ref_id], category)

    def change_references_category(self, ref_ids: list[int], category: str) -> None:
        ids = [int(ref_id) for ref_id in ref_ids]
        if not ids:
            return
        changed = self.store.update_categories(ids, category)
        if self.current_id in ids:
            was_loading = self.loading
            self.loading = True
            try:
                self.category_edit.setCurrentText(category)
            finally:
                self.loading = was_loading
        self.refresh_table()
        self.select_rows_by_ids(ids)
        target = category or "未分类"
        if changed == 1:
            self.status.setText(f"已将 R{ids[0]:04d} 移动到：{target}")
        else:
            self.status.setText(f"已将 {changed} 条文献移动到：{target}")

    def delete_category(self, category: str) -> None:
        category = category.strip()
        if not category:
            return
        count = len(self.store.all(category_filter=category))
        answer = QMessageBox.question(
            self,
            "删除分类",
            f"确定删除分类“{category}”吗？\n该分类下 {count} 条文献会归入“未分类”，论文文件不会删除。",
        )
        if answer != QMessageBox.Yes:
            return
        self.save_current(silent=True)
        changed = self.store.clear_category(category)
        if self.active_category_filter == category:
            self.active_category_filter = ""
            self.current_id = None
        if self.category_edit.currentText().strip() == category:
            was_loading = self.loading
            self.loading = True
            try:
                self.category_edit.setCurrentText("")
            finally:
                self.loading = was_loading
        self.refresh_table()
        self.status.setText(f"已删除分类“{category}”，{changed} 条文献已归入未分类")

    def clear_details(self) -> None:
        was_loading = self.loading
        self.loading = True
        try:
            self.current_id = None
            self.title_edit.clear()
            self.doi_edit.clear()
            self.journal_edit.clear()
            self.publisher_edit.clear()
            self.category_edit.setCurrentText("")
            self.abstract_edit.clear()
            self.manuscript_edit.clear()
            self.notes_edit.clear()
            self.path_label.clear()
        finally:
            self.loading = was_loading

    def select_row_by_id(self, ref_id: int) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == ref_id:
                self.table.selectRow(row)
                self.load_reference(ref_id)
                return

    def select_rows_by_ids(self, ref_ids: list[int]) -> None:
        ids = {int(ref_id) for ref_id in ref_ids}
        self.table.clearSelection()
        first_id = None
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) in ids:
                self.table.setRangeSelected(
                    QTableWidgetSelectionRange(row, 0, row, self.table.columnCount() - 1),
                    True,
                )
                if first_id is None:
                    first_id = int(item.data(Qt.UserRole))
        if first_id is not None:
            self.load_reference(first_id)

    def selected_id(self) -> int | None:
        ids = self.selected_ids()
        if not ids:
            return None
        return ids[0]

    def selected_ids(self) -> list[int]:
        return self.table.selected_ids()

    def load_selected(self) -> None:
        ref_id = self.selected_id()
        if ref_id is None:
            return
        self.load_reference(ref_id)

    def load_reference(self, ref_id: int) -> None:
        if self.current_id is not None and self.current_id != ref_id:
            self.save_current(silent=True)
        row = self.store.get(ref_id)
        if row is None:
            return
        self.loading = True
        try:
            self.current_id = ref_id
            self.title_edit.setText(row["title"])
            self.doi_edit.setText(row["doi"])
            self.journal_edit.setText(row["journal"])
            self.publisher_edit.setText(row["publisher"])
            self.title_edit.setCursorPosition(0)
            self.doi_edit.setCursorPosition(0)
            self.journal_edit.setCursorPosition(0)
            self.publisher_edit.setCursorPosition(0)
            self.category_edit.setCurrentText(row["category"])
            self.abstract_edit.setPlainText(row["abstract_text"])
            self.manuscript_edit.setPlainText(row["manuscript_text"])
            self.notes_edit.setPlainText(row["notes"])
            self.path_label.setText(str(resolve_reference_path(row["rel_path"])))
        finally:
            self.loading = False

    def mark_dirty(self) -> None:
        if not self.loading and self.current_id is not None:
            self.status.setText("有未保存修改")

    def save_current(self, silent: bool = False) -> None:
        if self.loading or self.current_id is None:
            return
        self.store.update(
            self.current_id,
            self.title_edit.text(),
            self.doi_edit.text(),
            self.journal_edit.text(),
            self.publisher_edit.text(),
            self.category_edit.currentText(),
            self.abstract_edit.toPlainText(),
            self.manuscript_edit.toPlainText(),
            self.notes_edit.toPlainText(),
        )
        if not silent:
            self.update_category_options()
            self.refresh_table()
            self.select_row_by_id(self.current_id)
            self.status.setText("已保存")

    def add_files_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文献文件",
            str(ROOT_DIR),
            "Reference files (*.pdf *.doc *.docx *.txt *.ris *.bib);;All files (*.*)",
        )
        self.add_files([Path(p) for p in paths])

    def add_files(self, paths: list[Path], category: str | None = None) -> None:
        if not paths:
            return
        self.save_current(silent=True)
        self.clear_details()
        last_id = None
        errors = []
        for path in paths:
            try:
                row = self.store.add_file(path)
                last_id = int(row["id"])
                if category is not None:
                    self.store.update_category(last_id, category)
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self.refresh_table()
        if last_id:
            self.select_row_by_id(last_id)
        if category is not None and not errors:
            target = category or "未分类"
            self.status.setText(f"已添加到：{target}")
        if errors:
            QMessageBox.warning(self, "部分文件添加失败", "\n".join(errors[:8]))

    def add_files_to_category(self, paths: list[Path], category: str | None) -> None:
        self.add_files(paths, category)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(Path(url.toLocalFile()))
        if files:
            self.add_files(files)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def add_manual_reference(self) -> None:
        self.save_current(silent=True)
        self.clear_details()
        row = self.store.add_manual()
        new_id = int(row["id"])
        self.refresh_table()
        self.select_row_by_id(new_id)
        self.title_edit.setFocus()
        self.status.setText("已新增空白文献；填写右侧信息后点击保存")

    def reference_file_for_opening(self, ref_id: int) -> Path | None:
        row = self.store.get(ref_id)
        if row is None:
            return None
        if str(row["rel_path"]).startswith("__manual__/"):
            QMessageBox.information(self, "没有原文文件", "这是一条手动新增的文献记录，没有关联原文文件。")
            return None
        path = resolve_reference_path(row["rel_path"])
        if not path.exists():
            QMessageBox.warning(self, "文件不存在", str(path))
            return None
        return path

    def show_table_context_menu(self, position) -> None:
        item = self.table.itemAt(position)
        if item is None:
            return
        clicked_id = item.data(Qt.UserRole)
        selected_ids = self.selected_ids()
        if clicked_id not in selected_ids:
            self.table.selectRow(item.row())
            selected_ids = self.selected_ids()
        ref_id = self.selected_id()
        if ref_id is None:
            return
        row = self.store.get(ref_id)
        if row is None:
            return
        path = None
        if not str(row["rel_path"]).startswith("__manual__/"):
            candidate = resolve_reference_path(row["rel_path"])
            if candidate.exists():
                path = candidate
        global_position = self.table.viewport().mapToGlobal(position)
        menu = QMenu(self)
        open_with_action = menu.addAction("打开方式")
        locate_action = menu.addAction("定位到论文保存的文档")
        bulk_count = len(selected_ids)
        if bulk_count > 1:
            open_with_action.setText("打开方式（当前行）")
            locate_action.setText("定位到论文保存的文档（当前行）")
        if path is None:
            open_with_action.setEnabled(False)
            locate_action.setEnabled(False)
        category_menu = menu.addMenu("更改分类")
        category_actions = {}
        uncategorized_action = category_menu.addAction("未分类")
        category_actions[uncategorized_action] = ""
        categories = self.store.categories()
        if categories:
            category_menu.addSeparator()
        for category in categories:
            category_action = category_menu.addAction(category)
            category_actions[category_action] = category
        action = exec_qt_menu(menu, global_position)
        if action == open_with_action:
            shown = show_windows_file_context_menu(
                path,
                int(self.winId()),
                global_position.x(),
                global_position.y(),
            )
            if not shown:
                QMessageBox.warning(self, "打开失败", "无法调用 Windows 打开方式菜单。")
        elif action == locate_action:
            self.show_current_file_in_explorer()
        elif action in category_actions:
            self.save_current(silent=True)
            self.change_references_category(selected_ids, category_actions[action])
            return
        self.refresh_table()

    def open_current_file(self) -> None:
        ref_id = self.selected_id()
        if ref_id is None:
            return
        path = self.reference_file_for_opening(ref_id)
        if path is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def show_current_file_in_explorer(self) -> None:
        ref_id = self.selected_id()
        if ref_id is None:
            return
        path = self.reference_file_for_opening(ref_id)
        if path is None:
            return
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "open",
            "explorer.exe",
            f'/select,"{path}"',
            None,
            1,
        )

    def delete_current_record(self) -> None:
        ref_ids = self.selected_ids()
        if not ref_ids:
            return
        rows = [self.store.get(ref_id) for ref_id in ref_ids]
        rows = [row for row in rows if row is not None]
        if not rows:
            return
        if len(rows) == 1:
            row = rows[0]
            path = resolve_reference_path(row["rel_path"])
            if str(row["rel_path"]).startswith("__manual__/"):
                detail = "这是一条手动新增的文献记录，没有关联原文文件。"
            else:
                detail = str(path)
            message = f"将删除数据库记录和原文文件：\n{detail}\n\n确定删除吗？"
        else:
            sample = "\n".join(f"R{row['id']:04d} {row['title']}" for row in rows[:6])
            if len(rows) > 6:
                sample += f"\n……另有 {len(rows) - 6} 条"
            message = f"将删除 {len(rows)} 条文献的数据库记录和原文文件：\n{sample}\n\n确定删除吗？"
        answer = QMessageBox.question(
            self,
            "删除文献",
            message,
        )
        if answer != QMessageBox.Yes:
            return
        deleted_files = 0
        deleted_records = 0
        try:
            for ref_id in sorted(ref_ids, reverse=True):
                _, deleted_file = self.store.delete_reference(ref_id)
                deleted_records += 1
                if deleted_file:
                    deleted_files += 1
        except Exception as exc:
            QMessageBox.warning(self, "删除失败", str(exc))
            return
        self.current_id = None
        self.refresh_table()
        if deleted_records == 1:
            if deleted_files:
                self.status.setText("已删除 1 条文献和原文文件")
            else:
                self.status.setText("已删除 1 条记录；原文文件未找到或已不存在")
        else:
            self.status.setText(f"已删除 {deleted_records} 条记录，其中 {deleted_files} 个原文文件已删除")

    def export_files(self) -> None:
        self.save_current(silent=True)
        selected = QFileDialog.getExistingDirectory(self, "选择导出目录", str(get_export_dir()))
        if not selected:
            return
        export_dir = Path(selected)
        export_dir.mkdir(parents=True, exist_ok=True)
        APP_SETTINGS["export_dir"] = str(export_dir)
        save_app_settings()
        rows = self.store.all()
        csv_path = export_dir / "references.csv"
        md_path = export_dir / "references.md"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "题名", "DOI", "期刊", "出版社", "类别", "摘要", "对应我论文中原文", "文件", "备注", "添加时间"])
            for row in rows:
                writer.writerow(
                    [
                        f"R{row['id']:04d}",
                        row["title"],
                        row["doi"],
                        row["journal"],
                        row["publisher"],
                        row["category"],
                        row["abstract_text"],
                        row["manuscript_text"],
                        row["file_name"],
                        row["notes"],
                        row["added_at"],
                    ]
                )

        lines = [
            "# Reference Manager",
            "",
            f"Exported: {now_text()}",
            "",
            "| ID | 题名 | DOI | 期刊 | 出版社 | 类别 | 摘要 | 对应我论文中原文 | 文件 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            values = [
                f"R{row['id']:04d}",
                row["title"],
                row["doi"],
                row["journal"],
                row["publisher"],
                row["category"],
                row["abstract_text"].replace("\n", " "),
                row["manuscript_text"].replace("\n", " "),
                row["file_name"],
                row["notes"].replace("\n", " "),
            ]
            values = [str(v).replace("|", "\\|") for v in values]
            lines.append("| " + " | ".join(values) + " |")
        md_path.write_text("\n".join(lines), encoding="utf-8")
        QMessageBox.information(self, "导出完成", f"已导出：\n{csv_path}\n{md_path}")

    def closeEvent(self, event) -> None:
        self.save_current(silent=True)
        self.save_column_settings()
        super().closeEvent(event)


