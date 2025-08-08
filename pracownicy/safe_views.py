"""
Safe fallback views for Railway deployment
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import traceback


@login_required
def safe_oceny_view(request):
    """Safe fallback view for oceny system"""
    try:
        # Import here to catch import errors
        from .models import Pracownik, OcenaPracownika
        
        # Get current user's employee record
        pracownik = Pracownik.objects.get(user=request.user)
        
        # Simple context
        context = {
            'pracownik': pracownik,
            'do_oceny': Pracownik.objects.exclude(id=pracownik.id)[:5],  # Limit to 5
            'otrzymane_oceny': [],
            'wystawione_oceny': [],
            'oceny_count': 0,
        }
        
        return render(request, 'pracownicy/safe_oceny.html', context)
        
    except Exception as e:
        return HttpResponse(f"""
        <h1>Błąd systemu ocen</h1>
        <p>Wystąpił błąd: {str(e)}</p>
        <p>Traceback: <pre>{traceback.format_exc()}</pre></p>
        <a href="/">Powrót do strony głównej</a>
        """)


@login_required 
def safe_zadania_view(request):
    """Safe fallback view for zadania system"""
    try:
        # Import here to catch import errors
        from .models import Pracownik, Zadanie
        
        # Get current user's employee record
        pracownik = Pracownik.objects.get(user=request.user)
        
        # Simple context
        context = {
            'pracownik': pracownik,
            'zadania_todo': [],
            'zadania_progress': [],
            'zadania_done': [],
            'wszyscy_pracownicy': Pracownik.objects.all(),
        }
        
        return render(request, 'pracownicy/safe_zadania.html', context)
        
    except Exception as e:
        return HttpResponse(f"""
        <h1>Błąd systemu zadań</h1>
        <p>Wystąpił błąd: {str(e)}</p>
        <p>Traceback: <pre>{traceback.format_exc()}</pre></p>
        <a href="/">Powrót do strony głównej</a>
        """)
