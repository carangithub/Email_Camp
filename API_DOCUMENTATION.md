# API Documentation – Email Campaign Manager

This document provides a complete reference for every public class and method exposed by `mail.py`.

---

## Table of Contents

- [Classes](#classes)
  - [EmailStatus](#emailstatus)
  - [Contact](#contact)
  - [EmailTemplate](#emailtemplate)
  - [Campaign](#campaign)
  - [EmailCampaignManager](#emailcampaignmanager)
- [Methods](#methods)
  - [Initialization & Configuration](#initialization--configuration)
  - [Contact Management](#contact-management)
  - [Contact List Management](#contact-list-management)
  - [Template Management](#template-management)
  - [Email Personalization](#email-personalization)
  - [Email Sending](#email-sending)
  - [Campaign Management](#campaign-management)
  - [Logging & Utilities](#logging--utilities)
- [Exceptions](#exceptions)
- [Environment Variables Reference](#environment-variables-reference)

---

## Classes

### `EmailStatus`

An `Enum` representing possible states of an email delivery attempt.

| Member    | Value      | Description                       |
|-----------|------------|-----------------------------------|
| `PENDING` | `"pending"`| Queued but not yet attempted      |
| `SENT`    | `"sent"`   | Delivered successfully            |
| `FAILED`  | `"failed"` | Delivery failed                   |
| `BOUNCED` | `"bounced"`| Bounced back by receiving server  |

---

### `Contact`

A `dataclass` representing a single email contact.

```python
@dataclass
class Contact:
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    custom_fields: Dict = None   # auto-initialised to {} if None
```

| Field          | Type   | Required | Description                                                |
|----------------|--------|----------|------------------------------------------------------------|
| `email`        | `str`  | ✅        | Primary key – must be a valid email address and unique     |
| `first_name`   | `str`  | ❌        | Contact's first name                                       |
| `last_name`    | `str`  | ❌        | Contact's last name                                        |
| `company`      | `str`  | ❌        | Contact's company or organisation                         |
| `custom_fields`| `dict` | ❌        | Arbitrary extra data (e.g. `{"department": "Sales"}`)     |

---

### `EmailTemplate`

A `dataclass` representing a reusable email template.

```python
@dataclass
class EmailTemplate:
    name: str
    subject: str
    body: str
    html_body: str = ""
    created_at: datetime = None   # auto-set to datetime.now() if None
```

| Field        | Type       | Required | Description                                   |
|--------------|------------|----------|-----------------------------------------------|
| `name`       | `str`      | ✅        | Unique template identifier                    |
| `subject`    | `str`      | ✅        | Email subject line; supports `{{placeholders}}`|
| `body`       | `str`      | ✅        | Plain-text body; supports `{{placeholders}}`  |
| `html_body`  | `str`      | ❌        | HTML body; supports `{{placeholders}}`        |
| `created_at` | `datetime` | auto     | Populated automatically on creation           |

---

### `Campaign`

A `dataclass` representing a bulk email campaign.

```python
@dataclass
class Campaign:
    name: str
    template_id: str
    contact_list_ids: List[str]
    created_at: datetime = None
    sent_at: datetime = None
    status: str = "draft"
    total_recipients: int = 0
    sent_count: int = 0
    failed_count: int = 0
```

| Field                | Type         | Required | Description                                              |
|----------------------|--------------|----------|----------------------------------------------------------|
| `name`               | `str`        | ✅        | Unique campaign name                                     |
| `template_id`        | `str`        | ✅        | MongoDB `_id` string of the `EmailTemplate` to use      |
| `contact_list_ids`   | `list[str]`  | ✅        | MongoDB `_id` strings of target `contact_lists`         |
| `status`             | `str`        | auto     | `"draft"` before sending, `"sent"` after                |
| `total_recipients`   | `int`        | auto     | Number of unique recipients targeted                    |
| `sent_count`         | `int`        | auto     | Number of emails successfully delivered                 |
| `failed_count`       | `int`        | auto     | Number of emails that failed to deliver                 |
| `created_at`         | `datetime`   | auto     | Set automatically on creation                           |
| `sent_at`            | `datetime`   | auto     | Set when `send_campaign()` completes                    |

---

### `EmailCampaignManager`

Main controller class. Manages MongoDB connections, SMTP configuration, and all CRUD operations.

```python
manager = EmailCampaignManager(mongodb_uri=None, db_name=None)
```

---

## Methods

### Initialization & Configuration

---

#### `__init__(mongodb_uri=None, db_name=None)`

Connects to MongoDB and loads SMTP settings from environment variables.

**Parameters**

| Name          | Type            | Default | Description                                    |
|---------------|-----------------|---------|------------------------------------------------|
| `mongodb_uri` | `str` or `None` | `None`  | Falls back to `MONGODB_URI` env var, then `mongodb://localhost:27017/` |
| `db_name`     | `str` or `None` | `None`  | Falls back to `MONGODB_DATABASE` env var, then `email_campaigns` |

**Raises**
- Any `pymongo` connection exception if MongoDB is unreachable.

**Side effects**
- Creates unique indexes on `contacts.email`, `templates.name`, `campaigns.name`, `contact_lists.name`.

---

#### `configure_smtp(server, port, username, password, use_tls=True)`

Overrides SMTP settings that were loaded from the environment.

**Parameters**

| Name       | Type   | Default | Description                      |
|------------|--------|---------|----------------------------------|
| `server`   | `str`  | —       | SMTP server hostname             |
| `port`     | `int`  | —       | SMTP server port                 |
| `username` | `str`  | —       | SMTP login username              |
| `password` | `str`  | —       | SMTP login password / App Password |
| `use_tls`  | `bool` | `True`  | Whether to use STARTTLS          |

---

#### `close()`

Closes the MongoDB client connection. Always call this when you are done with the manager.

```python
manager.close()
```

---

### Contact Management

---

#### `add_contact(contact) -> str`

Adds a new contact to the `contacts` collection.

**Parameters**

| Name      | Type      | Description          |
|-----------|-----------|----------------------|
| `contact` | `Contact` | Contact to add       |

**Returns** – MongoDB `_id` string of the inserted document.

**Raises**
- `ValueError` – if `contact.email` is not a valid email address.
- `ValueError` – if a contact with that email already exists.

```python
contact_id = manager.add_contact(Contact(
    email="jane@example.com",
    first_name="Jane",
    last_name="Smith"
))
```

---

#### `get_contact(email) -> Optional[Contact]`

Retrieves a contact by their email address.

**Parameters**

| Name    | Type  | Description             |
|---------|-------|-------------------------|
| `email` | `str` | Email address to look up |

**Returns** – A `Contact` instance, or `None` if not found.

```python
contact = manager.get_contact("jane@example.com")
```

---

#### `update_contact(email, updates) -> bool`

Updates fields on an existing contact.

**Parameters**

| Name      | Type   | Description                                    |
|-----------|--------|------------------------------------------------|
| `email`   | `str`  | Email of the contact to update                 |
| `updates` | `dict` | Dictionary of fields to update (MongoDB `$set`) |

**Returns** – `True` if the contact was modified; `False` otherwise.

```python
manager.update_contact("jane@example.com", {"company": "New Corp"})
```

---

#### `delete_contact(email) -> bool`

Removes a contact from the database.

**Parameters**

| Name    | Type  | Description                    |
|---------|-------|--------------------------------|
| `email` | `str` | Email of the contact to delete |

**Returns** – `True` if deleted; `False` if not found.

```python
manager.delete_contact("jane@example.com")
```

---

#### `import_contacts_from_csv(csv_file_path, mapping) -> int`

Bulk-imports contacts from a CSV file.

**Parameters**

| Name             | Type   | Description                                                        |
|------------------|--------|--------------------------------------------------------------------|
| `csv_file_path`  | `str`  | Path to the CSV file                                               |
| `mapping`        | `dict` | Maps CSV column names to `Contact` field names                     |

**Mapping example:**
```python
mapping = {
    "Email Address": "email",
    "First":         "first_name",
    "Last":          "last_name",
    "Company":       "company"
}
```

**Returns** – Number of contacts successfully imported.

**Raises** – Any `pandas` or I/O exception if the file cannot be read.

---

#### `export_contacts(output_file, contact_list_name=None)`

Exports contacts to a CSV file.

**Parameters**

| Name                  | Type            | Default | Description                                    |
|-----------------------|-----------------|---------|------------------------------------------------|
| `output_file`         | `str`           | —       | Destination file path                          |
| `contact_list_name`   | `str` or `None` | `None`  | If provided, exports only contacts in that list; otherwise exports all contacts |

```python
manager.export_contacts("all_contacts.csv")
manager.export_contacts("vip_list.csv", contact_list_name="VIP")
```

---

### Contact List Management

---

#### `create_contact_list(name, description="") -> str`

Creates a new named contact list.

**Parameters**

| Name          | Type  | Default | Description          |
|---------------|-------|---------|----------------------|
| `name`        | `str` | —       | Unique list name     |
| `description` | `str` | `""`    | Optional description |

**Returns** – MongoDB `_id` string of the new list.

**Raises** – `ValueError` if a list with that name already exists.

```python
list_id = manager.create_contact_list("Newsletter", "Monthly newsletter subscribers")
```

---

#### `add_contacts_to_list(list_name, emails) -> int`

Adds one or more contacts (by email) to an existing contact list.

**Parameters**

| Name        | Type        | Description                       |
|-------------|-------------|-----------------------------------|
| `list_name` | `str`       | Name of the target contact list   |
| `emails`    | `list[str]` | Email addresses to add to the list |

**Returns** – Number of contacts successfully added.

```python
added = manager.add_contacts_to_list("Newsletter", ["a@x.com", "b@x.com"])
```

---

#### `get_contact_list_contacts(list_name) -> list[Contact]`

Returns all `Contact` objects that belong to a named list.

**Parameters**

| Name        | Type  | Description               |
|-------------|-------|---------------------------|
| `list_name` | `str` | Name of the contact list  |

**Returns** – List of `Contact` instances (empty list if the list doesn't exist).

```python
contacts = manager.get_contact_list_contacts("Newsletter")
```

---

### Template Management

---

#### `save_template(template) -> str`

Persists a new `EmailTemplate` to the database.

**Parameters**

| Name       | Type            | Description       |
|------------|-----------------|-------------------|
| `template` | `EmailTemplate` | Template to save  |

**Returns** – MongoDB `_id` string of the inserted template.

**Raises** – `ValueError` if a template with that name already exists.

```python
template_id = manager.save_template(EmailTemplate(
    name="Promo",
    subject="Special offer for {{first_name}}!",
    body="Hi {{first_name}}, we have a special deal for you."
))
```

---

#### `get_template(name) -> Optional[EmailTemplate]`

Retrieves a template by name.

**Returns** – An `EmailTemplate` instance, or `None` if not found.

```python
t = manager.get_template("Promo")
```

---

#### `list_templates() -> list[str]`

Returns the names of all saved templates.

```python
names = manager.list_templates()  # e.g. ["Welcome Email", "Promo"]
```

---

#### `delete_template(name) -> bool`

Deletes a template by name.

**Returns** – `True` if deleted; `False` if not found.

```python
manager.delete_template("Promo")
```

---

### Email Personalization

---

#### `personalize_email(template_content, contact) -> str`

Replaces `{{placeholder}}` tokens in a string with values from a `Contact`.

**Parameters**

| Name               | Type      | Description                            |
|--------------------|-----------|----------------------------------------|
| `template_content` | `str`     | Raw template text containing placeholders |
| `contact`          | `Contact` | Contact whose data will be substituted |

**Supported placeholders:**

| Placeholder          | Source                          |
|----------------------|---------------------------------|
| `{{first_name}}`     | `contact.first_name`            |
| `{{last_name}}`      | `contact.last_name`             |
| `{{full_name}}`      | `first_name + " " + last_name`  |
| `{{email}}`          | `contact.email`                 |
| `{{company}}`        | `contact.company`               |
| `{{custom.FIELD}}`   | `contact.custom_fields["FIELD"]`|

**Returns** – The personalised string with all known placeholders replaced.

```python
body = manager.personalize_email("Hello {{first_name}}!", contact)
```

---

### Email Sending

---

#### `send_single_email(to_email, subject, body, html_body="", attachments=None) -> bool`

Sends one email via the configured SMTP server.

**Parameters**

| Name          | Type            | Default | Description                                  |
|---------------|-----------------|---------|----------------------------------------------|
| `to_email`    | `str`           | —       | Recipient email address                      |
| `subject`     | `str`           | —       | Email subject line                           |
| `body`        | `str`           | —       | Plain-text email body                        |
| `html_body`   | `str`           | `""`    | HTML email body (sent as alternative part)   |
| `attachments` | `list[str]`     | `None`  | File paths to attach to the email            |

**Returns** – `True` on success; `False` on failure (failure is also logged).

**Raises** – `ValueError` if SMTP is not configured.

```python
ok = manager.send_single_email(
    to_email="user@example.com",
    subject="Hello!",
    body="Plain text body",
    html_body="<p>HTML body</p>",
    attachments=["/path/to/file.pdf"]
)
```

---

#### `validate_email(email) -> bool`

Validates an email address against a standard RFC-style regex pattern.

**Parameters**

| Name    | Type  | Description              |
|---------|-------|--------------------------|
| `email` | `str` | Email address to validate |

**Returns** – `True` if valid; `False` otherwise.

```python
manager.validate_email("user@example.com")  # True
manager.validate_email("not-an-email")       # False
```

---

#### `get_receiver_emails_from_env() -> list[str]`

Parses the `RECEIVER_EMAILS` environment variable and returns a list of validated email addresses.

**Returns** – List of valid email strings (invalid entries are skipped with a warning log).

```python
emails = manager.get_receiver_emails_from_env()
```

---

### Campaign Management

---

#### `create_campaign(campaign) -> str`

Saves a new `Campaign` document to the database with `status="draft"`.

**Parameters**

| Name       | Type       | Description         |
|------------|------------|---------------------|
| `campaign` | `Campaign` | Campaign to create  |

**Returns** – MongoDB `_id` string of the new campaign.

**Raises** – `ValueError` if a campaign with that name already exists.

```python
campaign_id = manager.create_campaign(Campaign(
    name="Spring Sale",
    template_id=template_id,
    contact_list_ids=[list_id]
))
```

---

#### `send_campaign(campaign_name, attachments=None) -> dict`

Executes a campaign: retrieves all contacts from the target lists, personalises the template for each, and sends individual emails.

**Parameters**

| Name              | Type            | Default | Description                              |
|-------------------|-----------------|---------|------------------------------------------|
| `campaign_name`   | `str`           | —       | Name of the campaign to send             |
| `attachments`     | `list[str]`     | `None`  | File paths to attach to every email      |

**Returns** – A stats dictionary:
```python
{"sent": int, "failed": int, "total": int}
```

**Raises**
- `ValueError` – if the campaign is not found.
- `ValueError` – if the campaign's template is not found.

**Side effects** – Updates the campaign document in MongoDB (`status`, `sent_at`, `sent_count`, `failed_count`, `total_recipient`).

```python
stats = manager.send_campaign("Spring Sale")
print(stats)  # {'sent': 95, 'failed': 5, 'total': 100}
```

---

#### `get_campaign_stats(campaign_name) -> dict`

Returns statistics for a campaign.

**Returns:**
```python
{
    "name": str,
    "status": str,           # "draft" or "sent"
    "total_recipient": int,
    "sent_count": int,
    "failed_count": int,
    "created_at": datetime,
    "sent_at": datetime      # None if not yet sent
}
```

**Raises** – `ValueError` if the campaign is not found.

```python
stats = manager.get_campaign_stats("Spring Sale")
```

---

#### `list_campaigns() -> list[str]`

Returns the names of all campaigns in the database.

```python
campaigns = manager.list_campaigns()
```

---

### Logging & Utilities

---

#### `log_email(to_email, subject, status, error_message="")`

Records an email delivery attempt to the `email_logs` collection. Called internally by `send_single_email`.

| Name            | Type  | Description                                    |
|-----------------|-------|------------------------------------------------|
| `to_email`      | `str` | Recipient address                              |
| `subject`       | `str` | Email subject                                  |
| `status`        | `str` | `EmailStatus` value string (`"sent"`, `"failed"`, etc.) |
| `error_message` | `str` | Optional error detail for failed sends         |

---

#### `get_email_logs(limit=100, status_filter=None) -> list[dict]`

Retrieves recent email log entries, newest first.

**Parameters**

| Name            | Type            | Default | Description                                 |
|-----------------|-----------------|---------|---------------------------------------------|
| `limit`         | `int`           | `100`   | Maximum number of log entries to return     |
| `status_filter` | `str` or `None` | `None`  | If set, returns only entries with this status (e.g. `"failed"`) |

**Returns** – List of log dictionaries with keys: `to_email`, `subject`, `status`, `timestamp`, `error_message`.

```python
failed_logs = manager.get_email_logs(limit=50, status_filter="failed")
```

---

#### `cleanup_old_logs(days_old=30)`

Deletes `email_logs` entries older than the specified number of days.

**Parameters**

| Name       | Type  | Default | Description                   |
|------------|-------|---------|-------------------------------|
| `days_old` | `int` | `30`    | Age threshold in days         |

```python
manager.cleanup_old_logs(days_old=60)
```

---

## Exceptions

| Exception                         | When raised                                                      |
|-----------------------------------|------------------------------------------------------------------|
| `ValueError`                      | Invalid email, duplicate contact / template / campaign, missing campaign or template |
| `pymongo.errors.DuplicateKeyError`| Caught internally; re-raised as `ValueError`                    |
| `smtplib.SMTPException` subclasses| Caught per email in `send_single_email`; logged, not propagated |
| General `Exception`               | MongoDB connection failure propagated from `__init__`           |

---

## Environment Variables Reference

| Variable                     | Used By                          | Description                                     |
|------------------------------|----------------------------------|-------------------------------------------------|
| `MONGODB_URI`                | `__init__`                       | MongoDB connection string                       |
| `MONGODB_DATABASE`           | `__init__`                       | Database name                                   |
| `SMTP_SERVER`                | `__init__`                       | SMTP hostname                                   |
| `SMTP_PORT`                  | `__init__`                       | SMTP port (default `587`)                       |
| `SMTP_USERNAME`              | `__init__`, `send_single_email`  | SMTP login                                      |
| `SMTP_PASSWORD`              | `__init__`, `send_single_email`  | SMTP password / App Password                    |
| `SMTP_USE_TLS`               | `__init__`                       | `"True"` / `"False"` – enables STARTTLS        |
| `FROM_EMAIL`                 | `send_single_email`              | Sender address in `From:` header                |
| `FROM_NAME`                  | `send_single_email`              | Sender display name in `From:` header           |
| `RECEIVER_EMAILS`            | `get_receiver_emails_from_env`   | Comma-separated list of recipient emails        |
| `DEFAULT_CONTACT_LIST_NAME`  | `main()` in `mail.py`           | Default contact list name used in demo          |
