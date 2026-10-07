# CTP Study Guide Tracker

## Menu Options
1. **Log Work** - Record practice work for a specific topic
2. **Mark Section Test Complete** - Mark an entire section as tested (one-time only)
3. **View Progress** - See your completion status
4. **Send Supervisor Email** - Email progress with evidence zip file
5. **Setup Email Configuration** - Configure email settings (sender, recipient, CC)
6. **Install Dependencies** - Install required Python packages
7. **Exit** - Close the program

## Sections & Topics

### 1. Python Foundations
- Syntax & control flow
- Functions
- Data structures
- Object-oriented Python
- Files, modules & environments
- Error handling
- Web fundamentals

### 2. Data Wrangling
- Loading & inspecting data
- Cleaning data
- Reshaping & combining
- SQL basics
- SQL aggregation
- SQL relationships
- SQL to the Django ORM

### 3. Git
- Setup & repositories
- Everyday flow
- Remotes
- Branching
- Merging & conflicts
- Pull requests & review
- History & recovery

### 4. Django
- Project structure
- The MTV pattern
- ORM & migrations
- Forms & validation
- Django admin
- Build end to end

### 5. Explain & Debug
- Read & trace code
- Debugging
- Defend design choices
- Own AI-generated code

### 6. AI Tooling
- AWS basics
- Amazon Bedrock
- AI tooling
- Prompting

## How It Works

### File Organization
Evidence files are organized in folders:
```
evidence/
├── Python Foundations/
│   ├── Syntax & control flow/
│   ├── Functions/
│   └── ...
├── Data Wrangling/
│   └── ...
old_work/  (created on each send)
├── Python Foundations/
│   └── ...
└── ...
```

### Archiving
- When you send email, NEW files stay in `evidence/` root
- OLD files automatically move to `old_work/` organized by section/topic
- All files (old + new) included in `evidence.zip` attachment
- Files only archived ONCE - preventing duplicates

### Email Configuration
Default emails:
- Sender: ysarigu@entergy.com
- Recipient: ysarigu@entergy.com
- CC: ysarigu@entergy.com

Use option 5 to update these anytime.

## First Run
1. Run: `python ctp_tracker.py`
2. Choose option 6 to install dependencies (pywin32)
3. Set up email config (option 5) if needed
4. Start logging work (option 1)!

## Django Web App

The Django interface uses the same `ctp_progress.json` and `evidence/` directory as
`ctp_tracker.py`. You can continue using the original command-line tracker; entries
logged in either interface appear in the other. Avoid writing to the tracker from
both interfaces at the same time.

From the project directory, install the web dependencies and start Django:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/> in your browser. The development server is intended
for local use; it is not configured for public deployment.

The web email form uses the sender, recipient, and CC addresses saved in the existing
`email_config.json`. It does not require SMTP: choose **Download supervisor email
draft**, then open the downloaded `.eml` file in your email app and review/send it
there. Evidence files are attached in a ZIP. After sending, return to the tracker and
choose **I sent the draft — mark progress as sent**. Only then is the shared
`sent_history.json` cutoff updated, so unsent drafts do not hide progress from a later
draft. The original CLI's Outlook email option remains unchanged.
