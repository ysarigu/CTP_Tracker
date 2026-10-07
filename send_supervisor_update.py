"""
CTP Supervisor Update Email Automation - WITH TEST MODE
Sends progress updates to supervisor with evidence ZIP
"""

import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.encoders import encode_base64
from datetime import datetime
import shutil
import glob

def load_config():
    """Load email configuration"""
    if not os.path.exists('email_config.json'):
        print("ERROR: email_config.json not found!")
        return None
    
    with open('email_config.json', 'r') as f:
        return json.load(f)

def load_progress():
    """Load progress tracking data"""
    if not os.path.exists('ctp_progress.json'):
        return {"sections": {}, "last_email_sent": None, "email_history": []}
    
    with open('ctp_progress.json', 'r') as f:
        return json.load(f)

def load_sent_history():
    """Load what was already sent"""
    if not os.path.exists('sent_history.json'):
        return {"last_sent": None, "sent_topics": []}
    
    with open('sent_history.json', 'r') as f:
        return json.load(f)

def get_new_items(progress, sent_history):
    """Find NEW items since last email"""
    new_items = {}
    
    for section, topics in progress.get("sections", {}).items():
        new_topics = {}
        for topic_name, topic_data in topics.items():
            # Check if this topic is new or updated since last send
            if topic_data.get("status") != "not started":
                topic_id = f"{section}::{topic_name}"
                if topic_id not in sent_history.get("sent_topics", []):
                    new_topics[topic_name] = topic_data
        
        if new_topics:
            new_items[section] = new_topics
    
    return new_items

def create_evidence_zip(new_items, test_mode=False):
    """Create ZIP file with evidence organized by section"""
    zip_name = f"CTP_Evidence_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    if test_mode:
        zip_name += "_TEST"
    
    # Create temp folder
    temp_folder = "temp_evidence"
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    os.makedirs(temp_folder)
    
    # Organize evidence by section
    file_count = 0
    for section, topics in new_items.items():
        section_folder = os.path.join(temp_folder, section)
        os.makedirs(section_folder, exist_ok=True)
        
        for topic_name, topic_data in topics.items():
            topic_folder = os.path.join(section_folder, topic_name)
            os.makedirs(topic_folder, exist_ok=True)
            
            # Copy uploaded files
            if "uploaded_files" in topic_data:
                for file_path in topic_data["uploaded_files"]:
                    if os.path.exists(file_path):
                        dest = os.path.join(topic_folder, os.path.basename(file_path))
                        shutil.copy(file_path, dest)
                        file_count += 1
            
            # Save notes as text file
            notes = topic_data.get("work_notes", "No notes")
            test_status = topic_data.get("test_passed", False)
            
            notes_file = os.path.join(topic_folder, "notes.txt")
            with open(notes_file, 'w') as f:
                f.write(f"Topic: {topic_name}\n")
                f.write(f"Section: {section}\n")
                f.write(f"Status: {topic_data.get('status', 'unknown')}\n")
                f.write(f"Test Passed: {test_status}\n")
                f.write(f"Date: {topic_data.get('timestamp', 'unknown')}\n")
                f.write(f"\nNotes:\n{notes}\n")
    
    # Create ZIP
    zip_path = shutil.make_archive(zip_name, 'zip', temp_folder)
    
    # Cleanup temp folder
    shutil.rmtree(temp_folder)
    
    return zip_path, file_count

def generate_email_body(new_items, test_mode=False):
    """Generate professional email body"""
    test_note = "\n[TEST MODE - This is a test run sent to yourself]\n" if test_mode else ""
    
    body = f"""CTP Developer Qualification Progress Update
{test_note}
Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

--- NEW PROGRESS ---

"""
    
    total_topics = 0
    total_tests_passed = 0
    
    for section, topics in new_items.items():
        body += f"\n{section.upper()}\n"
        body += "-" * 40 + "\n"
        
        for topic_name, topic_data in topics.items():
            status = topic_data.get("status", "unknown")
            test_passed = topic_data.get("test_passed", False)
            notes = topic_data.get("work_notes", "")
            
            body += f"  • {topic_name}\n"
            body += f"    Status: {status}\n"
            if test_passed:
                body += f"    ✓ Test Passed\n"
                total_tests_passed += 1
            if notes:
                body += f"    Notes: {notes[:100]}...\n" if len(notes) > 100 else f"    Notes: {notes}\n"
            body += "\n"
            total_topics += 1
    
    body += f"""
--- SUMMARY ---
Total Topics Updated: {total_topics}
Tests Passed: {total_tests_passed}

All evidence files are attached in the ZIP file, organized by section.

Best regards,
Your CTP Progress Tracker
"""
    
    return body

