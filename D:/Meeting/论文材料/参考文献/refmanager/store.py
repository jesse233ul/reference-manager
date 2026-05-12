import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .metadata import (
    abstract_needs_refresh,
    clean_abstract,
    clean_doi,
    clean_title,
    file_hash,
    extract_pdf_publication_info,
    initial_abstract,
    initial_doi,
    initial_title,
    looks_like_author_line,
    title_needs_refresh,
    useful_title,
)
from .paths import (
    DATA_DIR,
    SUPPORTED_EXTENSIONS,
    get_papers_dir,
    now_text,
    resolve_reference_path,
    stored_reference_path,
    unique_target_path,
)

@dataclass
class ColumnSpec:
    key: str
    label: str
    width: int
    visible: bool = True


COLUMNS = [
    ColumnSpec("ref_id", "ID", 74),
    ColumnSpec("title", "题名", 320),
    ColumnSpec("doi", "DOI", 180),
    ColumnSpec("journal", "期刊", 180, False),
    ColumnSpec("publisher", "出版社", 160, False),
    ColumnSpec("category", "类别", 120),
    ColumnSpec("abstract_text", "摘要", 320),
    ColumnSpec("manuscript_text", "对应我论文中原文", 300),
    ColumnSpec("file_name", "文件", 240),
    ColumnSpec("notes", "备注", 180, False),
    ColumnSpec("added_at", "添加时间", 150, False),
    ColumnSpec("size_mb", "大小 MB", 90, False),
]


