#!/usr/bin/env python
"""
Auto migration script for Railway deployment
This script runs migrations automatically on startup
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def run_migrations():
    """Run Django migrations automatically"""
    print("🔄 Running automatic migrations...")
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baza_pracownikow.settings')
    django.setup()
    
    try:
        # Run migrations
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        print("✅ Migrations completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = run_migrations()
    if not success:
        sys.exit(1)
    print("🚀 Starting Django server...")
