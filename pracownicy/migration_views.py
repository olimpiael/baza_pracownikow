"""
Force migration script for Railway
Visit this URL to force run migrations: /force-migrate/
"""
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
import os
import subprocess
import traceback


@staff_member_required  # Only admin can run this
def force_migrate(request):
    """Force run migrations via web interface"""
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'migrate', '--noinput'], 
            capture_output=True, 
            text=True,
            timeout=60
        )
        
        output = f"""
        <h1>🔄 Force Migration Results</h1>
        <h2>Command: python manage.py migrate --noinput</h2>
        <h3>Return Code: {result.returncode}</h3>
        
        <h3>STDOUT:</h3>
        <pre>{result.stdout}</pre>
        
        <h3>STDERR:</h3>
        <pre>{result.stderr}</pre>
        
        <hr>
        <a href="/debug/all/">Check Debug Info</a> | 
        <a href="/oceny/">Test Oceny</a> | 
        <a href="/zadania/">Test Zadania</a>
        """
        
        return HttpResponse(output)
        
    except subprocess.TimeoutExpired:
        return HttpResponse("<h1>❌ Migration timed out after 60 seconds</h1>")
    except Exception as e:
        return HttpResponse(f"""
        <h1>❌ Migration failed</h1>
        <p>Error: {str(e)}</p>
        <pre>{traceback.format_exc()}</pre>
        """)


def migration_status(request):
    """Check current migration status"""
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'showmigrations'], 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        output = f"""
        <h1>📋 Migration Status</h1>
        <h2>Command: python manage.py showmigrations</h2>
        <h3>Return Code: {result.returncode}</h3>
        
        <pre>{result.stdout}</pre>
        
        {f'<h3>Errors:</h3><pre>{result.stderr}</pre>' if result.stderr else ''}
        
        <hr>
        <a href="/force-migrate/">Force Run Migrations</a> | 
        <a href="/debug/all/">Debug Info</a>
        """
        
        return HttpResponse(output)
        
    except Exception as e:
        return HttpResponse(f"<h1>Error checking migrations: {str(e)}</h1>")
