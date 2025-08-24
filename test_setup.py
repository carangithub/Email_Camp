#!/usr/bin/env python3
"""
Test script for Email Campaign Manager setup verification
"""

from mail import EmailCampaignManager, Contact, EmailTemplate, Campaign
import os

def test_setup():
    """Test the email campaign manager setup"""
    
    print("=" * 60)
    print("EMAIL CAMPAIGN MANAGER - SETUP TEST")
    print("=" * 60)
    
    # Initialize manager
    print("\n1. Initializing Email Campaign Manager...")
    manager = EmailCampaignManager()
    print(f"[OK] Connected to MongoDB successfully")
    
    # Test environment configuration
    print("\n2. Testing Environment Configuration...")
    print(f"   SMTP Server: {manager.smtp_config['server']}")
    print(f"   SMTP Port: {manager.smtp_config['port']}")
    print(f"   SMTP Username: {manager.smtp_config['username']}")
    print(f"   From Email: {manager.from_email}")
    print(f"   From Name: {manager.from_name}")
    
    # Test receiver emails from env
    print("\n3. Testing Receiver Email Configuration...")
    receiver_emails = manager.get_receiver_emails_from_env()
    print(f"   Receiver emails from .env: {receiver_emails}")
    
    if not receiver_emails:
        print("   [!]  No receiver emails configured in .env file")
        print("   [TIP] Add emails to RECEIVER_EMAILS in .env file")
    else:
        print(f"   [OK] Found {len(receiver_emails)} valid receiver email(s)")
    
    # Test basic operations
    print("\n4. Testing Basic Operations...")
    
    # Test email validation
    test_email = "test@example.com"
    is_valid = manager.validate_email(test_email)
    print(f"   Email validation for '{test_email}': {'[OK] Valid' if is_valid else '[X] Invalid'}")
    
    # Test collections
    print("\n5. Testing Database Collections...")
    collections = ['contacts', 'templates', 'campaigns', 'contact_lists', 'email_logs']
    for collection_name in collections:
        collection = getattr(manager, f"{collection_name}_collection")
        count = collection.count_documents({})
        print(f"   {collection_name}: {count} documents")
    
    # Test environment variables
    print("\n6. Environment Variables Status...")
    env_vars = {
        'MONGODB_URI': os.getenv('MONGODB_URI', 'Not set'),
        'MONGODB_DATABASE': os.getenv('MONGODB_DATABASE', 'Not set'),
        'SMTP_SERVER': os.getenv('SMTP_SERVER', 'Not set'),
        'SMTP_USERNAME': os.getenv('SMTP_USERNAME', 'Not set'),
        'FROM_EMAIL': os.getenv('FROM_EMAIL', 'Not set'),
        'FROM_NAME': os.getenv('FROM_NAME', 'Not set'),
        'RECEIVER_EMAILS': os.getenv('RECEIVER_EMAILS', 'Not set'),
        'DEFAULT_CONTACT_LIST_NAME': os.getenv('DEFAULT_CONTACT_LIST_NAME', 'Not set'),
    }
    
    for var_name, value in env_vars.items():
        status = "[OK] Set" if value != "Not set" else "[X] Not set"
        print(f"   {var_name}: {status}")
    
    # Clean up
    manager.close()
    
    print("\n" + "=" * 60)
    print("SETUP TEST COMPLETED")
    print("=" * 60)
    print("\n[TIP] To send emails:")
    print("   1. Ensure SMTP credentials are correct in .env")
    print("   2. Add recipient emails to RECEIVER_EMAILS in .env")
    print("   3. Run: python mail.py")
    print("\n[EMAIL] Current receiver emails:", receiver_emails if receiver_emails else "None configured")

if __name__ == "__main__":
    try:
        test_setup()
    except Exception as e:
        print(f"[X] Test failed with error: {e}")
        import traceback
        traceback.print_exc()