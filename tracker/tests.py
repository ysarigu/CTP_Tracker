import json
import tempfile
from email import policy
from email.parser import BytesParser
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from ctp_tracker import SECTIONS, init_progress


class TrackerWebTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.progress_file = root / "ctp_progress.json"
        self.evidence_dir = root / "evidence"
        self.email_config_file = root / "email_config.json"
        self.sent_history_file = root / "sent_history.json"
        self.settings_override = override_settings(
            PROGRESS_FILE=self.progress_file,
            EVIDENCE_DIR=self.evidence_dir,
            EMAIL_CONFIG_FILE=self.email_config_file,
            SENT_HISTORY_FILE=self.sent_history_file,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def test_dashboard_shows_existing_sections(self):
        response = self.client.get(reverse("tracker:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Foundations")
        self.assertFalse(self.progress_file.exists())

    def test_dashboard_reads_existing_cli_progress(self):
        progress = init_progress()
        section_name = SECTIONS["1"]["name"]
        progress["sections_tested"][section_name]["entries"].append(
            {
                "timestamp": "2026-10-07T12:00:00",
                "topic": SECTIONS["1"]["topics"][0],
                "work_description": "Logged from the existing CLI",
                "files": [],
                "notes": "",
            }
        )
        self.progress_file.write_text(json.dumps(progress), encoding="utf-8")

        response = self.client.get(reverse("tracker:dashboard"))

        self.assertContains(response, "Logged from the existing CLI")

    def test_logging_work_writes_cli_compatible_progress_and_evidence(self):
        section_id = "1"
        section_name = SECTIONS[section_id]["name"]
        topic = SECTIONS[section_id]["topics"][0]
        response = self.client.post(
            reverse("tracker:log_work"),
            {
                "section": section_id,
                "topic": topic,
                "work_description": "Practiced the topic",
                "notes": "Review again tomorrow",
                "evidence_files": SimpleUploadedFile("sample.txt", b"evidence"),
            },
        )

        self.assertRedirects(response, reverse("tracker:dashboard"))
        progress = json.loads(self.progress_file.read_text(encoding="utf-8"))
        section = progress["sections_tested"][section_name]
        entry = section["entries"][0]
        self.assertEqual(section["status"], "not_started")
        self.assertEqual(entry["work_description"], "Practiced the topic")
        self.assertEqual(entry["notes"], "Review again tomorrow")
        self.assertTrue(entry["files"][0].startswith(f"{section_name}/{topic}/"))
        stored_file = self.evidence_dir / entry["files"][0]
        self.assertEqual(stored_file.read_bytes(), b"evidence")

    def test_mark_test_complete_uses_existing_progress_shape(self):
        section_id = "1"
        section_name = SECTIONS[section_id]["name"]
        response = self.client.post(
            reverse("tracker:mark_section_test", args=[section_id])
        )

        self.assertRedirects(response, reverse("tracker:dashboard"))
        progress = json.loads(self.progress_file.read_text(encoding="utf-8"))
        section = progress["sections_tested"][section_name]
        self.assertEqual(section["status"], "tested")
        self.assertTrue(section["entries"][0]["section_test"])

    def test_topics_are_loaded_for_each_section(self):
        response = self.client.get(reverse("tracker:dashboard"))

        self.assertEqual(
            response.context["topic_map"]["3"],
            SECTIONS["3"]["topics"],
        )
        self.assertContains(response, 'id="topics-by-section"')
        self.assertContains(response, "sectionSelect.addEventListener")

    def test_email_draft_includes_evidence_without_marking_it_sent(self):
        section_name = SECTIONS["3"]["name"]
        topic = SECTIONS["3"]["topics"][0]
        evidence_path = Path(section_name) / topic / "git-notes.txt"
        evidence_file = self.evidence_dir / evidence_path
        evidence_file.parent.mkdir(parents=True)
        evidence_file.write_text("remote practice evidence", encoding="utf-8")
        progress = init_progress()
        progress["sections_tested"][section_name]["entries"].append(
            {
                "timestamp": "2026-10-07T12:00:00.123456",
                "topic": topic,
                "work_description": "Practiced Git remotes",
                "files": [evidence_path.as_posix()],
                "notes": "",
            }
        )
        self.progress_file.write_text(json.dumps(progress), encoding="utf-8")
        self.email_config_file.write_text(
            json.dumps(
                {
                    "sender_email": "tracker@example.com",
                    "recipient_email": "supervisor@example.com",
                    "cc_email": "",
                }
            ),
            encoding="utf-8",
        )

        response = self.client.post(reverse("tracker:email_draft"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "message/rfc822")
        draft = BytesParser(policy=policy.default).parsebytes(response.content)
        self.assertEqual(draft["To"], "supervisor@example.com")
        self.assertEqual(draft["Cc"], None)
        self.assertIn("CTP Progress Update", draft["Subject"])
        parts = list(draft.iter_attachments())
        self.assertEqual([part.get_filename() for part in parts], ["CTP_Evidence.zip"])
        with ZipFile(BytesIO(parts[0].get_payload(decode=True))) as evidence_zip:
            self.assertEqual(
                evidence_zip.read(evidence_path.as_posix()),
                b"remote practice evidence",
            )
        self.assertIn("Practiced Git remotes", draft.get_body().get_content())
        self.assertEqual(
            self.client.session["pending_email_draft_cutoff"],
            "2026-10-07T12:00:00.123456",
        )
        self.assertFalse(self.sent_history_file.exists())

    def test_confirming_sent_draft_updates_shared_send_history(self):
        session = self.client.session
        session["pending_email_draft_cutoff"] = "2026-10-07T12:00:00.123456"
        session.save()

        response = self.client.post(reverse("tracker:mark_email_sent"))

        self.assertRedirects(response, reverse("tracker:dashboard"))
        sent_history = json.loads(self.sent_history_file.read_text(encoding="utf-8"))
        self.assertEqual(
            sent_history["last_sent_date"],
            "2026-10-07T12:00:00.123456",
        )
        self.assertNotIn(
            "pending_email_draft_cutoff",
            self.client.session,
        )

    def test_log_work_rejects_topic_from_another_section(self):
        response = self.client.post(
            reverse("tracker:log_work"),
            {
                "section": "3",
                "topic": SECTIONS["1"]["topics"][0],
                "work_description": "Should not be accepted",
            },
        )

        self.assertRedirects(response, reverse("tracker:dashboard"))
        self.assertFalse(self.progress_file.exists())
