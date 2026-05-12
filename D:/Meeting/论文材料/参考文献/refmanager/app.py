import sys

from .main_window import ReferenceManager
from .paths import APP_ICON_PATH, APP_NAME, APP_VERSION
from .qt_compat import QApplication, QIcon, exec_qt_app


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = ReferenceManager()
    window.show()
    return exec_qt_app(app)
