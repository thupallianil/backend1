from django.core.management.base import BaseCommand
import subprocess
import sys
import os

class Command(BaseCommand):
    help = "Seeds database with multi-tenant default roles, businesses, subscriptions, and accounts for production."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding for deployment..."))
        seed_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "seed_full_multitenant_data.py")
        if os.path.exists(seed_script):
            res = subprocess.run([sys.executable, seed_script], capture_output=True, text=True)
            self.stdout.write(res.stdout)
            if res.stderr:
                self.stderr.write(res.stderr)
            self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
        else:
            self.stderr.write(f"Seed script not found at {seed_script}")
