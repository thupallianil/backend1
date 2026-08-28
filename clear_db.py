import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from api.models import (
    BusinessProfile,
    AppSettings,
    Client,
    Vendor,
    Quote,
    QuoteItem,
    Invoice,
    InvoiceItem,
    Payment,
    Receipt,
    Ticket,
    TicketMessage,
    Notification,
    SignupVerificationOTP,
    PasswordResetOTP,
)

def clear_all_data():
    print("Clearing all test accounts, OTP records, and related data...")
    
    # Delete in order of dependencies
    TicketMessage.objects.all().delete()
    Ticket.objects.all().delete()
    Receipt.objects.all().delete()
    Payment.objects.all().delete()
    InvoiceItem.objects.all().delete()
    Invoice.objects.all().delete()
    QuoteItem.objects.all().delete()
    Quote.objects.all().delete()
    Vendor.objects.all().delete()
    Client.objects.all().delete()
    Notification.objects.all().delete()
    SignupVerificationOTP.objects.all().delete()
    PasswordResetOTP.objects.all().delete()
    AppSettings.objects.all().delete()
    BusinessProfile.objects.all().delete()
    
    # Delete all users
    user_count = User.objects.count()
    User.objects.all().delete()
    
    print(f"Successfully deleted {user_count} users and all associated records.")
    print("Database is now 100% clean and ready for fresh end-to-end testing!")

if __name__ == "__main__":
    clear_all_data()
