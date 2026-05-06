from email import policy
from email.parser import BytesParser
from pathlib import Path
import re

from gerenciador_app.config import TEST_SMTP_INBOX_DIR


URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")


def _ensure_inbox_dir():
    TEST_SMTP_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_SMTP_INBOX_DIR


def _split_saved_email(target_path):
    raw_bytes = target_path.read_bytes()
    for marker in (b"\r\n\r\n", b"\n\n"):
        separator_index = raw_bytes.find(marker)
        if separator_index != -1:
            return raw_bytes[:separator_index], raw_bytes[separator_index + len(marker):]
    return raw_bytes, b""


def _extract_text(message):
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                return part.get_content().strip()
        return ""

    return message.get_content().strip()


def _extract_html(message):
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/html" and not part.get_filename():
                return part.get_content().strip()
        return ""

    if message.get_content_type() == "text/html":
        return message.get_content().strip()

    return ""


def _extract_links(*contents):
    links = []
    for content in contents:
        if not content:
            continue
        for link in URL_PATTERN.findall(content):
            if link not in links:
                links.append(link)
    return links


def _read_email_file(target_path):
    _, message_bytes = _split_saved_email(target_path)
    return BytesParser(policy=policy.default).parsebytes(message_bytes)


def _build_email_summary(target_path):
    message = _read_email_file(target_path)
    body = _extract_text(message)
    links = _extract_links(body, _extract_html(message))
    preview = body.replace("\n", " ").strip()

    return {
        "filename": target_path.name,
        "subject": message.get("Subject", "(Sem assunto)"),
        "from": message.get("From", ""),
        "to": message.get("To", ""),
        "date": message.get("Date", ""),
        "primary_link": links[0] if links else "",
        "preview": preview[:180] + ("..." if len(preview) > 180 else ""),
        "modified_at": target_path.stat().st_mtime,
    }


def listar_emails_teste():
    inbox_dir = _ensure_inbox_dir()
    emails = [
        _build_email_summary(path)
        for path in inbox_dir.glob("*.eml")
        if path.is_file()
    ]
    return sorted(emails, key=lambda email_item: email_item["modified_at"], reverse=True)


def obter_email_teste(filename):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise ValueError("Nome de arquivo inválido.")

    target_path = _ensure_inbox_dir() / safe_name
    if not target_path.exists() or not target_path.is_file():
        return None

    metadata_bytes, _ = _split_saved_email(target_path)
    message = _read_email_file(target_path)
    body = _extract_text(message)
    html_body = _extract_html(message)
    metadata_text = metadata_bytes.decode("utf-8", errors="replace")
    return {
        "filename": target_path.name,
        "subject": message.get("Subject", "(Sem assunto)"),
        "from": message.get("From", ""),
        "to": message.get("To", ""),
        "date": message.get("Date", ""),
        "body": body,
        "html_body": html_body,
        "links": _extract_links(body, html_body),
        "raw": target_path.read_text(encoding="utf-8", errors="replace"),
        "metadata": metadata_text,
    }
