#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, zipfile
from datetime import datetime

class Colors:
    BLUE = '[94m'
    GREEN = '[92m'
    YELLOW = '[93m'
    RED = '[91m'
    CYAN = '[96m'
    WHITE = '[97m'
    RESET = '[0m'

SECTIONS = {
    "1": {"name": "Python Foundations", "topics": ["Syntax & control flow", "Functions", "Data structures", "Object-oriented Python", "Files, modules & environments", "Error handling", "Web fundamentals"]},
    "2": {"name": "Data Wrangling", "topics": ["Loading & inspecting data", "Cleaning data", "Reshaping & combining", "SQL basics", "SQL aggregation", "SQL relationships", "SQL to the Django ORM"]},
    "3": {"name": "Git", "topics": ["Setup & repositories", "Everyday flow", "Remotes", "Branching", "Merging & conflicts", "Pull requests & review", "History & recovery"]},
    "4": {"name": "Django", "topics": ["Project structure", "The MTV pattern", "ORM & migrations", "Forms & validation", "Django admin", "Build end to end"]},
    "5": {"name": "Explain & Debug", "topics": ["Read & trace code", "Debugging", "Defend design choices", "Own AI-generated code"]},
    "6": {"name": "AI Tooling", "topics": ["AWS basics", "Amazon Bedrock", "AI tooling", "Prompting"]}
}

PROGRESS_FILE = "ctp_progress.json"
SENT_HISTORY_FILE = "sent_history.json"
CONFIG_FILE = "email_config.json"
EVIDENCE_DIR = "evidence"
EVIDENCE_ZIP = "evidence.zip"
ARCHIVE_DIR = "old_work"

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_section(text):
    print(f"\n{Colors.CYAN}--- {text} ---{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.RESET}")

def get_yes_no(prompt, default=True):
    if default:
        default_str = "[y/n]"
    else:
        default_str = "[y/n]"
    while True:
        response = input(f"{prompt} {default_str}: ").strip().lower()
        if response == "":
            return default
        if response in ["y", "yes", "1", "true"]:
            return True
        if response in ["n", "no", "0", "false"]:
            return False
        print_error("Please enter y or n")

def get_input(prompt, allow_empty=False):
    while True:
        response = input(f"{prompt}: ").strip()
        if response == "":
            if allow_empty:
                return ""
            print_error("Input cannot be empty")
            continue
        return response

def strip_quotes(path):
    if path.startswith('"') and path.endswith('"'):
        return path[1:-1]
    if path.startswith("'") and path.endswith("'"):
        return path[1:-1]
    return path

def init_json(filepath, default_value):
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            json.dump(default_value, f, indent=2)
        return default_value
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except:
        with open(filepath, "w") as f:
            json.dump(default_value, f, indent=2)
        return default_value

def save_json(filepath, data):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print_error(f"Failed to save: {e}")
        return False

def init_progress():
    default_progress = {"created": datetime.now().isoformat(), "last_updated": datetime.now().isoformat(), "sections_tested": {}}
    for section_id, section_info in SECTIONS.items():
        section_name = section_info["name"]
        default_progress["sections_tested"][section_name] = {"status": "not_started", "entries": []}
    return default_progress

def load_progress():
    return init_json(PROGRESS_FILE, init_progress())

def save_progress(progress):
    progress["last_updated"] = datetime.now().isoformat()
    return save_json(PROGRESS_FILE, progress)

def create_evidence_structure():
    if not os.path.exists(EVIDENCE_DIR):
        os.makedirs(EVIDENCE_DIR)
    for section_id, section_info in SECTIONS.items():
        section_name = section_info["name"]
        section_dir = os.path.join(EVIDENCE_DIR, section_name)
        if not os.path.exists(section_dir):
            os.makedirs(section_dir)
        for topic in section_info["topics"]:
            topic_dir = os.path.join(section_dir, topic)
            if not os.path.exists(topic_dir):
                os.makedirs(topic_dir)

def display_sections():
    print_section("SELECT SECTION")
    for section_id, section_info in SECTIONS.items():
        print(f"  {section_id}. {section_info['name']}")
    print(f"  0. Back")
    while True:
        choice = input("\nEnter section number: ").strip()
        if choice == "0":
            return None
        if choice in SECTIONS:
            return choice
        print_error("Invalid selection")

