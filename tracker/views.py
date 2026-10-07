from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ctp_tracker import SECTIONS

from .email_service import (
    get_new_entries,
    load_email_config,
    load_sent_history,
    parse_addresses,
    create_email_draft,
    save_sent_history,
    save_email_config,
)
from .storage import load_progress, save_progress


def dashboard(request):
    progress = load_progress()
    sections = []
    completed_count = 0

    for section_id, section_info in SECTIONS.items():
        section_data = progress["sections_tested"].get(
            section_info["name"], {"status": "not_started", "entries": []}
        )
        if section_data["status"] == "tested":
            completed_count += 1
        sections.append(
            {
                "id": section_id,
                "name": section_info["name"],
                "topics": section_info["topics"],
                "data": section_data,
            }
        )

    email_config = load_email_config()
    sent_history = load_sent_history()
    return render(
        request,
        "tracker/dashboard.html",
        {
            "sections": sections,
            "topic_map": {
                section_id: section_info["topics"]
                for section_id, section_info in SECTIONS.items()
            },
            "total_sections": len(SECTIONS),
            "completed_count": completed_count,
            "completion_percent": round(completed_count / len(SECTIONS) * 100),
            "email_config": email_config,
            "email_configured": bool(
                email_config["sender_email"] and email_config["recipient_email"]
            ),
            "has_new_entries": bool(get_new_entries(progress, sent_history)),
            "has_pending_draft": bool(request.session.get("pending_email_draft_cutoff")),
        },
    )


@require_POST
def log_work(request):
    section_id = request.POST.get("section", "")
    topic = request.POST.get("topic", "").strip()
    work_description = request.POST.get("work_description", "").strip()
    notes = request.POST.get("notes", "").strip()

    if section_id not in SECTIONS:
        messages.error(request, "Choose a valid section.")
        return redirect("tracker:dashboard")

    section_info = SECTIONS[section_id]
    if topic not in section_info["topics"]:
        messages.error(request, "Choose a topic from the selected section.")
        return redirect("tracker:dashboard")
    if not work_description:
        messages.error(request, "Describe the work you completed.")
        return redirect("tracker:dashboard")

    progress = load_progress()
    section_data = progress["sections_tested"].setdefault(
        section_info["name"], {"status": "not_started", "entries": []}
    )
    evidence_dir = Path(settings.EVIDENCE_DIR)
    saved_paths = []
    files = []
    timestamp = datetime.now()

    for upload in request.FILES.getlist("evidence_files"):
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{Path(upload.name).name}"
        relative_path = Path(section_info["name"]) / topic / filename
        destination = evidence_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            for chunk in upload.chunks():
                output.write(chunk)
        saved_paths.append(destination)
        files.append(relative_path.as_posix())

    section_data["entries"].append(
        {
            "timestamp": timestamp.isoformat(),
            "topic": topic,
            "work_description": work_description,
            "files": files,
            "notes": notes,
        }
    )

    try:
        save_progress(progress)
    except OSError:
        for saved_path in saved_paths:
            saved_path.unlink(missing_ok=True)
        raise

    messages.success(request, "Work entry saved.")
    return redirect("tracker:dashboard")


@require_POST
def mark_section_test(request, section_id):
    if section_id not in SECTIONS:
        messages.error(request, "Choose a valid section.")
        return redirect("tracker:dashboard")

    section_name = SECTIONS[section_id]["name"]
    progress = load_progress()
    section_data = progress["sections_tested"].setdefault(
        section_name, {"status": "not_started", "entries": []}
    )
    if section_data["status"] == "tested":
        messages.warning(request, f"{section_name} is already marked complete.")
        return redirect("tracker:dashboard")

    section_data["status"] = "tested"
    section_data["entries"].append(
        {"timestamp": datetime.now().isoformat(), "section_test": True}
    )
    save_progress(progress)
    messages.success(request, f"{section_name} marked complete.")
    return redirect("tracker:dashboard")


@require_POST
def email_settings(request):
    config = {
        "sender_email": request.POST.get("sender_email", "").strip(),
        "recipient_email": request.POST.get("recipient_email", "").strip(),
        "cc_email": request.POST.get("cc_email", "").strip(),
    }
    try:
        parse_addresses(config["sender_email"], required=True)
        parse_addresses(config["recipient_email"], required=True)
        parse_addresses(config["cc_email"])
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("tracker:dashboard")

    save_email_config(config)
    messages.success(
        request,
        "Email addresses saved for the downloadable draft.",
    )
    return redirect("tracker:dashboard")


@require_POST
def download_email_draft(request):
    try:
        progress = load_progress()
        sent_history = load_sent_history()
        draft, cutoff = create_email_draft(progress, load_email_config(), sent_history)
    except (ValueError, OSError) as exc:
        messages.error(request, f"Email draft could not be created: {exc}")
        return redirect("tracker:dashboard")

    if cutoff:
        request.session["pending_email_draft_cutoff"] = cutoff
    response = HttpResponse(draft, content_type="message/rfc822")
    response["Content-Disposition"] = (
        f'attachment; filename="CTP_Progress_Update_{datetime.now():%Y%m%d_%H%M%S}.eml"'
    )
    return response


@require_POST
def mark_email_sent(request):
    cutoff = request.session.pop("pending_email_draft_cutoff", None)
    if not cutoff:
        messages.error(request, "Create a draft first. Entries are marked sent only after you confirm sending it.")
        return redirect("tracker:dashboard")

    sent_history = load_sent_history()
    previous_cutoff = sent_history.get("last_sent_date")
    if previous_cutoff is None or cutoff > previous_cutoff:
        sent_history["last_sent_date"] = cutoff
    sent_history.setdefault("sent_timestamps", []).append(datetime.now().isoformat())
    sent_history.setdefault("archived_files", [])
    save_sent_history(sent_history)
    messages.success(request, "Progress marked as sent. New entries will be included in the next draft.")
    return redirect("tracker:dashboard")