class ReferenceStore:
    def __init__(self, db_path: Path):
        DATA_DIR.mkdir(exist_ok=True)
        get_papers_dir().mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                doi TEXT NOT NULL DEFAULT '',
                journal TEXT NOT NULL DEFAULT '',
                publisher TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                abstract_text TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                manuscript_text TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                rel_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL DEFAULT '',
                extension TEXT NOT NULL DEFAULT '',
                size_mb REAL NOT NULL DEFAULT 0,
                added_at TEXT NOT NULL DEFAULT '',
                modified TEXT NOT NULL DEFAULT '',
                sha256 TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self.ensure_column("doi", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column("journal", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column("publisher", "TEXT NOT NULL DEFAULT ''")
        self.ensure_column("abstract_text", "TEXT NOT NULL DEFAULT ''")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_refs_sha ON refs(sha256)")
        self.conn.commit()

    def ensure_column(self, name: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(refs)").fetchall()
        }
        if name not in columns:
            self.conn.execute(f"ALTER TABLE refs ADD COLUMN {name} {definition}")

    def all(self, query: str = "", category_filter: str | None = None) -> list[sqlite3.Row]:
        conditions = []
        params = []
        if query:
            q = f"%{query.strip()}%"
            conditions.append(
                """
                (title LIKE ? OR doi LIKE ? OR journal LIKE ? OR publisher LIKE ? OR category LIKE ? OR abstract_text LIKE ? OR tags_json LIKE ?
                 OR manuscript_text LIKE ? OR notes LIKE ? OR file_name LIKE ?)
                """
            )
            params.extend([q, q, q, q, q, q, q, q, q, q])
        if category_filter is not None:
            if category_filter == "":
                conditions.append("TRIM(category) = ''")
            else:
                conditions.append("category = ?")
                params.append(category_filter)

        sql = "SELECT * FROM refs"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id ASC"
        return list(self.conn.execute(sql, params))

    def get(self, ref_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM refs WHERE id = ?", (ref_id,)).fetchone()

    def categories(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT category FROM refs WHERE TRIM(category) <> '' ORDER BY category COLLATE NOCASE"
        )
        return [row["category"] for row in rows]

    def find_by_hash_or_path(self, sha: str, rel_path: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM refs WHERE sha256 = ? OR rel_path = ? LIMIT 1",
            (sha, rel_path),
        ).fetchone()

    def fill_missing_metadata(self, row: sqlite3.Row, file_path: Path) -> sqlite3.Row:
        updates = {}
        current_title = str(row["title"] or "")
        normalized_title = useful_title(current_title)
        fallback_title = clean_title(file_path)
        if normalized_title and normalized_title != current_title:
            updates["title"] = normalized_title
        if not normalized_title or normalized_title == fallback_title or title_needs_refresh(current_title):
            extracted_title = initial_title(file_path)
            if extracted_title and extracted_title != current_title:
                updates["title"] = extracted_title
        elif normalized_title:
            extracted_title = initial_title(file_path)
            if extracted_title and normalized_title.startswith(extracted_title):
                remainder = normalized_title[len(extracted_title) :].strip(" :-–—")
                if remainder and looks_like_author_line(remainder):
                    updates["title"] = extracted_title

        current_doi = clean_doi(str(row["doi"] or ""))
        if current_doi != str(row["doi"] or ""):
            updates["doi"] = current_doi
        if not current_doi:
            extracted_doi = initial_doi(file_path)
            if extracted_doi:
                updates["doi"] = extracted_doi
        if not str(row["journal"] or "").strip() or not str(row["publisher"] or "").strip():
            extracted_journal, extracted_publisher = extract_pdf_publication_info(file_path)
            if extracted_journal and not str(row["journal"] or "").strip():
                updates["journal"] = extracted_journal
            if extracted_publisher and not str(row["publisher"] or "").strip():
                updates["publisher"] = extracted_publisher
        if abstract_needs_refresh(str(row["abstract_text"] or "")):
            extracted_abstract = initial_abstract(file_path)
            if extracted_abstract:
                updates["abstract_text"] = extracted_abstract

        if updates:
            assignments = ", ".join(f"{key} = ?" for key in updates)
            values = list(updates.values()) + [row["id"]]
            self.conn.execute(f"UPDATE refs SET {assignments} WHERE id = ?", values)
            self.conn.commit()
            return self.get(int(row["id"]))
        return row

    def backfill_missing_metadata(self) -> int:
        changed = 0
        rows = list(
            self.conn.execute(
                """
                SELECT * FROM refs
                WHERE TRIM(title) = '' OR TRIM(COALESCE(doi, '')) = ''
                   OR title LIKE '%Available online%'
                   OR title LIKE '%Published by%'
                   OR title LIKE '%open access article%'
                   OR title LIKE '%{'
                   OR title IN ('No Job Name', 'Main_Text', 'Main Text')
                   OR TRIM(COALESCE(abstract_text, '')) = ''
                   OR abstract_text LIKE '%/gid%'
                   OR abstract_text LIKE '%Abstract:%'
                   OR abstract_text LIKE '% Abstract %'
                   OR abstract_text LIKE '; Published:%'
                   OR abstract_text LIKE '/ Published online:%'
                   OR abstract_text LIKE 'Available online%'
                   OR abstract_text LIKE 'First published as%'
                   OR abstract_text LIKE 'of human milk macronutrients%'
                   OR (LENGTH(TRIM(COALESCE(abstract_text, ''))) < 160 AND abstract_text LIKE '%doi:%')
                """
            )
        )
        for row in rows:
            if str(row["rel_path"]).startswith("__manual__/"):
                continue
            path = resolve_reference_path(row["rel_path"])
            if not path.exists():
                continue
            updated = self.fill_missing_metadata(row, path)
            if dict(updated) != dict(row):
                changed += 1
        return changed

    def add_file(self, source: Path) -> sqlite3.Row:
        source = source.resolve()
        if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型：{source.suffix}")
        sha = file_hash(source)

        papers_dir = get_papers_dir().resolve()
        papers_dir.mkdir(parents=True, exist_ok=True)
        target = source
        try:
            source.relative_to(papers_dir)
            already_managed = True
        except ValueError:
            already_managed = False

        if not already_managed:
            existing = self.conn.execute(
                "SELECT * FROM refs WHERE sha256 = ? LIMIT 1",
                (sha,),
            ).fetchone()
            if existing:
                return self.fill_missing_metadata(existing, source)

        if not already_managed:
            target = unique_target_path(papers_dir, source.name)
            shutil.copy2(source, target)

        rel_path = stored_reference_path(target)
        existing = self.find_by_hash_or_path(sha, rel_path)
        if existing:
            return self.fill_missing_metadata(existing, target)

        stat = target.stat()
        journal, publisher = extract_pdf_publication_info(target)
        self.conn.execute(
            """
            INSERT INTO refs (
                title, doi, journal, publisher, category, abstract_text, tags_json, manuscript_text, notes,
                rel_path, file_name, extension, size_mb, added_at, modified, sha256
            )
            VALUES (?, ?, ?, ?, '', ?, '[]', '', '', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                initial_title(target),
                initial_doi(target),
                journal,
                publisher,
                initial_abstract(target),
                rel_path,
                target.name,
                target.suffix.lower(),
                round(stat.st_size / 1024 / 1024, 2),
                now_text(),
                datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                sha,
            ),
        )
        self.conn.commit()
        return self.get(int(self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]))

    def add_manual(self) -> sqlite3.Row:
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        rel_path = f"__manual__/{stamp}"
        self.conn.execute(
            """
            INSERT INTO refs (
                title, doi, journal, publisher, category, abstract_text, tags_json, manuscript_text, notes,
                rel_path, file_name, extension, size_mb, added_at, modified, sha256
            )
            VALUES ('', '', '', '', '', '', '[]', '', '', ?, '', '', 0, ?, '', '')
            """,
            (rel_path, now_text()),
        )
        self.conn.commit()
        return self.get(int(self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]))

    def update(
        self,
        ref_id: int,
        title: str,
        doi: str,
        journal: str,
        publisher: str,
        category: str,
        abstract_text: str,
        manuscript_text: str,
        notes: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE refs
            SET title = ?, doi = ?, journal = ?, publisher = ?, category = ?, abstract_text = ?, manuscript_text = ?, notes = ?
            WHERE id = ?
            """,
            (
                title.strip(),
                clean_doi(doi),
                journal.strip(),
                publisher.strip(),
                category.strip(),
                clean_abstract(abstract_text) or abstract_text.strip(),
                manuscript_text.strip(),
                notes.strip(),
                ref_id,
            ),
        )
        self.conn.commit()

    def update_category(self, ref_id: int, category: str) -> None:
        self.conn.execute(
            "UPDATE refs SET category = ? WHERE id = ?",
            (category.strip(), ref_id),
        )
        self.conn.commit()

    def update_categories(self, ref_ids: list[int], category: str) -> int:
        ids = [int(ref_id) for ref_id in ref_ids]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cursor = self.conn.execute(
            f"UPDATE refs SET category = ? WHERE id IN ({placeholders})",
            [category.strip(), *ids],
        )
        self.conn.commit()
        return cursor.rowcount

    def clear_category(self, category: str) -> int:
        cursor = self.conn.execute(
            "UPDATE refs SET category = '' WHERE category = ?",
            (category.strip(),),
        )
        self.conn.commit()
        return cursor.rowcount

    def delete_record(self, ref_id: int) -> None:
        self.conn.execute("DELETE FROM refs WHERE id = ?", (ref_id,))
        self.conn.commit()

    def delete_reference(self, ref_id: int) -> tuple[Path | None, bool]:
        row = self.get(ref_id)
        if row is None:
            return None, False

        file_path = resolve_reference_path(row["rel_path"])
        deleted_file = False
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            deleted_file = True
            self.remove_empty_parent_dirs(file_path.parent)

        self.conn.execute("DELETE FROM refs WHERE id = ?", (ref_id,))
        self.renumber_ids()
        self.conn.commit()
        return file_path, deleted_file

    def remove_empty_parent_dirs(self, start_dir: Path) -> None:
        papers_dir = get_papers_dir().resolve()
        current = start_dir.resolve()
        while current != papers_dir:
            try:
                current.relative_to(papers_dir)
            except ValueError:
                return
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent

    def renumber_ids(self) -> None:
        rows = list(self.conn.execute("SELECT id FROM refs ORDER BY id ASC"))
        for new_id, row in enumerate(rows, start=1):
            self.conn.execute("UPDATE refs SET id = ? WHERE id = ?", (-new_id, row["id"]))
        for new_id in range(1, len(rows) + 1):
            self.conn.execute("UPDATE refs SET id = ? WHERE id = ?", (new_id, -new_id))
        self.conn.execute("DELETE FROM sqlite_sequence WHERE name = 'refs'")
        self.conn.execute("INSERT INTO sqlite_sequence(name, seq) VALUES('refs', ?)", (len(rows),))


