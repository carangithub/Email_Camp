"""
mail.py – Email Campaign Manager
=================================
Core module for the Email Campaign Manager application.

Provides the following public API:

Classes
-------
EmailStatus     : Enum of possible email delivery states.
Contact         : Dataclass representing a single email contact.
EmailTemplate   : Dataclass representing a reusable email template.
Campaign        : Dataclass representing a bulk email campaign.
EmailCampaignManager : Main controller – manages contacts, templates,
                       campaigns, and SMTP delivery via MongoDB.

Usage
-----
    from mail import EmailCampaignManager, Contact, EmailTemplate, Campaign

    manager = EmailCampaignManager()
    manager.add_contact(Contact(email="user@example.com", first_name="User"))
    ...
    manager.close()

Configuration is read from a ``.env`` file (see ``.env.example``).
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pymongo
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import json
import os
from typing import List, Dict, Optional
import re
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EmailStatus(Enum):
    """Enum representing the delivery status of a single email.

    Members
    -------
    PENDING : Email is queued but has not been sent yet.
    SENT    : Email was delivered successfully.
    FAILED  : Delivery failed (SMTP error or exception).
    BOUNCED : Email was rejected / bounced by the receiving server.
    """

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


@dataclass
class Contact:
    """Dataclass representing a single email contact.

    Attributes
    ----------
    email : str
        Primary identifier – must be a valid, unique email address.
    first_name : str, optional
        Contact's first name (default ``""``).
    last_name : str, optional
        Contact's last name (default ``""``).
    company : str, optional
        Contact's company or organisation (default ``""``).
    custom_fields : dict, optional
        Arbitrary key/value pairs for any additional contact data
        (e.g. ``{"department": "Sales", "city": "NYC"}``).
        Initialised to ``{}`` if not provided.
    """

    email: str
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    custom_fields: Dict = None

    def __post_init__(self):
        if self.custom_fields is None:
            self.custom_fields = {}


@dataclass
class EmailTemplate:
    """Dataclass representing a reusable email template.

    Attributes
    ----------
    name : str
        Unique template name used to look up the template.
    subject : str
        Email subject line. Supports ``{{placeholder}}`` tokens.
    body : str
        Plain-text email body. Supports ``{{placeholder}}`` tokens.
    html_body : str, optional
        HTML email body (default ``""``). When provided it is attached
        as an ``alternative`` MIME part alongside the plain-text body.
        Supports ``{{placeholder}}`` tokens.
    created_at : datetime, optional
        Creation timestamp. Set automatically to ``datetime.now()`` if
        not provided.
    """

    name: str
    subject: str
    body: str
    html_body: str = ""
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Campaign:
    """Dataclass representing a bulk email campaign.

    Attributes
    ----------
    name : str
        Unique campaign name.
    template_id : str
        MongoDB ``_id`` (as a string) of the :class:`EmailTemplate` to use.
    contact_list_ids : list of str
        MongoDB ``_id`` strings of the contact lists to target.
    created_at : datetime, optional
        Creation timestamp; set automatically to ``datetime.now()``.
    sent_at : datetime, optional
        Timestamp when ``send_campaign()`` completed; set automatically.
    status : str
        ``"draft"`` before sending, ``"sent"`` after a successful send.
    total_recipients : int
        Total unique contacts targeted (updated after sending).
    sent_count : int
        Number of emails successfully delivered (updated after sending).
    failed_count : int
        Number of emails that failed to deliver (updated after sending).
    """

    name: str
    template_id: str
    contact_list_ids: List[str]
    created_at: datetime = None
    sent_at: datetime = None
    status: str = "draft"
    total_recipients: int = 0
    sent_count: int = 0
    failed_count: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class EmailCampaignManager:
    def __init__(self, mongodb_uri: str = None, db_name: str = None):
        """
        Initialize the Email Campaign Manager

        Args:
            mongodb_uri: MongoDB connection string (defaults to env variable)
            db_name: Database name (defaults to env variable)
        """
        # Load configuration from environment variables
        mongodb_uri = mongodb_uri or os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        db_name = db_name or os.getenv('MONGODB_DATABASE', 'email_campaigns')
        
        try:
            self.client = MongoClient(mongodb_uri)
            self.db = self.client[db_name]

            # Collections
            self.contacts_collection = self.db.contacts
            self.templates_collection = self.db.templates
            self.campaigns_collection = self.db.campaigns
            self.contact_lists_collection = self.db.contact_lists
            self.email_logs_collection = self.db.email_logs

            # Create indexes for better performance
            self.contacts_collection.create_index("email", unique=True)
            self.templates_collection.create_index("name", unique=True)
            self.campaigns_collection.create_index("name", unique=True)
            self.contact_lists_collection.create_index("name", unique=True)

            logger.info("Connected to MongoDB successfully")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

        # SMTP configuration - load from environment variables
        self.smtp_config = {
            'server': os.getenv('SMTP_SERVER', ''),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'use_tls': os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
        }
        
        # Email settings
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_config['username'])
        self.from_name = os.getenv('FROM_NAME', 'Email Campaign Manager')

    def configure_smtp(self, server: str, port: int, username: str, password: str, use_tls: bool = True):
        """Configure SMTP settings for email delivery.

        Overrides any settings previously loaded from environment variables.

        Args:
            server:   SMTP server hostname (e.g. ``"smtp.gmail.com"``).
            port:     SMTP server port (e.g. ``587`` for STARTTLS, ``465`` for SSL).
            username: SMTP login username (typically your email address).
            password: SMTP password or App Password.
            use_tls:  If ``True``, STARTTLS is used to upgrade the connection.
                      Set to ``False`` when using SSL directly on port 465.
        """
        self.smtp_config = {
            'server': server,
            'port': port,
            'username': username,
            'password': password,
            'use_tls': use_tls
        }
        logger.info(f"SMTP configured for server: {server}")

    def validate_email(self, email: str) -> bool:
        """Validate an email address format using a regex pattern.

        Args:
            email: The email address string to validate.

        Returns:
            ``True`` if the address matches a standard email pattern,
            ``False`` otherwise.
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def get_receiver_emails_from_env(self) -> List[str]:
        """Parse and validate receiver emails from the ``RECEIVER_EMAILS`` env variable.

        Reads the ``RECEIVER_EMAILS`` environment variable (a comma-separated
        list of addresses) and returns only those that pass :meth:`validate_email`.
        Invalid addresses are skipped and logged as warnings.

        Returns:
            List of valid email address strings. Empty list if ``RECEIVER_EMAILS``
            is not set or contains no valid addresses.
        """
        receiver_emails_str = os.getenv('RECEIVER_EMAILS', '')
        if not receiver_emails_str:
            return []
        
        # Split by comma and clean up whitespace
        emails = [email.strip() for email in receiver_emails_str.split(',') if email.strip()]
        
        # Validate each email
        valid_emails = []
        for email in emails:
            if self.validate_email(email):
                valid_emails.append(email)
            else:
                logger.warning(f"Invalid email address in RECEIVER_EMAILS: {email}")
        
        return valid_emails

    # Contact Management
    def add_contact(self, contact: Contact) -> str:
        """Add a new contact to the ``contacts`` collection.

        Args:
            contact: A :class:`Contact` instance to persist.

        Returns:
            The MongoDB ``_id`` string of the newly inserted document.

        Raises:
            ValueError: If ``contact.email`` is not a valid email address.
            ValueError: If a contact with that email already exists.
        """
        if not self.validate_email(contact.email):
            raise ValueError(f"Invalid email address: {contact.email}")

        try:
            contact_dict = asdict(contact)
            contact_dict['created_at'] = datetime.now()
            result = self.contacts_collection.insert_one(contact_dict)
            logger.info(f"Contact added: {contact.email}")
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Contact already exists: {contact.email}")
            raise ValueError(f"Contact with email {contact.email} already exists")

    def get_contact(self, email: str) -> Optional[Contact]:
        """Retrieve a contact by their email address.

        Args:
            email: The email address to look up.

        Returns:
            A :class:`Contact` instance if found, or ``None``.
        """
        contact_doc = self.contacts_collection.find_one({"email": email})
        if contact_doc:
            contact_doc.pop('_id', None)
            contact_doc.pop('created_at', None)
            return Contact(**contact_doc)
        return None

    def update_contact(self, email: str, updates: Dict) -> bool:
        """Update fields on an existing contact using a MongoDB ``$set`` operation.

        Args:
            email:   Email address of the contact to update.
            updates: Dictionary of field names and their new values.

        Returns:
            ``True`` if the contact was found and modified; ``False`` otherwise.
        """
        updates['updated_at'] = datetime.now()
        result = self.contacts_collection.update_one(
            {"email": email},
            {"$set": updates}
        )
        if result.modified_count > 0:
            logger.info(f"Contact updated: {email}")
            return True
        return False

    def delete_contact(self, email: str) -> bool:
        """Remove a contact from the database by email address.

        Args:
            email: Email address of the contact to delete.

        Returns:
            ``True`` if deleted; ``False`` if no matching contact was found.
        """
        result = self.contacts_collection.delete_one({"email": email})
        if result.deleted_count > 0:
            logger.info(f"Contact deleted: {email}")
            return True
        return False

    def import_contacts_from_csv(self, csv_file_path: str, mapping: Dict[str, str]) -> int:
        """
        Import contacts from CSV file

        Args:
            csv_file_path: Path to CSV file
            mapping: Dictionary mapping CSV columns to contact fields
                    e.g., {'Email': 'email', 'First Name': 'first_name'}

        Returns:
            Number of contacts imported
        """
        import pandas as pd

        try:
            df = pd.read_csv(csv_file_path)
            imported_count = 0

            for _, row in df.iterrows():
                try:
                    contact_data = {}
                    for csv_col, contact_field in mapping.items():
                        if csv_col in row and pd.notna(row[csv_col]):
                            contact_data[contact_field] = str(row[csv_col]).strip()

                    if 'email' in contact_data:
                        contact = Contact(**contact_data)
                        self.add_contact(contact)
                        imported_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import contact: {e}")
                    continue

            logger.info(f"Imported {imported_count} contacts from CSV")
            return imported_count

        except Exception as e:
            logger.error(f"Failed to import contacts from CSV: {e}")
            raise

    # Contact List Management
    def create_contact_list(self, name: str, description: str = "") -> str:
        """Create a new named contact list.

        Args:
            name:        Unique name for the contact list.
            description: Optional human-readable description.

        Returns:
            MongoDB ``_id`` string of the newly created list.

        Raises:
            ValueError: If a contact list with that name already exists.
        """
        list_doc = {
            'name': name,
            'description': description,
            'contact_ids': [],
            'created_at': datetime.now()
        }

        try:
            result = self.contact_lists_collection.insert_one(list_doc)
            logger.info(f"Contact list created: {name}")
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            raise ValueError(f"Contact list with name '{name}' already exists")

    def add_contacts_to_list(self, list_name: str, emails: List[str]) -> int:
        """Add one or more contacts (by email) to an existing contact list.

        Contacts are looked up by their email address. Only contacts that exist
        in the ``contacts`` collection are added. Duplicate entries are
        prevented via MongoDB's ``$addToSet`` operator.

        Args:
            list_name: Name of the target contact list.
            emails:    List of email addresses to add.

        Returns:
            Number of contacts successfully added to the list.
        """
        # Get contact IDs for the emails
        contact_ids = []
        for email in emails:
            contact = self.contacts_collection.find_one({"email": email})
            if contact:
                contact_ids.append(str(contact['_id']))

        result = self.contact_lists_collection.update_one(
            {"name": list_name},
            {"$addToSet": {"contact_ids": {"$each": contact_ids}}}
        )

        if result.modified_count > 0:
            logger.info(f"Added {len(contact_ids)} contacts to list: {list_name}")
            return len(contact_ids)
        return 0

    def get_contact_list_contacts(self, list_name: str) -> List[Contact]:
        """Return all contacts that belong to a named contact list.

        Args:
            list_name: Name of the contact list to query.

        Returns:
            List of :class:`Contact` instances. Returns an empty list if
            the list does not exist or contains no contacts.
        """
        list_doc = self.contact_lists_collection.find_one({"name": list_name})
        if not list_doc:
            return []

        contacts = []
        for contact_id in list_doc['contact_ids']:
            contact_doc = self.contacts_collection.find_one({"_id": ObjectId(contact_id)})
            if contact_doc:
                contact_doc.pop('_id', None)
                contact_doc.pop('created_at', None)
                contacts.append(Contact(**contact_doc))

        return contacts

    # Template Management
    def save_template(self, template: EmailTemplate) -> str:
        """Persist a new email template to the ``templates`` collection.

        Args:
            template: An :class:`EmailTemplate` instance to save.

        Returns:
            MongoDB ``_id`` string of the newly inserted document.

        Raises:
            ValueError: If a template with that name already exists.
        """
        try:
            template_dict = asdict(template)
            result = self.templates_collection.insert_one(template_dict)
            logger.info(f"Template saved: {template.name}")
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            raise ValueError(f"Template with name '{template.name}' already exists")

    def get_template(self, name: str) -> Optional[EmailTemplate]:
        """Retrieve an email template by its unique name.

        Args:
            name: The template name to look up.

        Returns:
            An :class:`EmailTemplate` instance if found, or ``None``.
        """
        template_doc = self.templates_collection.find_one({"name": name})
        if template_doc:
            template_doc.pop('_id', None)
            return EmailTemplate(**template_doc)
        return None

    def list_templates(self) -> List[str]:
        """Return the names of all saved email templates.

        Returns:
            List of template name strings (may be empty).
        """
        templates = self.templates_collection.find({}, {"name": 1})
        return [template['name'] for template in templates]

    def delete_template(self, name: str) -> bool:
        """Delete an email template by name.

        Args:
            name: Name of the template to remove.

        Returns:
            ``True`` if deleted; ``False`` if not found.
        """
        result = self.templates_collection.delete_one({"name": name})
        if result.deleted_count > 0:
            logger.info(f"Template deleted: {name}")
            return True
        return False

    # Email Personalization
    def personalize_email(self, template_content: str, contact: Contact) -> str:
        """Replace ``{{placeholder}}`` tokens in a string with contact field values.

        Supported placeholders
        ----------------------
        ``{{first_name}}``       → ``contact.first_name``
        ``{{last_name}}``        → ``contact.last_name``
        ``{{full_name}}``        → ``first_name + " " + last_name`` (stripped)
        ``{{email}}``            → ``contact.email``
        ``{{company}}``          → ``contact.company``
        ``{{custom.FIELD}}``     → ``contact.custom_fields["FIELD"]``

        Unknown placeholders are left unchanged.

        Args:
            template_content: Raw string containing zero or more
                              ``{{placeholder}}`` tokens.
            contact:          :class:`Contact` whose data will be substituted.

        Returns:
            The personalised string with all known placeholders replaced.
        """
        content = template_content

        # Replace basic fields
        placeholders = {
            '{{first_name}}': contact.first_name,
            '{{last_name}}': contact.last_name,
            '{{email}}': contact.email,
            '{{company}}': contact.company,
            '{{full_name}}': f"{contact.first_name} {contact.last_name}".strip()
        }

        for placeholder, value in placeholders.items():
            content = content.replace(placeholder, str(value))

        # Replace custom fields
        if contact.custom_fields:
            for field_name, field_value in contact.custom_fields.items():
                placeholder = "{{custom." + field_name + "}}"
                content = content.replace(placeholder, str(field_value))

        return content

    # Email Sending
    def send_single_email(self, to_email: str, subject: str, body: str, html_body: str = "",
                          attachments: List[str] = None) -> bool:
        """Send a single email via the configured SMTP server.

        Builds a ``multipart/alternative`` MIME message. If ``html_body`` is
        provided it is attached as the ``text/html`` alternative part.
        File attachments are added as ``application/octet-stream`` parts.

        The connection uses STARTTLS (port 587) when ``smtp_config['use_tls']``
        is ``True``, which is the default. ``ehlo('gmail.com')`` is called
        before and after ``STARTTLS`` to satisfy Gmail's requirements.

        A log entry is written to the ``email_logs`` collection regardless of
        success or failure.

        Args:
            to_email:    Recipient email address.
            subject:     Email subject line.
            body:        Plain-text email body.
            html_body:   HTML email body (optional; default ``""``).
            attachments: List of file paths to attach (optional).

        Returns:
            ``True`` if the email was sent successfully; ``False`` on failure.

        Raises:
            ValueError: If SMTP is not configured (``smtp_config['server']``
                        is empty).
        """
        if not self.smtp_config['server']:
            raise ValueError("SMTP configuration not set. Use configure_smtp() first.")

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)

            # Create SMTP session with proper FQDN
            server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
            server.ehlo('gmail.com')  # Use gmail.com as FQDN for Gmail

            if self.smtp_config['use_tls']:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo('gmail.com')  # Call ehlo again after STARTTLS

            server.login(self.smtp_config['username'], self.smtp_config['password'])

            # Send email
            server.send_message(msg)
            server.quit()

            # Log the email
            self.log_email(to_email, subject, EmailStatus.SENT.value)
            logger.info(f"Email sent successfully to: {to_email}")
            return True

        except Exception as e:
            self.log_email(to_email, subject, EmailStatus.FAILED.value, str(e))
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def log_email(self, to_email: str, subject: str, status: str, error_message: str = ""):
        """Record an email delivery attempt in the ``email_logs`` collection.

        Called automatically by :meth:`send_single_email` after each send
        attempt. Each log entry includes a UTC timestamp.

        Args:
            to_email:      Recipient address.
            subject:       Email subject.
            status:        Delivery status string (see :class:`EmailStatus`).
            error_message: Optional error detail for failed deliveries.
        """
        log_entry = {
            'to_email': to_email,
            'subject': subject,
            'status': status,
            'timestamp': datetime.now(),
            'error_message': error_message
        }
        self.email_logs_collection.insert_one(log_entry)

    # Campaign Management
    def create_campaign(self, campaign: Campaign) -> str:
        """Persist a new campaign to the ``campaigns`` collection.

        The campaign is saved with ``status="draft"``. Use
        :meth:`send_campaign` to execute it.

        Args:
            campaign: A :class:`Campaign` instance to save.

        Returns:
            MongoDB ``_id`` string of the newly inserted campaign document.

        Raises:
            ValueError: If a campaign with that name already exists.
        """
        try:
            campaign_dict = asdict(campaign)
            result = self.campaigns_collection.insert_one(campaign_dict)
            logger.info(f"Campaign created: {campaign.name}")
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            raise ValueError(f"Campaign with name '{campaign.name}' already exists")

    def send_campaign(self, campaign_name: str, attachments: List[str] = None) -> Dict[str, int]:
        """
        Send an email campaign

        Returns:
            Dictionary with send statistics: {'sent': int, 'failed': int, 'total': int}
        """
        # Get campaign
        campaign_doc = self.campaigns_collection.find_one({"name": campaign_name})
        if not campaign_doc:
            raise ValueError(f"Campaign not found: {campaign_name}")

        # Get template
        template_doc = self.templates_collection.find_one({"_id": ObjectId(campaign_doc['template_id'])})
        if not template_doc:
            raise ValueError(f"Template not found for campaign: {campaign_name}")

        template_doc.pop('_id', None)
        template = EmailTemplate(**template_doc)

        # Get all contacts from contact lists
        all_contacts = []
        for list_id in campaign_doc['contact_list_ids']:
            list_doc = self.contact_lists_collection.find_one({"_id": ObjectId(list_id)})
            if list_doc:
                for contact_id in list_doc['contact_ids']:
                    contact_doc = self.contacts_collection.find_one({"_id": ObjectId(contact_id)})
                    if contact_doc:
                        contact_doc.pop('_id', None)
                        contact_doc.pop('created_at', None)
                        all_contacts.append(Contact(**contact_doc))

        # Remove duplicates based on email
        unique_contacts = []
        seen_emails = set()
        for contact in all_contacts:
            if contact.email not in seen_emails:
                unique_contacts.append(contact)
                seen_emails.add(contact.email)

        # Send emails
        sent_count = 0
        failed_count = 0
        total_count = len(unique_contacts)

        logger.info(f"Starting campaign: {campaign_name} to {total_count} recipients")

        for contact in unique_contacts:
            try:
                # Personalize email content
                personalized_subject = self.personalize_email(template.subject, contact)
                personalized_body = self.personalize_email(template.body, contact)
                personalized_html = self.personalize_email(template.html_body, contact) if template.html_body else ""

                # Send email
                if self.send_single_email(
                        to_email=contact.email,
                        subject=personalized_subject,
                        body=personalized_body,
                        html_body=personalized_html,
                        attachments=attachments
                ):
                    sent_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Failed to send email to {contact.email}: {e}")
                failed_count += 1

        # Update campaign status
        self.campaigns_collection.update_one(
            {"name": campaign_name},
            {
                "$set": {
                    "status": "sent",
                    "sent_at": datetime.now(),
                    "total_recipient": total_count,
                    "sent_count": sent_count,
                    "failed_count": failed_count
                }
            }
        )

        stats = {"sent": sent_count, "failed": failed_count, "total": total_count}
        logger.info(f"Campaign completed: {campaign_name} - {stats}")
        return stats

    def get_campaign_stats(self, campaign_name: str) -> Dict:
        """Return delivery statistics for a campaign.

        Args:
            campaign_name: Name of the campaign to query.

        Returns:
            Dictionary with keys:
            ``name``, ``status``, ``total_recipient``,
            ``sent_count``, ``failed_count``, ``created_at``, ``sent_at``.

        Raises:
            ValueError: If no campaign with that name exists.
        """
        campaign_doc = self.campaigns_collection.find_one({"name": campaign_name})
        if not campaign_doc:
            raise ValueError(f"Campaign not found: {campaign_name}")

        return {
            "name": campaign_doc["name"],
            "status": campaign_doc.get("status", "draft"),
            "total_recipient": campaign_doc.get("total_recipient", 0),
            "sent_count": campaign_doc.get("sent_count", 0),
            "failed_count": campaign_doc.get("failed_count", 0),
            "created_at": campaign_doc.get("created_at"),
            "sent_at": campaign_doc.get("sent_at")
        }

    def list_campaigns(self) -> List[str]:
        """Return the names of all campaigns in the database.

        Returns:
            List of campaign name strings (may be empty).
        """
        campaigns = self.campaigns_collection.find({}, {"name": 1})
        return [campaign['name'] for campaign in campaigns]

    # Utility Methods
    def get_email_logs(self, limit: int = 100, status_filter: str = None) -> List[Dict]:
        """Retrieve recent email delivery log entries, newest first.

        Args:
            limit:         Maximum number of log entries to return (default ``100``).
            status_filter: If provided, only entries with this status value are
                           returned (e.g. ``"failed"``, ``"sent"``).

        Returns:
            List of log dictionaries. Each dict contains:
            ``to_email``, ``subject``, ``status``, ``timestamp``,
            ``error_message``.
        """
        query = {}
        if status_filter:
            query['status'] = status_filter

        logs = self.email_logs_collection.find(query).sort("timestamp", -1).limit(limit)
        return list(logs)

    def cleanup_old_logs(self, days_old: int = 30):
        """Delete email log entries older than a specified number of days.

        Useful for keeping the ``email_logs`` collection lean in long-running
        deployments. Call periodically (e.g. via a scheduled task).

        Args:
            days_old: Entries older than this many days will be deleted
                      (default ``30``).
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)
        result = self.email_logs_collection.delete_many({"timestamp": {"$lt": cutoff_date}})
        logger.info(f"Cleaned up {result.deleted_count} old email logs")

    def export_contacts(self, output_file: str, contact_list_name: str = None):
        """Export contacts to a CSV file using pandas.

        Args:
            output_file:         Destination file path (e.g. ``"contacts.csv"``).
            contact_list_name:   If provided, exports only contacts in that
                                 list; otherwise all contacts are exported.
        """
        import pandas as pd

        if contact_list_name:
            contacts = self.get_contact_list_contacts(contact_list_name)
        else:
            # Export all contacts
            contacts = []
            for contact_doc in self.contacts_collection.find():
                contact_doc.pop('_id', None)
                contact_doc.pop('created_at', None)
                contacts.append(Contact(**contact_doc))

        # Convert to DataFrame
        contact_dicts = [asdict(contact) for contact in contacts]
        df = pd.DataFrame(contact_dicts)

        # Save to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Exported {len(contacts)} contacts to {output_file}")

    def close(self):
        """Close the MongoDB client connection.

        Always call this method when you are finished with the manager to
        release the connection pool cleanly.
        """
        self.client.close()
        logger.info("Database connection closed")


# Example Usage and CLI Interface
def main():
    """Example usage of the Email Campaign Manager"""

    # Initialize the manager (automatically loads from .env)
    manager = EmailCampaignManager()

    # SMTP is automatically configured from .env file
    print(f"SMTP Server: {manager.smtp_config['server']}")
    print(f"From Email: {manager.from_email}")
    print(f"From Name: {manager.from_name}")

    try:
        # Get receiver emails from .env file
        receiver_emails = manager.get_receiver_emails_from_env()
        print(f"Receiver emails from .env: {receiver_emails}")
        
        if not receiver_emails:
            print("No valid receiver emails found in .env file. Please update RECEIVER_EMAILS.")
            return

        # Create contacts from receiver emails
        contacts_to_add = []
        for i, email in enumerate(receiver_emails):
            # Extract name from email (simple approach)
            name_part = email.split('@')[0]
            first_name = name_part.capitalize()
            
            contact = Contact(
                email=email,
                first_name=first_name,
                last_name="",
                company="From Environment",
                custom_fields={"source": "env_file"}
            )
            contacts_to_add.append(contact)

        # Add contacts (handle duplicates)
        added_contacts = []
        for contact in contacts_to_add:
            try:
                manager.add_contact(contact)
                added_contacts.append(contact.email)
                print(f"Added contact: {contact.email}")
            except ValueError as e:
                print(f"Contact may already exist: {e}")
                added_contacts.append(contact.email)  # Add to list anyway for campaign

        # Create a contact list
        list_name = os.getenv('DEFAULT_CONTACT_LIST_NAME', 'Default Recipients')
        try:
            list_id = manager.create_contact_list(list_name, "Contacts from environment file")
            print(f"Created contact list: {list_name}")
        except ValueError:
            print(f"Contact list '{list_name}' may already exist")

        # Add contacts to list
        if added_contacts:
            count = manager.add_contacts_to_list(list_name, added_contacts)
            print(f"Added {count} contacts to list: {list_name}")

        # Create email template
        template = EmailTemplate(
            name="Welcome Email",
            subject="Welcome {{first_name}}! Thanks for subscribing",
            body="""
            Hello {{first_name}} {{last_name}},

            Welcome to our newsletter! We're excited to have you from {{company}}.

            Your email: {{email}}
            Department: {{custom.department}}
            Location: {{custom.city}}

            Best regards,
            The Team
            """,
            html_body="""
            <html>
            <body>
            <h2>Hello {{first_name}} {{last_name}},</h2>

            <p>Welcome to our newsletter! We're excited to have you from <strong>{{company}}</strong>.</p>

            <p>Your details:</p>
            <ul>
                <li>Email: {{email}}</li>
                <li>Department: {{custom.department}}</li>
                <li>Location: {{custom.city}}</li>
            </ul>

            <p>Best regards,<br>The Team</p>
            </body>
            </html>
            """
        )

        # Save template (handle duplicates)
        try:
            template_id = manager.save_template(template)
        except ValueError:
            print("Template may already exist")
            template_doc = manager.templates_collection.find_one({"name": "Welcome Email"})
            template_id = str(template_doc['_id']) if template_doc else None

        if template_id:
            # Create campaign using the contact list from environment
            list_doc = manager.contact_lists_collection.find_one({"name": list_name})
            list_id = str(list_doc['_id']) if list_doc else None

            if list_id:
                campaign_name = "Environment Campaign 2024"
                campaign = Campaign(
                    name=campaign_name,
                    template_id=template_id,
                    contact_list_ids=[list_id]
                )

                try:
                    campaign_id = manager.create_campaign(campaign)
                    print(f"Campaign created with ID: {campaign_id}")

                    # Send campaign (SMTP is now configured from .env)
                    if manager.smtp_config['server']:
                        print(f"Sending campaign to {len(receiver_emails)} recipients...")
                        stats = manager.send_campaign(campaign_name)
                        print(f"Campaign results: {stats}")
                    else:
                        print("SMTP not configured. Please check your .env file.")

                except ValueError as e:
                    print(f"Campaign may already exist: {e}")
                    # Try to send existing campaign
                    if manager.smtp_config['server']:
                        try:
                            stats = manager.send_campaign(campaign_name)
                            print(f"Sent existing campaign: {stats}")
                        except Exception as send_error:
                            print(f"Error sending campaign: {send_error}")

        # List templates and campaigns
        print(f"Templates: {manager.list_templates()}")
        print(f"Campaigns: {manager.list_campaigns()}")

        # Get email logs
        logs = manager.get_email_logs(limit=10)
        print(f"Recent email logs: {len(logs)} entries")

    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Application error: {e}")

    finally:
        manager.close()


if __name__ == "__main__":
    main()