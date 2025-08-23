# Email Campaign Manager
# A comprehensive tool for managing email campaigns with MongoDB and SMTP

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pymongo
from pymongo import MongoClient
from datetime import datetime
import json
import os
from typing import List, Dict, Optional
import re
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EmailStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


@dataclass
class Contact:
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
    def __init__(self, mongodb_uri: str = "mongodb://localhost:27017/", db_name: str = "email_campaigns"):
        """
        Initialize the Email Campaign Manager

        Args:
            mongodb_uri: MongoDB connection string
            db_name: Database name
        """
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

        # SMTP configuration
        self.smtp_config = {
            'server': '',
            'port': 587,
            'username': '',
            'password': '',
            'use_tls': True
        }

    def configure_smtp(self, server: str, port: int, username: str, password: str, use_tls: bool = True):
        """Configure SMTP settings for email delivery"""
        self.smtp_config = {
            'server': server,
            'port': port,
            'username': username,
            'password': password,
            'use_tls': use_tls
        }
        logger.info(f"SMTP configured for server: {server}")

    def validate_email(self, email: str) -> bool:
        """Validate email address format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    # Contact Management
    def add_contact(self, contact: Contact) -> str:
        """Add a new contact to the database"""
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
        """Retrieve a contact by email"""
        contact_doc = self.contacts_collection.find_one({"email": email})
        if contact_doc:
            contact_doc.pop('_id', None)
            contact_doc.pop('created_at', None)
            return Contact(**contact_doc)
        return None

    def update_contact(self, email: str, updates: Dict) -> bool:
        """Update an existing contact"""
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
        """Delete a contact"""
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
        """Create a new contact list"""
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
        """Add contacts to a contact list"""
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
        """Get all contacts in a contact list"""
        list_doc = self.contact_lists_collection.find_one({"name": list_name})
        if not list_doc:
            return []

        contacts = []
        for contact_id in list_doc['contact_ids']:
            contact_doc = self.contacts_collection.find_one({"_id": pymongo.ObjectId(contact_id)})
            if contact_doc:
                contact_doc.pop('_id', None)
                contact_doc.pop('created_at', None)
                contacts.append(Contact(**contact_doc))

        return contacts

    # Template Management
    def save_template(self, template: EmailTemplate) -> str:
        """Save an email template"""
        try:
            template_dict = asdict(template)
            result = self.templates_collection.insert_one(template_dict)
            logger.info(f"Template saved: {template.name}")
            return str(result.inserted_id)
        except pymongo.errors.DuplicateKeyError:
            raise ValueError(f"Template with name '{template.name}' already exists")

    def get_template(self, name: str) -> Optional[EmailTemplate]:
        """Retrieve a template by name"""
        template_doc = self.templates_collection.find_one({"name": name})
        if template_doc:
            template_doc.pop('_id', None)
            return EmailTemplate(**template_doc)
        return None

    def list_templates(self) -> List[str]:
        """List all template names"""
        templates = self.templates_collection.find({}, {"name": 1})
        return [template['name'] for template in templates]

    def delete_template(self, name: str) -> bool:
        """Delete a template"""
        result = self.templates_collection.delete_one({"name": name})
        if result.deleted_count > 0:
            logger.info(f"Template deleted: {name}")
            return True
        return False

    # Email Personalization
    def personalize_email(self, template_content: str, contact: Contact) -> str:
        """
        Personalize email content with contact information

        Supports placeholders like {{first_name}}, {{last_name}}, {{email}}, {{company}}
        and custom fields like {{custom.field_name}}
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
        """Send a single email"""
        if not self.smtp_config['server']:
            raise ValueError("SMTP configuration not set. Use configure_smtp() first.")

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_config['username']
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

            # Create SMTP session
            server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])

            if self.smtp_config['use_tls']:
                context = ssl.create_default_context()
                server.starttls(context=context)

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
        """Log email send attempt"""
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
        """Create a new email campaign"""
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
        template_doc = self.templates_collection.find_one({"_id": pymongo.ObjectId(campaign_doc['template_id'])})
        if not template_doc:
            raise ValueError(f"Template not found for campaign: {campaign_name}")

        template_doc.pop('_id', None)
        template = EmailTemplate(**template_doc)

        # Get all contacts from contact lists
        all_contacts = []
        for list_id in campaign_doc['contact_list_ids']:
            list_doc = self.contact_lists_collection.find_one({"_id": pymongo.ObjectId(list_id)})
            if list_doc:
                for contact_id in list_doc['contact_ids']:
                    contact_doc = self.contacts_collection.find_one({"_id": pymongo.ObjectId(contact_id)})
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
        """Get campaign statistics"""
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
        """List all campaign names"""
        campaigns = self.campaigns_collection.find({}, {"name": 1})
        return [campaign['name'] for campaign in campaigns]

    # Utility Methods
    def get_email_logs(self, limit: int = 100, status_filter: str = None) -> List[Dict]:
        """Get email sending logs"""
        query = {}
        if status_filter:
            query['status'] = status_filter

        logs = self.email_logs_collection.find(query).sort("timestamp", -1).limit(limit)
        return list(logs)

    def cleanup_old_logs(self, days_old: int = 30):
        """Remove email logs older than specified days"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)
        result = self.email_logs_collection.delete_many({"timestamp": {"$lt": cutoff_date}})
        logger.info(f"Cleaned up {result.deleted_count} old email logs")

    def export_contacts(self, output_file: str, contact_list_name: str = None):
        """Export contacts to CSV file"""
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
        """Close database connection"""
        self.client.close()
        logger.info("Database connection closed")


# Example Usage and CLI Interface
def main():
    """Example usage of the Email Campaign Manager"""

    # Initialize the manager
    manager = EmailCampaignManager()

    # Configure SMTP (example with Gmail)
    # manager.configure_smtp(
    #     server="smtp.gmail.com",
    #     port=587,
    #     username="your_email@gmail.com",
    #     password="your_app_password",
    #     use_tls=True
    # )

    try:
        # Example: Add contacts
        contact1 = Contact(
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
            company="Example Corp",
            custom_fields={"department": "Marketing", "city": "New York"}
        )

        contact2 = Contact(
            email="jane.smith@example.com",
            first_name="Jane",
            last_name="Smith",
            company="Tech Solutions",
            custom_fields={"department": "Sales", "city": "Los Angeles"}
        )

        # Add contacts (handle duplicates)
        try:
            manager.add_contact(contact1)
            manager.add_contact(contact2)
        except ValueError as e:
            print(f"Contact may already exist: {e}")

        # Create a contact list
        try:
            list_id = manager.create_contact_list("Newsletter Subscribers", "Main newsletter list")
        except ValueError:
            print("Contact list may already exist")

        # Add contacts to list
        manager.add_contacts_to_list("Newsletter Subscribers", ["john.doe@example.com", "jane.smith@example.com"])

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
            # Create campaign
            list_doc = manager.contact_lists_collection.find_one({"name": "Newsletter Subscribers"})
            list_id = str(list_doc['_id']) if list_doc else None

            if list_id:
                campaign = Campaign(
                    name="Welcome Campaign 2024",
                    template_id=template_id,
                    contact_list_ids=[list_id]
                )

                try:
                    campaign_id = manager.create_campaign(campaign)
                    print(f"Campaign created with ID: {campaign_id}")

                    # Send campaign (uncomment when SMTP is configured)
                    # stats = manager.send_campaign("Welcome Campaign 2024")
                    # print(f"Campaign sent: {stats}")

                except ValueError as e:
                    print(f"Campaign may already exist: {e}")

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