def send_email(config, recipient_email, subject, body, zip_file, test_mode=False):
    """Send email via Entergy's mail server"""
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = config['sender_email']
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    if config.get('cc_email'):
        if test_mode:
            print(f"[TEST MODE] Would CC: {config['cc_email']}")
        else:
            msg['Cc'] = config['cc_email']
    
    # Add body
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach ZIP file
    if os.path.exists(zip_file):
        with open(zip_file, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(zip_file)}')
        msg.attach(part)
    
    try:
        # Try Entergy mail server (modify if different)
        server = smtplib.SMTP('smtp.entergy.com', 587)  # Standard Entergy SMTP
        server.starttls()
        # Note: You may need to use app-specific password or enable "Less secure apps"
        server.login(config['sender_email'], config['sender_password'])
        
        recipients = [recipient_email]
        if config.get('cc_email') and not test_mode:
            recipients.append(config['cc_email'])
        
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"ERROR sending email: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check your password is correct")
        print("2. If using Gmail, use an app-specific password")
        print("3. Check if 2FA is enabled (may need special setup)")
        print("4. For Entergy email, contact IT for correct SMTP settings")
        return False

def main():
    print("=" * 60)
    print("CTP SUPERVISOR UPDATE EMAIL")
    print("=" * 60)
    
    # Ask if test mode
    test_input = input("\n[TEST MODE] Send to yourself first? (y/n): ").strip().lower()
    test_mode = test_input == 'y'
    
    config = load_config()
    if not config:
        return
    
    progress = load_progress()
    sent_history = load_sent_history()
    
    # Get new items
    new_items = get_new_items(progress, sent_history)
    
    if not new_items:
        print("\n⚠️  No new items since last email.")
        print("Have you logged any new work? Run: python ctp_tracker.py")
        return
    
    print(f"\n✓ Found {sum(len(topics) for topics in new_items.values())} new topics to report")
    
    # Create ZIP
    print("\nCreating evidence ZIP file...")
    zip_file, file_count = create_evidence_zip(new_items, test_mode)
    print(f"✓ ZIP created with {file_count} evidence files: {zip_file}")
    
    # Generate email
    body = generate_email_body(new_items, test_mode)
    
    # Determine recipient
    if test_mode:
        recipient = config['sender_email']
        cc_note = f" (Will CC: {config.get('cc_email', 'none')} in production)"
    else:
        recipient = config['supervisor_email']
        cc_note = f" (CC: {config.get('cc_email', 'none')})"
    
    print(f"\n--- EMAIL PREVIEW ---")
    print(f"From: {config['sender_email']}")
    print(f"To: {recipient}{cc_note}")
    print(f"Subject: CTP Progress Update - {datetime.now().strftime('%B %d, %Y')}")
    print(f"Attachment: {os.path.basename(zip_file)}")
    print(f"\n{body}")
    print(f"\n--- END PREVIEW ---")
    
    # Confirm send
    confirm = input(f"\nSend email? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Cancelled.")
        os.remove(zip_file)
        return
    
    # Send email
    print("\nSending email...")
    if send_email(config, recipient, f"CTP Progress Update - {datetime.now().strftime('%B %d, %Y')}", body, zip_file, test_mode):
        print("✓ Email sent successfully!")
        
        if not test_mode:
            # Update sent history
            for section, topics in new_items.items():
                for topic_name in topics.keys():
                    sent_history["sent_topics"].append(f"{section}::{topic_name}")
            
            sent_history["last_sent"] = datetime.now().isoformat()
            
            with open('sent_history.json', 'w') as f:
                json.dump(sent_history, f, indent=2)
            
            print("✓ History updated - these items won't be sent again")
    else:
        print("✗ Failed to send email. Check your email configuration.")
    
    # Cleanup
    os.remove(zip_file)

if __name__ == "__main__":
    main()