def display_topics(section_id):
    if section_id not in SECTIONS:
        return None
    section_info = SECTIONS[section_id]
    print_section(f"SELECT TOPIC - {section_info['name']}")
    topics = section_info["topics"]
    for i, topic in enumerate(topics, 1):
        print(f"  {i}. {topic}")
    print(f"  0. Back")
    while True:
        choice = input("\nEnter topic number: ").strip()
        if choice == "0":
            return None
        try:
            topic_idx = int(choice) - 1
            if 0 <= topic_idx < len(topics):
                return topics[topic_idx]
        except:
            pass
        print_error("Invalid selection")

def handle_file_upload(section_name, topic_name):
    files_uploaded = []
    create_evidence_structure()
    topic_dir = os.path.join(EVIDENCE_DIR, section_name, topic_name)
    
    while True:
        file_path = get_input("Enter file path (or press Enter to skip)", allow_empty=True).strip()
        if file_path == "":
            break
        file_path = strip_quotes(file_path)
        if not os.path.exists(file_path):
            print_error(f"File not found: {file_path}")
            continue
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{os.path.basename(file_path)}"
            dest_path = os.path.join(topic_dir, filename)
            shutil.copy2(file_path, dest_path)
            print_success(f"File uploaded: {filename}")
            files_uploaded.append(os.path.join(section_name, topic_name, filename))
            if not get_yes_no("Add another file?", default=False):
                break
        except Exception as e:
            print_error(f"Failed to upload file: {e}")
    return files_uploaded

def log_work(progress):
    print_header("LOG YOUR WORK")
    section_id = display_sections()
    if section_id is None:
        return progress
    section_name = SECTIONS[section_id]["name"]
    topic = display_topics(section_id)
    if topic is None:
        return log_work(progress)
    print_section(f"LOGGING: {topic} ({section_name})")
    work_desc = get_input("Describe the work/practice you did")
    files = handle_file_upload(section_name, topic)
    notes = get_input("Any notes for your supervisor? (optional)", allow_empty=True)
    entry = {"timestamp": datetime.now().isoformat(), "topic": topic, "work_description": work_desc, "files": files, "notes": notes}
    progress["sections_tested"][section_name]["entries"].append(entry)
    save_progress(progress)
    print_success(f"Work logged for {topic}")
    return progress

def mark_section_test(progress):
    print_header("MARK SECTION TEST COMPLETE")
    section_id = display_sections()
    if section_id is None:
        return progress
    section_name = SECTIONS[section_id]["name"]
    print_section(f"MARK COMPLETE: {section_name}")
    print_info(f"You will mark {section_name} section test as complete.")
    
    # Check if already tested
    if progress["sections_tested"][section_name]["status"] == "tested":
        print_warning("A section can only be marked complete once")
        input("\nPress Enter to continue...")
        return progress
    
    if not get_yes_no("Confirm?", default=False):
        print_warning("Cancelled")
        input("\nPress Enter to continue...")
        return progress
    entry = {"timestamp": datetime.now().isoformat(), "section_test": True}
    progress["sections_tested"][section_name]["status"] = "tested"
    progress["sections_tested"][section_name]["entries"].append(entry)
    save_progress(progress)
    print_success(f"Section test marked for {section_name}")
    input("\nPress Enter to continue...")
    return progress

def view_progress(progress):
    print_header("YOUR PROGRESS")
    total_sections = len(progress["sections_tested"])
    completed_sections = 0
    for section_name, section_data in progress["sections_tested"].items():
        if section_data["status"] == "tested":
            completed_sections += 1
            status_icon = f"{Colors.GREEN}✓{Colors.RESET}"
        elif len(section_data["entries"]) > 0:
            status_icon = f"{Colors.YELLOW}◐{Colors.RESET}"
        else:
            status_icon = f"{Colors.WHITE}○{Colors.RESET}"
        entry_count = len(section_data["entries"])
        print(f"{status_icon} {section_name} ({entry_count} entries)")
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"Sections Tested: {completed_sections}/{total_sections}")
    if total_sections > 0:
        percentage = (completed_sections / total_sections) * 100
        print(f"Completion: {percentage:.1f}%")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    input("\nPress Enter to continue...")

