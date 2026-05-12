import hashlib
import html
import re
import unicodedata
from pathlib import Path

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_title(path: Path) -> str:
    title = path.stem
    for prefix in ("1-s2.0-",):
        if title.startswith(prefix):
            title = title[len(prefix) :]
    title = title.replace("_", " ").replace("-", " ")
    return " ".join(title.split())


def useful_title(value: str) -> str:
    text = html.unescape(value or "")
    text = (
        text.replace("¡ä", "′")
        .replace("¡¯", "'")
        .replace("¡°", '"')
        .replace("¡±", '"')
        .replace("¡ª", "-")
        .replace("¡­", "...")
    )
    cleaned = []
    bad_chars = 0
    for char in text.replace("\x00", " "):
        category = unicodedata.category(char)
        if category.startswith("C"):
            if char in "\r\n\t":
                cleaned.append(" ")
            else:
                bad_chars += 1
            continue
        cleaned.append(char)
    title = " ".join("".join(cleaned).split())
    title = title.strip(" {[(<")
    title = title.rstrip(" {[(<")
    while title.endswith(("}", "]", ")")) and not title.startswith(title[-1].translate(str.maketrans("}])", "{[("))):
        title = title[:-1].rstrip()
    if len(title) < 8:
        return ""
    if bad_chars > max(2, len(title) // 8):
        return ""
    if "\ufffd" in title or "þÿ" in title or "ÿþ" in title:
        return ""
    lower = title.lower()
    if lower in {"untitled", "title", "references", "abstract", "no job name", "main_text", "main text"}:
        return ""
    if lower.startswith(("doi:", "doi ")):
        return ""
    if DOI_RE.fullmatch(title):
        return ""
    if lower.endswith((".pdf", ".doc", ".docx", ".eps", ".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        return ""
    if lower in {"crossmark_default", "crossmark_default.eps", "bpe_logo", "bpe_logo.eps"}:
        return ""
    if "crossmark" in lower and len(title) < 40:
        return ""
    if looks_like_pdf_internal_title(title):
        return ""
    return title


def looks_like_pdf_internal_title(value: str) -> bool:
    title = " ".join((value or "").split())
    lower = title.lower()
    if re.fullmatch(r"[a-z]{1,8}\d+[a-z0-9]*\s+\d+\.\.\d+", lower):
        return True
    if re.fullmatch(r"[a-z]{1,8}\d+[a-z0-9]*", lower) and not re.search(r"\s", lower):
        return True
    if re.fullmatch(r"(?:article|manuscript|paper|proof|galley)[-_ ]?\d+[a-z0-9._-]*", lower):
        return True
    return False


def title_needs_refresh(value: str) -> bool:
    title = " ".join((value or "").split())
    if not title:
        return True
    lower = title.lower()
    bad_markers = (
        "available online",
        "published by",
        "creative commons",
        "open access article",
        "contents lists available",
        "journal homepage",
    )
    if any(marker in lower for marker in bad_markers):
        return True
    if lower in {"no job name", "main_text", "main text"}:
        return True
    if title.endswith(("{", "[", "(")):
        return True
    if looks_like_pdf_internal_title(title):
        return True
    if len(title) > 180 and DOI_RE.search(title):
        return True
    return False


def looks_like_author_line(line: str) -> bool:
    if re.search(r"\b(JD|PhD|MSc|MD)\b", line):
        return True
    if "⁎" in line or "*" in line:
        return True
    if "&" in line and re.search(r"\b[A-Z]\.", line) and len(re.findall(r"\b[A-Z][A-Za-z'’.-]+\b", line)) >= 3:
        return True
    if "," in line and re.search(r"\d|\b[A-Z]\.", line):
        return True
    if re.search(r"\b[A-Z][A-Za-z'’.-]+(?:\s+[A-Z]\.)?\s+[A-Z][A-Za-z'’.-]+.*(?:\d|,)", line):
        return True
    return False


def decode_pdf_title_bytes(data: bytes) -> str:
    if data.startswith(b"\xfe\xff"):
        try:
            return useful_title(data[2:].decode("utf-16-be", errors="ignore"))
        except Exception:
            return ""
    if data.startswith(b"\xff\xfe"):
        try:
            return useful_title(data[2:].decode("utf-16-le", errors="ignore"))
        except Exception:
            return ""
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            title = useful_title(data.decode(encoding, errors="ignore"))
        except Exception:
            title = ""
        if title:
            return title
    return ""


def decode_pdf_literal(value: str) -> str:
    result = bytearray()
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            result.append(ord(char) & 0xFF)
            index += 1
            continue

        index += 1
        if index >= len(value):
            break
        escaped = value[index]
        if escaped in "01234567":
            digits = escaped
            index += 1
            for _ in range(2):
                if index < len(value) and value[index] in "01234567":
                    digits += value[index]
                    index += 1
                else:
                    break
            result.append(int(digits, 8) & 0xFF)
            continue
        replacements = {
            "n": b"\n",
            "r": b"\r",
            "t": b"\t",
            "b": b"\b",
            "f": b"\f",
            "(": b"(",
            ")": b")",
            "\\": b"\\",
        }
        if escaped in "\r\n":
            while index + 1 < len(value) and value[index + 1] in "\r\n":
                index += 1
        else:
            result.extend(replacements.get(escaped, escaped.encode("latin-1", errors="ignore")))
        index += 1
    return decode_pdf_title_bytes(bytes(result))


def decode_pdf_hex(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value)
    if len(cleaned) < 2:
        return ""
    if len(cleaned) % 2:
        cleaned = cleaned[:-1]
    try:
        data = bytes.fromhex(cleaned)
    except ValueError:
        return ""
    return decode_pdf_title_bytes(data)


def extract_pdf_title(path: Path) -> str:
    if path.suffix.lower() != ".pdf":
        return ""
    try:
        raw = path.read_bytes()[: 4 * 1024 * 1024]
        text = raw.decode("latin-1", errors="ignore")

        literal_match = re.search(r"/Title\s*\(((?:\\.|[^\\)]){1,800})\)", text, re.S)
        if literal_match:
            title = decode_pdf_literal(literal_match.group(1))
            if title and not title_needs_refresh(title):
                return title

        hex_match = re.search(r"/Title\s*<([0-9A-Fa-f\s]{2,1600})>", text, re.S)
        if hex_match:
            title = decode_pdf_hex(hex_match.group(1))
            if title and not title_needs_refresh(title):
                return title

        xmp_match = re.search(r"<dc:title>.*?<rdf:li[^>]*>(.*?)</rdf:li>", text, re.S | re.I)
        if xmp_match:
            title = re.sub(r"<.*?>", " ", xmp_match.group(1))
            title = (
                title.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", '"')
                .replace("&apos;", "'")
            )
            title = useful_title(title)
            if title and not title_needs_refresh(title):
                return title
    except Exception:
        pass
    return extract_pdf_title_from_first_page(path)


def extract_pdf_title_from_first_page(path: Path) -> str:
    try:
        from pypdf import PdfReader

        text = PdfReader(str(path)).pages[0].extract_text() or ""
    except Exception:
        return ""
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    skip_re = re.compile(
        r"^(available online|contents lists available|journal homepage|https?://|"
        r"\d{4}-\d{4}/|©|copyright|published by|this is an open access|journal of )",
        re.I,
    )
    title_lines = []
    for index, line in enumerate(lines[:24]):
        if skip_re.search(line):
            continue
        if DOI_RE.search(line) or "creativecommons.org" in line.lower():
            continue
        if re.search(r"\b(received|abstract|keywords?|article info)\b", line, re.I):
            break
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if title_lines and re.fullmatch(r"[a-z]\s*", next_line):
            break
        if title_lines and looks_like_author_line(line):
            break
        if title_lines and re.search(r"\b(University|Institute|Department|School|Center|Centre)\b", line):
            break
        if re.fullmatch(r"[a-z]\s*", line):
            continue
        title_lines.append(line)
        if len(" ".join(title_lines)) > 180:
            break
    return useful_title(" ".join(title_lines))


def initial_title(path: Path) -> str:
    return extract_pdf_title(path) or clean_title(path)


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)


def clean_doi(value: str) -> str:
    doi = " ".join((value or "").replace("\x00", " ").split())
    doi = doi.strip().strip("<>[]{}")
    for marker in (")/S/", ")/URI", ")/Author", ")/Title", "/S/URI", "/Author", "/Title"):
        if marker in doi:
            doi = doi.split(marker, 1)[0]
    if "/-/DC" in doi:
        doi = doi.split("/-/DC", 1)[0]
    doi = doi.rstrip(".,;:")
    while doi.endswith(")") and doi.count("(") < doi.count(")"):
        doi = doi[:-1]
    return doi


def extract_pdf_doi(path: Path) -> str:
    if path.suffix.lower() != ".pdf":
        return ""
    try:
        raw = path.read_bytes()[: 6 * 1024 * 1024]
    except Exception:
        return ""

    candidates = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        metadata = reader.metadata or {}
        for key, value in metadata.items():
            if str(key).lower().strip("/") == "doi":
                candidates.append(str(value))
        for page in reader.pages[:4]:
            page_text = page.extract_text() or ""
            candidates.extend(DOI_RE.findall(page_text))
            if candidates:
                break
    except Exception:
        pass

    for encoding in ("utf-8", "latin-1"):
        try:
            text = raw.decode(encoding, errors="ignore")
        except Exception:
            continue
        priority_patterns = [
            r"<prism:doi[^>]*>(.*?)</prism:doi>",
            r"<dc:identifier[^>]*>\s*doi:(.*?)</dc:identifier>",
            r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s<>\)]+)",
            r"doi:\s*(10\.\d{4,9}/[^\s<>\)]+)",
        ]
        for pattern in priority_patterns:
            for match in re.findall(pattern, text, re.I | re.S):
                candidates.append(match)
        candidates.extend(DOI_RE.findall(text))

    for value in candidates:
        doi = clean_doi(value)
        if doi:
            return doi
    return ""


