#!/usr/bin/env python
"""
Railway migration script - FIXED VERSION
Run this to apply migrations manually if automatic doesn't work
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'baza_pracownikow.settings')
    django.setup()
    
    print("=== Railway Manual Migration Script - FIXED ===")
    print("🔄 Applying migrations...")
    
    try:
        # Run migrations with --noinput flag
        print("Running: python manage.py migrate --noinput")
        execute_from_command_line(['manage.py', 'migrate', '--noinput'])
        print("✅ Migrations completed successfully!")
        
        # Test if OcenaPracownika table exists
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name='pracownicy_ocenapracownika'")
        result = cursor.fetchone()
        
        if result:
            print("✅ Table 'pracownicy_ocenapracownika' exists!")
        else:
            print("❌ Table 'pracownicy_ocenapracownika' still doesn't exist!")
            # Show what tables do exist
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%pracownicy%'")
            tables = cursor.fetchall()
            print("Available tables:", [table[0] for table in tables])
            
        # List applied migrations to verify
        print("\n🔍 Checking migration status...")
        execute_from_command_line(['manage.py', 'showmigrations', 'pracownicy'])
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't exit with error, let the app start anyway
        print("⚠️ Continuing despite migration error...")
        pass
