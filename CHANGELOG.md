# Changelog

All notable changes to the Email Campaign Manager are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- `API_DOCUMENTATION.md` – full API reference for all classes and methods
- `CONTRIBUTING.md` – contributor guidelines
- `CHANGELOG.md` – this file
- `.env.example` – environment configuration template
- Improved `README.md` with badges, tables, and expanded sections

---

## [1.0.0] – 2024-08-01

### Added
- `EmailCampaignManager` core class with MongoDB integration
- `Contact`, `EmailTemplate`, `Campaign` data classes
- `EmailStatus` enum (`PENDING`, `SENT`, `FAILED`, `BOUNCED`)
- Contact CRUD: `add_contact`, `get_contact`, `update_contact`, `delete_contact`
- CSV import via `import_contacts_from_csv` (pandas-backed)
- CSV export via `export_contacts`
- Template CRUD: `save_template`, `get_template`, `list_templates`, `delete_template`
- Contact list management: `create_contact_list`, `add_contacts_to_list`, `get_contact_list_contacts`
- Email personalisation engine: `{{first_name}}`, `{{last_name}}`, `{{full_name}}`, `{{email}}`, `{{company}}`, `{{custom.FIELD}}`
- Campaign management: `create_campaign`, `send_campaign`, `get_campaign_stats`, `list_campaigns`
- SMTP delivery via `send_single_email` with TLS/SSL support and file attachment handling
- Email delivery logging to MongoDB (`email_logs` collection)
- `get_email_logs` and `cleanup_old_logs` utilities
- Environment-variable–based configuration via `python-dotenv`
- Auto-created unique indexes on `contacts.email`, `templates.name`, `campaigns.name`, `contact_lists.name`
- `test_setup.py` – interactive setup verification script
- `smtp_test.py` – step-by-step SMTP connection diagnostic
- `smtp_fix.py` – multi-method Gmail SMTP troubleshooting tool
- `gmail_test.py` – minimal Gmail send test
- `create_word_doc.py` – auto-generates a Word `.docx` project report
- `requirements.txt` with pinned minimum versions for `pymongo`, `pandas`, `python-dotenv`, `dnspython`