def load_email_config():
    default_config = {"sender_email": "ysarigu@entergy.com", "recipient_email": "tliggan@entergy.com", "cc_email": "wlotte1@entergy.com"}
    return init_json(CONFIG_FILE, default_config)

def setup_email_config():
    print_header("SETUP EMAIL CONFIGURATION")
    config = load_email_config()
    
    print_section("CURRENT EMAIL CONFIGURATION")
    print(f"  Sender Email: {config['sender_email']}")
    print(f"  Recipient Email: {config['recipient_email']}")
    print(f"  CC Email: {config['cc_email']}")
    
    if not get_yes_no("\nUpdate email configuration?", default=False):
        print_warning("Cancelled")
        input("\nPress Enter to continue...")
        return
    
    config["sender_email"] = get_input("Enter your email")
    config["recipient_email"] = get_input("Enter supervisor's email")
    config["cc_email"] = get_input("Enter CC email")
    
    if save_json(CONFIG_FILE, config):
        print_success("Email configuration updated!")
    else:
        print_error("Failed to save configuration")
    
    input("\nPress Enter to continue...")

def load_sent_history():
    default_history = {"last_sent_date": None, "sent_timestamps": [], "archived_files": []}
    return init_json(SENT_HISTORY_FILE, default_history)

def save_sent_history(history):
    return save_json(SENT_HISTORY_FILE, history)

def get_entries_since_last_send(progress, sent_history):
    last_sent = sent_history.get("last_sent_date")
    new_entries = {}
    for section_name, section_data in progress["sections_tested"].items():
        new_section_entries = []
        for entry in section_data["entries"]:
            entry_time = entry["timestamp"]
            if last_sent is None or entry_time > last_sent:
                new_section_entries.append(entry)
        if new_section_entries:
            new_entries[section_name] = new_section_entries
    return new_entries

def archive_old_work(new_entries, sent_history):
    """Archive old work in old_work/ subdirectories, keeping current files in root"""
    try:
        # Build list of all files that are currently being sent (new entries)
        current_files = set()
        for section_name, entries in new_entries.items():
            for entry in entries:
                if entry.get("files"):
                    for file_ref in entry["files"]:
                        # file_ref is like "Section Name/Topic/timestamp_filename.ext"
                        # We just need the filename part
                        current_files.add(os.path.basename(file_ref))
        
        # Get previously archived files from history
        previously_archived = set(sent_history.get("archived_files", []))
        
        # Walk through evidence directory and move old files
        for section_name in SECTIONS.values():
            section_folder = section_name["name"]
            section_path = os.path.join(EVIDENCE_DIR, section_folder)
            
            if os.path.exists(section_path):
                for topic in section_name["topics"]:
                    topic_path = os.path.join(section_path, topic)
                    
                    if os.path.exists(topic_path):
                        for filename in os.listdir(topic_path):
                            file_path = os.path.join(topic_path, filename)
                            
                            if os.path.isfile(file_path):
                                # If file is NOT in current batch AND not already archived, move it
                                if filename not in current_files and filename not in previously_archived:
                                    archive_section_dir = os.path.join(ARCHIVE_DIR, section_folder, topic)
                                    if not os.path.exists(archive_section_dir):
                                        os.makedirs(archive_section_dir)
                                    
                                    dest = os.path.join(archive_section_dir, filename)
                                    shutil.move(file_path, dest)
                                    previously_archived.add(filename)
        
        # Update sent history with archived files
        sent_history["archived_files"] = list(previously_archived)
        save_sent_history(sent_history)
        
    except Exception as e:
        print_error(f"Archive operation failed: {e}")