def initial_doi(path: Path) -> str:
    return extract_pdf_doi(path)


def clean_publication_value(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<.*?>", " ", text)
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip(" ;,")
    if not text or len(text) < 3:
        return ""
    if DOI_RE.search(text) and len(text) < 40:
        return ""
    bad_values = {"untitled", "unknown", "none", "n/a"}
    if text.lower() in bad_values:
        return ""
    known_names = {
        "nutrients": "Nutrients",
        "glycobiology": "Glycobiology",
    }
    if text.lower() in known_names:
        return known_names[text.lower()]
    return text[:240]


def extract_journal_from_line(line: str) -> str:
    text = clean_publication_value(line)
    if not text:
        return ""
    if DOI_RE.search(text) or len(text) > 180:
        return ""
    affiliation_words = (
        "Institute",
        "University",
        "Department",
        "School",
        "Faculty",
        "Hospital",
        "Company",
        "Laboratory",
        "Centre",
        "Center",
        "Address",
    )
    if any(re.search(rf"\b{word}\b", text, re.I) for word in affiliation_words):
        return ""

    candidate = text
    candidate = re.sub(r"\s*\(\d{4}\).*$", "", candidate).strip()
    candidate = re.sub(r"\s+\d+\s*$", "", candidate).strip()
    candidate = re.sub(r"\s+Article\s*$", "", candidate, flags=re.I).strip()
    candidate = re.sub(r"\s+\d{4},\s*\d+.*$", "", candidate).strip()
    candidate = re.sub(r"\s+Vol\.\s*\d+.*$", "", candidate, flags=re.I).strip()
    candidate = re.sub(r"\s*\|\s*.*$", "", candidate).strip(" ;,")
    if not candidate or len(candidate) > 90:
        return ""

    journal_patterns = (
        r"^Journal of\b",
        r"^J\.\s",
        r"^Anal\.\s*Chem\.",
        r"^J\s+Pediatr\b",
        r"^Nutrients\b",
        r"^Glycobiology\b",
        r"\bJournal\b",
        r"\bBiomedical Analysis\b",
        r"\bFood Chemistry\b",
        r"\bPerinatology\b",
        r"\bPediatric Gastroenterology\b",
    )
    if any(re.search(pattern, candidate, re.I) for pattern in journal_patterns):
        return clean_publication_value(candidate)
    return ""


def infer_publisher(text: str) -> str:
    candidates = [
        ("Elsevier", r"\bElsevier\b"),
        ("Springer Nature", r"\b(Springer Nature|Springer Science|Springer-Verlag|Springer)\b"),
        ("Wiley", r"\b(Wiley|John Wiley)\b"),
        ("American Chemical Society", r"\b(American Chemical Society|Am\. Chem\. Soc\.|ACS Publications)\b"),
        ("Royal Society of Chemistry", r"\b(Royal Society of Chemistry|RSC Publishing)\b"),
        ("MDPI", r"\bMDPI\b"),
        ("Oxford University Press", r"\bOxford University Press\b"),
        ("Taylor & Francis", r"\b(Taylor & Francis|Informa UK)\b"),
        ("Nature Portfolio", r"\bNature Portfolio\b"),
    ]
    for name, pattern in candidates:
        if re.search(pattern, text, re.I):
            return name
    published_by = re.search(r"\bPublished by\s+([^.;\n\r]{3,90})", text, re.I)
    if published_by:
        return clean_publication_value(published_by.group(1))
    copyright_owner = re.search(r"(?:©|\(c\)|Copyright)\s*(?:\d{4}\s*)?([^.;\n\r]{3,90})", text, re.I)
    if copyright_owner:
        owner = clean_publication_value(copyright_owner.group(1))
        if owner and not owner.lower().startswith("the author"):
            return owner
    return ""


def extract_pdf_publication_info(path: Path) -> tuple[str, str]:
    if path.suffix.lower() != ".pdf":
        return "", ""

    journal = ""
    publisher = ""
    page_text = ""
    raw_text = ""
    try:
        raw = path.read_bytes()[: 8 * 1024 * 1024]
        raw_text = raw.decode("latin-1", errors="ignore")
    except Exception:
        raw_text = ""

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        metadata = reader.metadata or {}
        journal_keys = {
            "journal",
            "journaltitle",
            "publicationname",
            "prism:publicationname",
            "dc:source",
            "source",
        }
        publisher_keys = {"publisher", "dc:publisher", "prism:publisher"}
        for key, value in metadata.items():
            normalized_key = str(key).lower().strip("/")
            if not journal and normalized_key in journal_keys:
                journal = clean_publication_value(str(value))
            if not publisher and normalized_key in publisher_keys:
                publisher = clean_publication_value(str(value))
        for page in reader.pages[:2]:
            page_text += "\n" + (page.extract_text() or "")
    except Exception:
        pass

    search_text = "\n".join(part for part in (raw_text, page_text) if part)
    if not journal and raw_text:
        patterns = [
            r"<prism:publicationName[^>]*>(.*?)</prism:publicationName>",
            r"<prism:publicationname[^>]*>(.*?)</prism:publicationname>",
            r"<dc:source[^>]*>(.*?)</dc:source>",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_text, re.I | re.S)
            if match:
                journal = clean_publication_value(match.group(1))
                if journal:
                    break
    if not publisher and raw_text:
        for pattern in (r"<dc:publisher[^>]*>(.*?)</dc:publisher>", r"<prism:publisher[^>]*>(.*?)</prism:publisher>"):
            match = re.search(pattern, raw_text, re.I | re.S)
            if match:
                publisher = clean_publication_value(match.group(1))
                if publisher:
                    break

    if not journal:
        lines = [re.sub(r"\s+", " ", line).strip() for line in page_text.splitlines()]
        lines = [line for line in lines if line]
        for line in lines[:45]:
            if DOI_RE.search(line) or re.search(r"https?://doi\.org/", line, re.I):
                candidate = extract_journal_from_line(line)
                if candidate:
                    journal = candidate
                    break
        if not journal:
            for line in lines[:12] + lines[-20:]:
                candidate = extract_journal_from_line(line)
                if candidate:
                    journal = candidate
                    break

    if not publisher:
        publisher = infer_publisher(search_text)
    return journal, publisher


def initial_journal(path: Path) -> str:
    return extract_pdf_publication_info(path)[0]


def initial_publisher(path: Path) -> str:
    return extract_pdf_publication_info(path)[1]


def pdf_article_signals(path: Path) -> set[str]:
    signals = set()
    if path.suffix.lower() != ".pdf":
        return signals
    try:
        raw = path.read_bytes()[: 1024 * 1024]
        text = raw.decode("latin-1", errors="ignore")
    except Exception:
        text = ""
    if DOI_RE.search(text):
        signals.add("doi")
    if re.search(r"\b(abstract|summary|synopsis|keywords)\b", text, re.I):
        signals.add("article_text")
    if re.search(r"<dc:(title|creator|description)>|<prism:doi>|<prism:publicationName>", text, re.I):
        signals.add("metadata")
    return signals


def clean_abstract(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<.*?>", " ", text)
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()

    heading_match = re.search(r"\b(abstract|summary|synopsis)\b\s*[:.\-]?\s+", text, re.I)
    if heading_match:
        text = text[heading_match.end() :].strip()

    text = re.sub(r"^(abstract|summary)\s*[:.\-]?\s*", "", text, flags=re.I)
    text = re.sub(
        r"^First published as .*?\bDOI\s*:?\s*10\.\d{4,9}/[-._;()/:A-Z0-9]+\s*",
        "",
        text,
        flags=re.I,
    ).strip()
    text = re.sub(r"^/?\s*(available online|published(?: online)?)\s*[:.]?\s*[^A-Z]{0,300}", "", text, flags=re.I).strip()
    if len(text) < 40:
        return ""
    if len(text) < 160 and DOI_RE.search(text):
        return ""
    return text[:2500].strip()


def abstract_needs_refresh(value: str) -> bool:
    text = " ".join((value or "").split())
    if not text:
        return True
    lower = text.lower()
    if "/gid" in lower or re.search(r"^\W*(available online|published(?: online)?|first published as)\b", lower):
        return True
    if lower.startswith("of human milk macronutrients and measurement considerations"):
        return True
    if re.search(r"\babstract\b\s*[:.\-]?\s+", lower) and not lower.startswith("abstract"):
        return True
    if len(text) < 160 and ("doi:" in lower or DOI_RE.search(text)):
        return True
    if len(text) < 80:
        return True
    return False


def extract_abstract_from_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text or "")
    received_match = re.search(
        r"\bReceived\b.*?\baccepted\b.*?\b\d{4}\b\s*(.*?)(?=\bKeywords?\b|\bIntroduction\b|\b1\.?\s+Introduction\b)",
        normalized,
        re.I | re.S,
    )
    if received_match:
        abstract = clean_abstract(received_match.group(1))
        if abstract:
            return abstract

    lines = []
    for raw_line in (text or "").replace("\r", "\n").split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)

    heading_re = re.compile(r"^(abstract|summary|synopsis)\b|^abstract(?=article info)", re.I)
    stop_re = re.compile(
        r"^(introduction|1\.?\s+introduction|contents|specifications table|abbreviations|"
        r"article history|references|conflict of interest|copyright)\b",
        re.I,
    )
    for index, line in enumerate(lines):
        heading_match = heading_re.search(line)
        if not heading_match:
            continue

        collected = []
        remainder = line[heading_match.end() :].strip(" :.-")
        if remainder and not re.fullmatch(r"article info", remainder, re.I):
            collected.append(remainder)
        skipping_keywords = False

        for following in lines[index + 1 :]:
            lower = following.lower()
            if stop_re.search(following):
                break
            if re.match(r"^keywords?\b", following, re.I):
                skipping_keywords = True
                continue
            if skipping_keywords:
                looks_like_sentence = (
                    len(following) >= 70
                    or bool(re.search(r"\b(is|are|was|were|has|have|can|may|provides?|contains?)\b", lower))
                )
                if not looks_like_sentence:
                    continue
                skipping_keywords = False
            collected.append(following)
            abstract = clean_abstract(" ".join(collected))
            if len(abstract) >= 450:
                return abstract

        abstract = clean_abstract(" ".join(collected))
        if abstract:
            return abstract

    patterns = [
        r"\bAbstract\b\s*[:.\-]?\s*(.*?)(?=\bKeywords?\b|\bIndex Terms\b|\bIntroduction\b|\b1\.?\s+Introduction\b)",
        r"\bSummary\b\s*[:.\-]?\s*(.*?)(?=\bKeywords?\b|\bIntroduction\b|\b1\.?\s+Introduction\b)",
        r"\bSynopsis\b\s*[:.\-]?\s*(.*?)(?=\bKeywords?\b|\bIntroduction\b|\b1\.?\s+Introduction\b)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.I | re.S)
        if match:
            abstract = clean_abstract(match.group(1))
            if abstract:
                return abstract
    return extract_unlabeled_first_page_abstract(text)


def extract_unlabeled_first_page_abstract(text: str) -> str:
    lines = []
    for raw_line in (text or "").replace("\r", "\n").split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    if len(lines) < 6:
        return ""

    start = None
    affiliation_re = re.compile(
        r"\b(Institute|University|Department|Faculty|School|Center|Centre|Laborator|Council|"
        r"Hospital|Company|Corporation|Canada|USA|United States|China|Japan|Germany|France|"
        r"Kingdom|Australia|Netherlands|Spain|Italy)\b",
        re.I,
    )
    for index, line in enumerate(lines[:18]):
        if affiliation_re.search(line) and index + 1 < len(lines):
            start = index + 1
            break
    if start is None:
        for index, line in enumerate(lines[:18]):
            if line.startswith(("©", "(c)")) or re.search(r"\bThe Author\(s\)\b", line, re.I):
                start = index + 1
                break
    if start is None:
        return ""

    collected = []
    skipped_publication_block = False
    for index, line in enumerate(lines[start:], start=start):
        if re.search(r"https?://doi\.org/|doi\.org/", line, re.I):
            break
        if not collected and re.search(r"\b(Received|Accepted|First published|Published online)\b", line, re.I):
            skipped_publication_block = True
            continue
        if not collected and skipped_publication_block and DOI_RE.search(line):
            continue
        if re.search(r"\b(keywords?|introduction|references|figure\s+\d+|table\s+\d+)\b", line, re.I):
            break
        if line.startswith("* ") or line.lower().startswith("to whom correspondence"):
            break
        if DOI_RE.search(line) or re.search(r"\b(anal\. chem\.|j\.\s|vol\.|published on web|downloaded via)\b", line, re.I):
            break
        if index > start and len(" ".join(collected)) >= 450 and re.match(r"^(The|This|These|Here|In this|Recently|However|Human|Nuclear)\b", line):
            break
        collected.append(line)
        if len(" ".join(collected)) >= 1200:
            break

    abstract = clean_abstract(" ".join(collected))
    if len(abstract) < 180:
        return ""
    return abstract


def extract_xmp_abstract(text: str) -> str:
    patterns = [
        r"<dc:description>.*?<rdf:li[^>]*>(.*?)</rdf:li>",
        r"<dc:description[^>]*>(.*?)</dc:description>",
        r"<prism:teaser[^>]*>(.*?)</prism:teaser>",
        r"<xmp:Description[^>]*>(.*?)</xmp:Description>",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.S | re.I)
        if match:
            abstract = clean_abstract(match.group(1))
            if abstract:
                return abstract
    return ""


def extract_pdf_abstract(path: Path) -> str:
    if path.suffix.lower() != ".pdf":
        return ""
    signals = pdf_article_signals(path)
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        page_text = []
        for page in reader.pages[:3]:
            page_text.append(page.extract_text() or "")
        extracted_text = "\n".join(page_text)
        if re.search(
            r"\b(abstract|summary|synopsis)\b|abstract(?=article info)|\breceived\b.*?\baccepted\b",
            extracted_text,
            re.I | re.S,
        ):
            signals.add("article_text")
            abstract = extract_abstract_from_text(extracted_text)
            if abstract:
                return abstract
        abstract = extract_unlabeled_first_page_abstract(extracted_text)
        if abstract:
            signals.add("article_text")
            return abstract
    except Exception:
        pass

    if not signals:
        return ""
    try:
        raw = path.read_bytes()[: 8 * 1024 * 1024]
        text = raw.decode("latin-1", errors="ignore")
        abstract = extract_xmp_abstract(text)
        if abstract:
            return abstract
    except Exception:
        pass

    return ""


def initial_abstract(path: Path) -> str:
    return extract_pdf_abstract(path)
