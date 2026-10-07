import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email


def load_email_config():
    config_file = Path(settings.EMAIL_CONFIG_FILE)
    if not config_file.exists():
        return {"sender_email": "", "recipient_email": "", "cc_email": ""}
    with config_file.open(encoding="utf-8") as file:
        config = json.load(file)
    return {
        "sender_email": config.get("sender_email", ""),
        "recipient_email": config.get("recipient_email", ""),
        "cc_email": config.get("cc_email", ""),
    }


def save_email_config(config):
    config_file = Path(settings.EMAIL_CONFIG_FILE)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with config_file.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


def load_sent_history():
    history_file = Path(settings.SENT_HISTORY_FILE)
    if not history_file.exists():
        return {"last_sent_date": None, "sent_timestamps": [], "archived_files": []}
    with history_file.open(encoding="utf-8") as file:
        history = json.load(file)
    if not isinstance(history, dict):
        raise ValueError(f"{history_file} does not contain a valid sent-history document.")
    return history


def save_sent_history(history):
    history_file = Path(settings.SENT_HISTORY_FILE)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2)


def get_new_entries(progress, sent_history):
    last_sent = sent_history.get("last_sent_date")
    new_entries = {}
    for section_name, section_data in progress["sections_tested"].items():
        entries = [
            entry
            for entry in section_data.get("entries", [])
            if last_sent is None or entry.get("timestamp", "") > last_sent
        ]
        if entries:
            new_entries[section_name] = entries
    return new_entries


def parse_addresses(value, required=False):
    addresses = [
        address.strip()
        for address in re.split(r"[,;]", value or "")
        if address.strip()
    ]
    if required and not addresses:
        raise ValueError("Enter at least one recipient email address.")
    for address in addresses:
        try:
            validate_email(address)
        except ValidationError as exc:
            raise ValueError(f"Invalid email address: {address}") from exc
    return addresses


def create_evidence_zip(new_entries):
    evidence_root = Path(settings.EVIDENCE_DIR).resolve()
    archive = BytesIO()
    included = set()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zip_file:
        for entries in new_entries.values():
            for entry in entries:
                for file_ref in entry.get("files", []):
                    relative_path = Path(file_ref)
                    file_path = (evidence_root / relative_path).resolve()
                    if not file_path.is_relative_to(evidence_root):
                        raise ValueError("An evidence path points outside the evidence directory.")
                    if not file_path.is_file():
                        raise FileNotFoundError(f"Evidence file is missing: {file_ref}")
                    archive_name = relative_path.as_posix()
                    if archive_name not in included:
                        zip_file.write(file_path, archive_name)
                        included.add(archive_name)
    if not included:
        return None
    archive.seek(0)
    return archive.getvalue()


def build_email_body(new_entries):
    lines = ["CTP Progress Update", f"Report date: {datetime.now().astimezone():%Y-%m-%d %H:%M %Z}", ""]
    for section_name, entries in new_entries.items():
        lines.extend([section_name, "-" * len(section_name)])
        for entry in entries:
            if entry.get("section_test"):
                lines.append(f"Section test completed: {entry.get('timestamp', 'unknown')}")
                continue
            lines.extend(
                [
                    f"Topic: {entry.get('topic', 'N/A')}",
                    f"Time: {entry.get('timestamp', 'unknown')}",
                    f"Work: {entry.get('work_description', '')}",
                ]
            )
            if entry.get("notes"):
                lines.append(f"Notes: {entry['notes']}")
            if entry.get("files"):
                lines.append(f"Evidence files attached: {len(entry['files'])}")
            lines.append("")
        lines.append("")
    if not any(entry.get("files") for entries in new_entries.values() for entry in entries):
        lines.append("No evidence files were attached.")
    return "\n".join(lines)


def create_email_draft(progress, config, sent_history):
    sender = (config.get("sender_email") or "").strip()
    if not sender:
        raise ValueError("Set the sender address in email settings before sending.")
    parse_addresses(sender, required=True)
    recipients = parse_addresses(config.get("recipient_email"), required=True)
    cc = parse_addresses(config.get("cc_email"))

    new_entries = get_new_entries(progress, sent_history)
    if not new_entries:
        raise ValueError("There are no new progress entries to send.")

    message = EmailMessage(
        subject=f"CTP Progress Update - {datetime.now():%Y-%m-%d}",
        body=build_email_body(new_entries),
        from_email=sender,
        to=recipients,
        cc=cc,
    )
    attachment = create_evidence_zip(new_entries)
    if attachment:
        message.attach("CTP_Evidence.zip", attachment, "application/zip")

    timestamps = [
        entry["timestamp"]
        for entries in new_entries.values()
        for entry in entries
        if entry.get("timestamp")
    ]
    return message.message().as_bytes(), max(timestamps) if timestamps else None