def create_evidence_zip(new_entries, sent_history):
    if not new_entries or not any(new_entries.values()):
        return None
    
    try:
        # Archive old work first
        archive_old_work(new_entries, sent_history)
        
        if os.path.exists(EVIDENCE_ZIP):
            os.remove(EVIDENCE_ZIP)
        
        with zipfile.ZipFile(EVIDENCE_ZIP, 'w') as zipf:
            # Add current work from evidence directory
            if os.path.exists(EVIDENCE_DIR):
                for root, dirs, files in os.walk(EVIDENCE_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, EVIDENCE_DIR)
                        zipf.write(file_path, arcname)
            
            # Add archived work in old_work/ subdirectory
            if os.path.exists(ARCHIVE_DIR):
                for root, dirs, files in os.walk(ARCHIVE_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("old_work", os.path.relpath(file_path, ARCHIVE_DIR))
                        zipf.write(file_path, arcname)
        
        return EVIDENCE_ZIP if os.path.exists(EVIDENCE_ZIP) else None
    except Exception as e:
        print_error(f"Failed to create zip: {e}")
        return None

def send_supervisor_email(progress):
    print_header("SEND SUPERVISOR EMAIL")
    config = load_email_config()
    sent_history = load_sent_history()
    new_entries = get_entries_since_last_send(progress, sent_history)
    has_new = any(len(entries) > 0 for entries in new_entries.values())
    if not has_new:
        print_warning("No new work to send!")
        print_info("Log more work before sending an update")
        input("\nPress Enter to continue...")
        return progress
    test_mode = get_yes_no("Send to yourself first? (TEST MODE)", default=True)
    recipient = config["sender_email"] if test_mode else config["recipient_email"]
    cc = None if test_mode else config["cc_email"]
    print_info(f"Email will be sent to: {recipient}")
    if cc:
        print_info(f"CC: {cc}")
    if not get_yes_no("Ready to send?", default=False):
        print_warning("Email cancelled")
        input("\nPress Enter to continue...")
        return progress
    try:
        import win32com.client as win32
        outlook = win32.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = recipient
        if cc:
            mail.CC = cc
        mail.Subject = f"CTP Progress Update - {datetime.now().strftime('%Y-%m-%d')}"
        body = f"CTP Progress Update\nReport Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for section_name, entries in new_entries.items():
            if entries:
                body += f"{section_name}:\n{'-'*60}\n\n"
                for i, entry in enumerate(entries, 1):
                    if "section_test" in entry and entry["section_test"]:
                        body += f"Section Test Completed\n"
                        body += f"  Time: {entry['timestamp']}\n\n"
                    else:
                        body += f"Entry {i}:\n"
                        body += f"  Topic: {entry.get('topic', 'N/A')}\n"
                        body += f"  Time: {entry['timestamp']}\n"
                        body += f"  Work: {entry['work_description']}\n"
                        if entry['files']:
                            body += f"  Files: {len(entry['files'])} file(s)\n"
                        if entry['notes']:
                            body += f"  Notes: {entry['notes']}\n"
                        body += "\n"
        mail.Body = body
        zip_file = create_evidence_zip(new_entries, sent_history)
        if zip_file and os.path.exists(zip_file):
            mail.Attachments.Add(os.path.abspath(zip_file))
        mail.Display()
        print_success("Email opened in Outlook - review and send manually")
        sent_history["last_sent_date"] = datetime.now().isoformat()
        save_sent_history(sent_history)
    except Exception as e:
        print_error(f"Failed to create email: {e}")
    input("\nPress Enter to continue...")
    return progress

def install_dependencies():
    print_header("INSTALL DEPENDENCIES")
    print_info("Installing required packages...")
    packages = ["pywin32"]
    for package in packages:
        try:
            print_info(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print_success(f"{package} installed successfully!")
        except Exception as e:
            print_error(f"Failed to install {package}: {e}")
    print_success("All dependencies installed!")
    input("\nPress Enter to continue...")

def main_menu():
    while True:
        print_header("CTP PROGRESS TRACKER")
        print("\n  1. Log Work")
        print("  2. Mark Section Test Complete")
        print("  3. View Progress")
        print("  4. Send Supervisor Email")
        print("  5. Setup Email Configuration")
        print("  6. Install Dependencies")
        print("  7. Exit")
        choice = input("\nEnter option number: ").strip()
        if choice == "1":
            progress = load_progress()
            progress = log_work(progress)
        elif choice == "2":
            progress = load_progress()
            progress = mark_section_test(progress)
        elif choice == "3":
            progress = load_progress()
            view_progress(progress)
        elif choice == "4":
            progress = load_progress()
            progress = send_supervisor_email(progress)
        elif choice == "5":
            setup_email_config()
        elif choice == "6":
            install_dependencies()
        elif choice == "7":
            print_info("Goodbye!")
            break
        else:
            print_error("Invalid option")

def main():
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
