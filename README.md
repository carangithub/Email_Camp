# Email Campaign Manager

A comprehensive Python application for managing email campaigns with MongoDB integration and SMTP delivery. This tool provides a complete solution for organizing contacts, creating email templates, managing contact lists, and executing email campaigns with personalization features.

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
- Campaign status tracking (draft, sent)

### Email Personalization
- Dynamic content replacement using placeholders:
  - `{{first_name}}`, `{{last_name}}`, `{{email}}`, `{{company}}`
  - `{{full_name}}` (automatic combination)
  - `{{custom.field_name}}` for custom fields

### Email Delivery
- SMTP integration with TLS support
- Attachment support
- Bounce and failure tracking
- Comprehensive email logging

### Analytics and Logging
- Email delivery logs with timestamps
- Campaign success/failure statistics
- Log cleanup utilities
- Detailed error reporting

## Requirements

- Python 3.7+
- MongoDB server
- Required Python packages:
  ```
  pymongo
  pandas
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Email_Camp
   ```

2. Install required dependencies:
   ```bash
   pip install pymongo pandas
   ```

3. Ensure MongoDB is running on your system

## Configuration

### MongoDB Setup
The application connects to MongoDB using the default connection string `mongodb://localhost:27017/`. You can customize this during initialization:

```python
manager = EmailCampaignManager(
    mongodb_uri="mongodb://your-mongodb-uri",
    db_name="your_database_name"
)
```

### SMTP Configuration
Configure your email provider settings:

```python
manager.configure_smtp(
    server="smtp.gmail.com",  # Your SMTP server
    port=587,                 # SMTP port
    username="your_email@gmail.com",  # Your email
    password="your_app_password",     # App password
    use_tls=True             # Enable TLS
)
```

**Note:** For Gmail, you'll need to use an App Password instead of your regular password.

## Quick Start

```python
from mail import EmailCampaignManager, Contact, EmailTemplate, Campaign

# Initialize the manager
manager = EmailCampaignManager()

# Configure SMTP
manager.configure_smtp(
    server="smtp.gmail.com",
    port=587,
    username="your_email@gmail.com",
    password="your_app_password"
)

# Add a contact
contact = Contact(
    email="john.doe@example.com",
    first_name="John",
    last_name="Doe",
    company="Example Corp",
    custom_fields={"department": "Marketing"}
)
manager.add_contact(contact)

# Create a contact list
list_id = manager.create_contact_list("Newsletter", "Main newsletter subscribers")
manager.add_contacts_to_list("Newsletter", ["john.doe@example.com"])

# Create an email template
template = EmailTemplate(
    name="Welcome Email",
    subject="Welcome {{first_name}}!",
    body="Hello {{first_name}}, welcome to our newsletter!"
)
template_id = manager.save_template(template)

# Create and send campaign
campaign = Campaign(
    name="Welcome Campaign",
    template_id=template_id,
    contact_list_ids=[list_id]
)
campaign_id = manager.create_campaign(campaign)
stats = manager.send_campaign("Welcome Campaign")

print(f"Campaign results: {stats}")
```

## Database Schema

The application creates the following MongoDB collections:

- **contacts**: Contact information and custom fields
- **templates**: Email templates with content
- **campaigns**: Campaign definitions and statistics  
- **contact_lists**: Contact list definitions and memberships
- **email_logs**: Email delivery logs and status

## API Reference

### Core Classes

#### EmailCampaignManager
Main class for managing email campaigns.

#### Contact
Data class representing a contact:
- `email`: Contact email address (required)
- `first_name`: First name
- `last_name`: Last name  
- `company`: Company name
- `custom_fields`: Dictionary of custom fields

#### EmailTemplate  
Data class for email templates:
- `name`: Template name (unique)
- `subject`: Email subject line
- `body`: Plain text email body
- `html_body`: HTML email body (optional)

#### Campaign
Data class for campaigns:
- `name`: Campaign name (unique)
- `template_id`: ID of the email template to use
- `contact_list_ids`: List of contact list IDs to target

### Key Methods

#### Contact Management
- `add_contact(contact)`: Add new contact
- `get_contact(email)`: Retrieve contact by email
- `update_contact(email, updates)`: Update contact information
- `delete_contact(email)`: Remove contact
- `import_contacts_from_csv(file_path, mapping)`: Import contacts from CSV

#### Template Management  
- `save_template(template)`: Save email template
- `get_template(name)`: Retrieve template by name
- `list_templates()`: List all template names
- `delete_template(name)`: Remove template

#### Campaign Management
- `create_campaign(campaign)`: Create new campaign
- `send_campaign(name, attachments)`: Execute campaign
- `get_campaign_stats(name)`: Get campaign statistics
- `list_campaigns()`: List all campaigns

#### List Management
- `create_contact_list(name, description)`: Create contact list
- `add_contacts_to_list(list_name, emails)`: Add contacts to list
- `get_contact_list_contacts(list_name)`: Get list contacts

## Email Personalization

Use these placeholders in your email templates:

- `{{first_name}}` - Contact's first name
- `{{last_name}}` - Contact's last name
- `{{full_name}}` - Full name (first + last)
- `{{email}}` - Contact's email address
- `{{company}}` - Contact's company
- `{{custom.field_name}}` - Custom field values

Example:
```
Subject: Welcome {{first_name}}!

Hello {{first_name}} {{last_name}},

Thank you for joining us at {{company}}.
Your department is: {{custom.department}}

Best regards,
The Team
```

## Error Handling

The application includes comprehensive error handling:

- Email validation before adding contacts
- Duplicate prevention for contacts, templates, and campaigns
- SMTP connection error handling
- Detailed logging for troubleshooting
- Graceful failure handling during campaign execution

## Logging

The application uses Python's logging module with INFO level by default. Logs include:

- Contact operations (add, update, delete)
- Template operations  
- Campaign creation and execution
- Email sending success/failure
- Database operations

## Security Considerations

- Store SMTP credentials securely
- Use app passwords for Gmail
- Validate email addresses before sending
- Monitor email logs for suspicious activity
- Regularly clean up old logs

## Performance Tips

- Use indexes on email fields (automatically created)
- Clean up old email logs regularly using `cleanup_old_logs()`
- Consider batch operations for large contact imports
- Monitor MongoDB performance with large datasets

## Troubleshooting

### Common Issues

**SMTP Authentication Failed**
- Verify SMTP credentials
- Enable "Less secure apps" or use App Passwords for Gmail
- Check firewall settings

**MongoDB Connection Error**  
- Ensure MongoDB service is running
- Verify connection string format
- Check network connectivity

**Email Not Delivered**
- Check email logs using `get_email_logs()`
- Verify recipient email addresses
- Review SMTP server response codes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review email logs for error details
3. Create an issue in the repository with detailed information