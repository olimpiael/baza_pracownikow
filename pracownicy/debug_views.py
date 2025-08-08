"""
Debug view for Railway 500 errors
Place this in pracownicy/debug_views.py
"""
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import traceback
import sys


def debug_models(request):
    """Test whether models can be imported"""
    try:
        from .models import Pracownik, Zadanie, OcenaPracownika
        
        # Test database connection
        pracownik_count = Pracownik.objects.count()
        zadanie_count = Zadanie.objects.count()
        ocena_count = OcenaPracownika.objects.count()
        
        return JsonResponse({
            'status': 'OK',
            'models_imported': True,
            'database_connection': True,
            'counts': {
                'pracownicy': pracownik_count,
                'zadania': zadanie_count,
                'oceny': ocena_count
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'ERROR',
            'error': str(e),
            'traceback': traceback.format_exc()
        })


def debug_templates(request):
    """Test whether templates exist"""
    try:
        from django.template.loader import get_template
        
        templates_to_test = [
            'pracownicy/zadania.html',
            'pracownicy/oceny.html',
            'pracownicy/ocen_pracownika.html'
        ]
        
        results = {}
        for template_name in templates_to_test:
            try:
                get_template(template_name)
                results[template_name] = 'OK'
            except Exception as e:
                results[template_name] = f'ERROR: {str(e)}'
        
        return JsonResponse({
            'status': 'OK',
            'templates': results
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'ERROR',
            'error': str(e),
            'traceback': traceback.format_exc()
        })


def debug_views(request):
    """Test whether views can be imported"""
    try:
        from . import views
        
        # Check if specific functions exist
        functions_to_check = ['zadania_view', 'oceny_pracownikow', 'ocen_pracownika']
        results = {}
        
        for func_name in functions_to_check:
            if hasattr(views, func_name):
                results[func_name] = 'EXISTS'
            else:
                results[func_name] = 'MISSING'
        
        return JsonResponse({
            'status': 'OK',
            'views': results,
            'python_version': sys.version,
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'ERROR',
            'error': str(e),
            'traceback': traceback.format_exc()
        })


def debug_migrations(request):
    """Check migrations status"""
    try:
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connection
        
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        return JsonResponse({
            'status': 'OK',
            'unapplied_migrations': len(plan),
            'migrations_needed': [str(migration) for migration, backwards in plan],
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'ERROR',
            'error': str(e),
            'traceback': traceback.format_exc()
        })


def debug_all(request):
    """Combined debug information"""
    debug_info = {}
    
    # Test models
    try:
        from .models import Pracownik, Zadanie, OcenaPracownika
        debug_info['models'] = 'OK - All imported'
        debug_info['model_counts'] = {
            'pracownicy': Pracownik.objects.count(),
            'zadania': Zadanie.objects.count(), 
            'oceny': OcenaPracownika.objects.count()
        }
    except Exception as e:
        debug_info['models'] = f'ERROR: {str(e)}'
    
    # Test views
    try:
        from . import views
        debug_info['views'] = 'OK - Views imported'
    except Exception as e:
        debug_info['views'] = f'ERROR: {str(e)}'
    
    # Test database
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        debug_info['database'] = 'OK - Connection working'
    except Exception as e:
        debug_info['database'] = f'ERROR: {str(e)}'
    
    return JsonResponse({
        'status': 'DEBUG_INFO',
        'debug': debug_info,
        'python_version': sys.version,
    })
