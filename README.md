# Email Campaign Manager

![Python](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python)
![MongoDB](https://img.shields.io/badge/MongoDB-4.0%2B-green?logo=mongodb)
![License](https://img.shields.io/badge/License-MIT-yellow)
![SMTP](https://img.shields.io/badge/SMTP-Gmail%20Ready-red?logo=gmail)

A comprehensive Python application for managing email campaigns with MongoDB integration and SMTP delivery. This tool provides a complete solution for organizing contacts, creating email templates, managing contact lists, and executing email campaigns with personalization features.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Data Models](#data-models)
- [API Reference](#api-reference)
- [Email Personalization](#email-personalization)
- [Database Schema](#database-schema)
- [Error Handling](#error-handling)
- [Logging](#logging)
- [Security Considerations](#security-considerations)
- [Performance Tips](#performance-tips)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

### Contact Management
- Add, update, and delete contacts
- Email validation and duplicate prevention
- Custom fields support for additional contact information
- CSV import functionality with flexible field mapping
- Contact export to CSV

### Email Templates
- Create and manage reusable email templates
- Support for both plain text and HTML content
- Template personalization with placeholders
- Template versioning and management

### Contact Lists
- Organize contacts into targeted lists
- Multiple list membership support
- Easy list management and contact assignment

### Campaign Management
- Create and execute email campaigns
- Multi-list targeting
- Real-time campaign statistics
- Campaign status tracking (`draft` → `sent`)

### Email Personalization
- Dynamic content replacement using placeholders:
  - `{{first_name}}`, `{{last_name}}`, `{{email}}`, `{{company}}`
  - `{{full_name}}` (automatic combination)
  - `{{custom.field_name}}` for custom fields

### Email Delivery
- SMTP integration with TLS support (port 587) and SSL support (port 465)
- File attachment support
- Bounce and failure tracking
- Comprehensive email delivery logging

### Analytics and Logging
- Email delivery logs with timestamps
- Campaign success/failure statistics
- Log cleanup utilities
- Detailed error reporting

---

## Project Structure

```
Email_Camp/
├── mail.py                  # Core application – all classes and EmailCampaignManager
├── test_setup.py            # Setup verification and environment check script
├── smtp_test.py             # Step-by-step SMTP connection test script
├── smtp_fix.py              # Diagnostic tool for Gmail SMTP connection methods
├── gmail_test.py            # Minimal Gmail send test using .env credentials
├── create_word_doc.py       # Generates a Word (.docx) project documentation file
├── requirements.txt         # Python package dependencies
├── .env.example             # Example environment variable configuration
├── .gitignore               # Git ignore rules
├── README.md                # Project documentation (this file)
├── API_DOCUMENTATION.md     # Detailed API reference
└── CHANGELOG.md             # Version history and release notes
```

---

## Requirements

| Component     | Minimum Version              |
|---------------|------------------------------|
| Python        | 3.7+                         |
| MongoDB       | 4.0+ (local or Atlas)        |
| pymongo       | 4.6.0+                       |
| pandas        | 2.1.0+                       |
| python-dotenv | 1.0.0+                       |
| dnspython     | 2.0.0+                       |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/carangithub/Email_Camp.git
cd Email_Camp
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your MongoDB URI, SMTP credentials, and email settings
```

### 4. Ensure MongoDB is running

- **Local:** Start the MongoDB service (`mongod`)
- **Cloud:** Use a [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) connection string

### 5. Verify your setup

```bash
python test_setup.py
```

---

## Configuration

All settings are managed through a `.env` file. Copy `.env.example` to `.env` and fill in your values.

### Environment Variables

| Variable                     | Description                              | Default / Example                        |
|------------------------------|------------------------------------------|------------------------------------------|
| `MONGODB_URI`                | MongoDB connection string                | `mongodb://localhost:27017/`             |
| `MONGODB_DATABASE`           | Database name                            | `email_campaigns`                        |
| `SMTP_SERVER`                | SMTP server hostname                     | `smtp.gmail.com`                         |
| `SMTP_PORT`                  | SMTP port                                | `587`                                    |
| `SMTP_USERNAME`              | SMTP login username                      | `you@gmail.com`                          |
| `SMTP_PASSWORD`              | SMTP password or App Password            | `abcd efgh ijkl mnop` (16-char)          |
| `SMTP_USE_TLS`               | Enable STARTTLS (port 587)               | `True`                                   |
| `FROM_EMAIL`                 | Sender email address                     | `you@gmail.com`                          |
| `FROM_NAME`                  | Sender display name                      | `Your Name`                              |
| `RECEIVER_EMAILS`            | Comma-separated recipient list           | `a@example.com,b@example.com`            |
| `DEFAULT_CONTACT_LIST_NAME`  | Name for the default contact list        | `Default Recipients`                     |

### MongoDB Setup

```python
manager = EmailCampaignManager(
    mongodb_uri="mongodb://your-mongodb-uri",
    db_name="your_database_name"
)
```

### SMTP Configuration (programmatic)

```python
manager.configure_smtp(
    server="smtp.gmail.com",
    port=587,
    username="your_email@gmail.com",
    password="your_app_password",   # Use a Gmail App Password
    use_tls=True
)
```

> **Gmail note:** Enable 2-Factor Authentication in your Google Account, then generate a
> 16-character [App Password](https://myaccount.google.com/apppasswords) for "Mail". Use
> that App Password (without spaces) as `SMTP_PASSWORD`.

---

## Quick Start

```python
from mail import EmailCampaignManager, Contact, EmailTemplate, Campaign

# Initialize the manager (reads settings from .env automatically)
manager = EmailCampaignManager()

# --- Contacts ---
contact = Contact(
    email="john.doe@example.com",
    first_name="John",
    last_name="Doe",
    company="Example Corp",
    custom_fields={"department": "Marketing"}
)
manager.add_contact(contact)

# --- Contact List ---
list_id = manager.create_contact_list("Newsletter", "Main newsletter subscribers")
manager.add_contacts_to_list("Newsletter", ["john.doe@example.com"])

# --- Email Template ---
template = EmailTemplate(
    name="Welcome Email",
    subject="Welcome {{first_name}}!",
    body="Hello {{first_name}}, welcome to our newsletter!\n\nBest regards,\nThe Team",
    html_body="<h2>Hello {{first_name}},</h2><p>Welcome to our newsletter!</p>"
)
template_id = manager.save_template(template)

# --- Campaign ---
list_doc = manager.contact_lists_collection.find_one({"name": "Newsletter"})
campaign = Campaign(
    name="Welcome Campaign",
    template_id=template_id,
    contact_list_ids=[str(list_doc["_id"])]
)
campaign_id = manager.create_campaign(campaign)

# --- Send ---
stats = manager.send_campaign("Welcome Campaign")
print(f"Campaign results: {stats}")
# Example output: {'sent': 1, 'failed': 0, 'total': 1}

manager.close()
```

---

## Data Models

### `Contact`

| Field          | Type   | Required | Description                           |
|----------------|--------|----------|---------------------------------------|
| `email`        | `str`  | ✅        | Email address (unique)                |
| `first_name`   | `str`  | ❌        | First name                            |
| `last_name`    | `str`  | ❌        | Last name                             |
| `company`      | `str`  | ❌        | Company name                          |
| `custom_fields`| `dict` | ❌        | Arbitrary key/value pairs             |

### `EmailTemplate`

| Field        | Type       | Required | Description                              |
|--------------|------------|----------|------------------------------------------|
| `name`       | `str`      | ✅        | Unique template name                     |
| `subject`    | `str`      | ✅        | Subject line (supports placeholders)     |
| `body`       | `str`      | ✅        | Plain-text body (supports placeholders)  |
| `html_body`  | `str`      | ❌        | HTML body (supports placeholders)        |
| `created_at` | `datetime` | auto     | Creation timestamp (set automatically)   |

### `Campaign`

| Field              | Type         | Required | Description                              |
|--------------------|--------------|----------|------------------------------------------|
| `name`             | `str`        | ✅        | Unique campaign name                     |
| `template_id`      | `str`        | ✅        | MongoDB `_id` of the template to use     |
| `contact_list_ids` | `list[str]`  | ✅        | List of contact list `_id` values        |
| `status`           | `str`        | auto     | `"draft"` or `"sent"`                   |
| `total_recipients` | `int`        | auto     | Total unique recipients                  |
| `sent_count`       | `int`        | auto     | Successful deliveries                    |
| `failed_count`     | `int`        | auto     | Failed deliveries                        |
| `created_at`       | `datetime`   | auto     | Creation timestamp                       |
| `sent_at`          | `datetime`   | auto     | Sent timestamp                           |

---

## API Reference

For the full API reference, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

### Contact Management

```python
manager.add_contact(contact: Contact) -> str
manager.get_contact(email: str) -> Optional[Contact]
manager.update_contact(email: str, updates: dict) -> bool
manager.delete_contact(email: str) -> bool
manager.import_contacts_from_csv(file_path: str, mapping: dict) -> int
manager.export_contacts(output_file: str, contact_list_name: str = None)
```

### Template Management

```python
manager.save_template(template: EmailTemplate) -> str
manager.get_template(name: str) -> Optional[EmailTemplate]
manager.list_templates() -> list[str]
manager.delete_template(name: str) -> bool
```

### Campaign Management

```python
manager.create_campaign(campaign: Campaign) -> str
manager.send_campaign(name: str, attachments: list[str] = None) -> dict
manager.get_campaign_stats(name: str) -> dict
manager.list_campaigns() -> list[str]
```

### Contact List Management

```python
manager.create_contact_list(name: str, description: str = "") -> str
manager.add_contacts_to_list(list_name: str, emails: list[str]) -> int
manager.get_contact_list_contacts(list_name: str) -> list[Contact]
```

### Utility

```python
manager.validate_email(email: str) -> bool
manager.get_receiver_emails_from_env() -> list[str]
manager.get_email_logs(limit: int = 100, status_filter: str = None) -> list[dict]
manager.cleanup_old_logs(days_old: int = 30)
manager.configure_smtp(server, port, username, password, use_tls=True)
manager.close()
```

---

## Email Personalization

Use these placeholders inside template `subject`, `body`, and `html_body` fields:

| Placeholder            | Replaced With                          |
|------------------------|----------------------------------------|
| `{{first_name}}`       | Contact's first name                   |
| `{{last_name}}`        | Contact's last name                    |
| `{{full_name}}`        | First name + last name (combined)      |
| `{{email}}`            | Contact's email address                |
| `{{company}}`          | Contact's company                      |
| `{{custom.FIELD}}`     | Value of `custom_fields["FIELD"]`      |

**Example template:**

```
Subject: Welcome {{first_name}}!

Hello {{first_name}} {{last_name}},

Thank you for joining us at {{company}}.
Your department is: {{custom.department}}

Best regards,
The Team
```

---

## Database Schema

MongoDB collections created automatically on first run:

| Collection      | Purpose                       | Key Fields                                                               |
|-----------------|-------------------------------|--------------------------------------------------------------------------|
| `contacts`      | Contact records               | `email` (unique index), `first_name`, `last_name`, `company`, `custom_fields` |
| `templates`     | Email templates               | `name` (unique index), `subject`, `body`, `html_body`, `created_at`     |
| `campaigns`     | Campaign definitions & stats  | `name` (unique index), `template_id`, `contact_list_ids`, `status`      |
| `contact_lists` | Named contact lists           | `name` (unique index), `contact_ids`, `description`                     |
| `email_logs`    | Delivery audit trail          | `to_email`, `subject`, `status`, `timestamp`, `error_message`           |

---

## Error Handling

| Situation                         | Behaviour                                                  |
|-----------------------------------|------------------------------------------------------------|
| Invalid email format              | `ValueError` raised by `add_contact` / `validate_email`   |
| Duplicate contact / template / campaign | `ValueError` raised (wraps `DuplicateKeyError`)      |
| SMTP send failure                 | Logged as `failed`; campaign stats updated; no exception thrown to caller |
| MongoDB connection failure        | Exception raised immediately in `__init__`                 |
| Missing template or campaign      | `ValueError` raised by `send_campaign`                     |

---

## Logging

Uses Python's built-in `logging` module at `INFO` level by default.

Events logged include:

- MongoDB connection established / failed
- Contact add / update / delete
- Template save / delete
- Campaign created / sent (with aggregate stats)
- Per-email send success / failure
- SMTP configuration changes
- CSV import results
- Log cleanup operations

---

## Security Considerations

- **Never commit `.env`** – it is already listed in `.gitignore`
- Use **Gmail App Passwords** instead of your account password
- Keep `SMTP_USE_TLS=True` (port 587) or use SSL on port 465 via `SMTP_SSL`
- Apply **MongoDB Atlas IP whitelisting** for cloud deployments
- All input email addresses are validated before storage
- Rotate SMTP credentials regularly
- Call `cleanup_old_logs()` periodically to limit sensitive data retention

---

## Performance Tips

- Unique indexes on `email`, template/campaign/list `name` are created automatically at startup
- For large campaigns (> 10 000 recipients), add a short delay between sends to respect SMTP rate limits
- Call `cleanup_old_logs(days_old=30)` on a schedule to keep the `email_logs` collection lean
- Use `import_contacts_from_csv` for bulk imports rather than looping `add_contact` externally

---

## Troubleshooting

### SMTP Authentication Failed
- Confirm your Gmail App Password is exactly 16 characters (no spaces)
- Ensure 2-Factor Authentication is enabled in your Google Account
- Run `python smtp_test.py` for step-by-step diagnostics
- Run `python smtp_fix.py` to automatically test port 587 / 465 methods

### MongoDB Connection Error
- Verify MongoDB is running: `mongod --version` / check service status
- Double-check `MONGODB_URI` in your `.env` file
- For Atlas: ensure your current IP is whitelisted and the URI includes credentials

### Email Not Delivered
- Run `python test_setup.py` to verify environment configuration
- Check logs: `manager.get_email_logs(status_filter="failed")`
- Confirm all recipient addresses pass `validate_email()`

### Connection Unexpectedly Closed (Gmail)
- `ehlo('gmail.com')` must be called after `STARTTLS` – this is already handled in `mail.py`
- Try SSL on port 465 by running `python smtp_fix.py`

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes with descriptive messages
4. Push to your branch and open a Pull Request

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## License

This project is licensed under the MIT License.
