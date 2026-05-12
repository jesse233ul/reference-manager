import json
import sys
from datetime import datetime
from pathlib import Path

if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", ROOT_DIR))
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = ROOT_DIR
DATA_DIR = ROOT_DIR / "_reference_manager_qt"
DB_PATH = DATA_DIR / "references.sqlite3"
COLUMN_PATH = DATA_DIR / "columns.json"
SETTINGS_PATH = DATA_DIR / "settings.json"
DEFAULT_PAPERS_DIR = DATA_DIR / "papers"
DEFAULT_EXPORT_DIR = DATA_DIR
APP_ICON_PATH = RESOURCE_DIR / "app_icon.ico"
APP_NAME = "文献管理"
APP_VERSION = "1.0.0"
SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".ris", ".bib"}
APP_SETTINGS: dict[str, str] = {}


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_app_settings() -> dict[str, str]:
    DATA_DIR.mkdir(exist_ok=True)
    defaults = {
        "papers_dir": str(DEFAULT_PAPERS_DIR),
        "export_dir": str(DEFAULT_EXPORT_DIR),
    }
    if not SETTINGS_PATH.exists():
        return defaults
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    for key, value in defaults.items():
        saved.setdefault(key, value)
    return saved


def save_app_settings() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(APP_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")


def get_papers_dir() -> Path:
    return Path(APP_SETTINGS.get("papers_dir") or DEFAULT_PAPERS_DIR).expanduser()


def get_export_dir() -> Path:
    return Path(APP_SETTINGS.get("export_dir") or DEFAULT_EXPORT_DIR).expanduser()


def stored_reference_path(path: Path) -> str:
    try:
        return str(path.relative_to(DATA_DIR))
    except ValueError:
        return str(path)


def resolve_reference_path(rel_path: str) -> Path:
    path = Path(rel_path)
    if path.is_absolute():
        return path
    data_path = DATA_DIR / rel_path
    if data_path.exists():
        return data_path
    return ROOT_DIR / rel_path


def unique_target_path(directory: Path, file_name: str) -> Path:
    target = directory / file_name
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1



APP_SETTINGS.update(load_app_settings())
