# Production Email Automation System

A production-grade Python application designed to send personalized bulk emails from CSV datasets using Jinja2 HTML templates. Features dual sending backends (**SMTP** with SSL/STARTTLS and **REST APIs** for SendGrid/Mailgun), automated exponential backoff retries, APScheduler job dispatches, progress tracking, HTML preview generation, and CSV audit logging.

---

## 🌟 Key Features

- 📧 **Personalized Email Templates**: Dynamic rendering of responsive HTML and plain-text fallback bodies using Jinja2 (`{{ name }}`, `{{ product }}`, `{{ order_id }}`, `{{ promo_code }}`).
- ⚙️ **Dual Sending Engine**:
  - **SMTP Backend**: Complete SSL/STARTTLS support (Gmail, Outlook, custom SMTP servers).
  - **REST API Backend**: Direct integration with **SendGrid** and **Mailgun** v3 APIs.
- 🛡️ **Data Validation & Cleaning**: Built-in email regex validation (RFC 5322 pattern) ensuring invalid contact entries are safely skipped without halting dispatches.
- 🔄 **Exponential Backoff Retries**: Automatic retry handling for transient network issues (configurable retries with 2s, 4s, 8s backoff delays).
- ⏱️ **Throttling & Rate Control**: Configurable inter-send delay settings to comply with provider rate limits.
- 📅 **Automated Scheduling**: Scheduled daily dispatches using `APScheduler`.
- 🔍 **Dry-Run & HTML Previews**: Preview personalized emails rendered to HTML files in `preview/` before sending real emails.
- 📊 **Audit Trail Logging**: Structured logging (`logs/app.log`) and CSV delivery audit trail (`logs/email_log.csv`).
- 💻 **CLI & Web Interface**: Command-line interface with options for immediate dispatch (`--now`), preview mode (`--dry-run`), test send (`--test-send`), custom subjects (`--subject`), and an optional web control dashboard (`server.py`).

---

## 🛠️ Tech Stack & Dependencies

- **Language**: Python 3.10+
- **Template Engine**: Jinja2 (`jinja2`)
- **Data Processing**: Pandas (`pandas`)
- **Environment Management**: python-dotenv (`python-dotenv`)
- **HTTP Client**: Requests (`requests`)
- **Task Scheduler**: APScheduler (`apscheduler`)
- **CLI Utilities**: TQDM progress bars (`tqdm`)

---

## 📁 Project Folder Structure

```
email_automation_system/
├── main.py                  # CLI application entry point
├── config.py                # Environment configuration loader & validator
├── server.py                # Optional Web Dashboard control server
├── .env.example             # Environment variable template file
├── .gitignore               # Git ignore rules for secrets, logs & cache
├── requirements.txt         # Project dependencies
├── README.md                # System documentation
├── data/
│   └── users.csv            # Recipient dataset (CSV format)
├── templates/
│   └── email_template.html  # Responsive HTML email template
├── src/
│   ├── __init__.py          # Package initializer
│   ├── data_loader.py       # CSV dataset reader & email regex validator
│   ├── email_builder.py     # Jinja2 renderer & MIME message builder
│   ├── email_sender.py      # Unified SMTP, SendGrid, & Mailgun senders
│   ├── retry_handler.py     # Exponential backoff retry execution wrapper
│   ├── scheduler.py         # APScheduler daily cron integration
│   └── logger.py            # Console, file, & CSV audit trail logger
├── preview/
│   └── .gitkeep             # Directory anchor for generated HTML previews
├── logs/
│   ├── .gitkeep             # Directory anchor for delivery logs
│   └── email_log.csv        # Delivery audit trail (ignored by git)
└── web/
    └── index.html           # Web Control Dashboard UI
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher installed.

### 2. Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/your-username/email-automation-system.git
cd email-automation-system

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration (`.env`)

Copy `.env.example` to create your local `.env` configuration file:

```bash
cp .env.example .env
```

Edit `.env` with your preferred credentials:

### Option A: Gmail SMTP Configuration
```ini
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_digit_app_password
FROM_NAME=Your Company Name
FROM_EMAIL=your_email@gmail.com
RETRY_LIMIT=3
SEND_DELAY_SECONDS=0.5
```

> 🔐 **Gmail App Password Setup**:
> 1. Go to your **Google Account** > **Security**.
> 2. Enable **2-Step Verification**.
> 3. Search for **App Passwords** and generate a new key (16 characters).
> 4. Paste the 16-character code into `SMTP_PASSWORD` in `.env`.

### Option B: SendGrid REST API
```ini
EMAIL_PROVIDER=api
API_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.your_sendgrid_api_key
FROM_NAME=Your Company Name
FROM_EMAIL=verified_sender@yourdomain.com
```

### Option C: Mailgun REST API
```ini
EMAIL_PROVIDER=api
API_PROVIDER=mailgun
MAILGUN_API_KEY=key-your_mailgun_api_key
MAILGUN_DOMAIN=mg.yourdomain.com
FROM_NAME=Your Company Name
FROM_EMAIL=mailgun@yourdomain.com
```

---

## 💻 CLI Usage Guide

### 1. Dry Run / HTML Preview Mode (`--dry-run`)
Test template rendering, check for missing variables, and save generated HTML preview files into `preview/` without making network calls or sending emails:

```bash
python main.py --dry-run
```

### 2. Immediate Bulk Dispatch (`--now`)
Send emails to all valid contacts in `data/users.csv`:

```bash
python main.py --now
```

### 3. Send Single Test Email (`--test-send`)
Send a single test email using the first CSV record to verify delivery:

```bash
python main.py --test-send "your_personal_email@example.com"
```

### 4. Schedule Daily Bulk Dispatches (`--schedule`)
Schedule the dispatches to run automatically every day at a specified time (HH:MM format):

```bash
python main.py --schedule "09:00"
```

### 5. Custom Dataset, Template, or Subject Line
Override defaults with custom file paths or subject templates:

```bash
python main.py --now --csv "data/custom_list.csv" --template "templates/promo.html" --subject "Special Offer for {{ name }}"
```

---

## 🌐 Web Control Dashboard (Optional)

Launch the lightweight HTTP control server to manage dispatches and view live logs from a browser dashboard:

```bash
python server.py
```
Open **http://localhost:8000** in your browser to access the control panel.

---

## 📊 Delivery Logs & Audit Trail

- **CSV Audit Trail (`logs/email_log.csv`)**:
  ```csv
  timestamp,name,recipient_email,status,error_message
  2026-08-19 14:45:10,John Doe,john.doe@example.com,SUCCESS,
  2026-08-19 14:45:11,Jane Smith,invalid_email_format,SKIPPED,Invalid email format
  ```
- **Application Trace Log (`logs/app.log`)**: Log file capturing detailed runtime execution and network retry attempts.

---

## 📄 License

This project is open-source under the MIT License.
