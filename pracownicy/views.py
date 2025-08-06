from urllib import request
from django.utils import timezone
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse, HttpRequest, HttpResponse, FileResponse
from django.contrib import messages
from requests import Response
from rest_framework import permissions, viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.serializers import ModelSerializer
from django_filters.rest_framework import DjangoFilterBackend
import json
import io
from datetime import datetime, date
from typing import Dict, List, Any
from django.db.models import Count, Q
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
from .models import Pracownik, Zespol, Stanowisko, Rola, DzienPracy
from .serializers import CVUploadSerializer, PracownikSerializer, ZespolSerializer
from .validators import validate_pesel


def validate_field_value(field_name, field_value):
    """
    Waliduje wartość pola przed zapisem
    Zwraca (is_valid, error_message)
    """
    if field_name == 'pesel':
        if field_value:
            try:
                validate_pesel(field_value)
                return True, None
            except Exception as e:
                return False, str(e)
    
    elif field_name == 'imie' or field_name == 'nazwisko':
        if not field_value or len(field_value.strip()) < 2:
            return False, f"{field_name.capitalize()} musi mieć co najmniej 2 znaki"
        if not field_value.replace(' ', '').replace('-', '').isalpha():
            return False, f"{field_name.capitalize()} może zawierać tylko litery"
    
    elif field_name == 'data_urodzenia':
        try:
            from datetime import datetime
            date_obj = datetime.strptime(field_value, '%Y-%m-%d').date()
            if date_obj > datetime.now().date():
                return False, "Data urodzenia nie może być w przyszłości"
        except ValueError:
            return False, "Nieprawidłowy format daty"
    
    elif field_name == 'zarobki':
        if field_value:
            try:
                from decimal import Decimal
                zarobki_val = Decimal(str(field_value))
                if zarobki_val < 0:
                    return False, "Zarobki nie mogą być ujemne"
                if zarobki_val > 999999.99:
                    return False, "Zarobki nie mogą przekraczać 999,999.99 PLN"
                return True, None
            except (ValueError, TypeError):
                return False, "Nieprawidłowa kwota zarobków"
        # Puste pole zarobki jest dozwolone
        return True, None
    
    elif field_name == 'ocena':
        if field_value:
            try:
                ocena_val = int(field_value)
                if ocena_val < 1 or ocena_val > 5:
                    return False, "Ocena musi być w zakresie 1-5"
                return True, None
            except (ValueError, TypeError):
                return False, "Nieprawidłowa ocena"
        # Puste pole oceny jest dozwolone
        return True, None
    
    elif field_name == 'data_ostatniej_oceny':
        if field_value:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(field_value, '%Y-%m-%d').date()
                if date_obj > datetime.now().date():
                    return False, "Data oceny nie może być w przyszłości"
                return True, None
            except ValueError:
                return False, "Nieprawidłowy format daty"
        return True, None
    
    return True, None

try:
    from mqtt import start_mqtt
    start_mqtt()
except Exception as e:
    print(f"MQTT nie uruchomiony: {e}")


def check_edit_permissions(user, target_pracownik_id, field_name):
    """Sprawdza uprawnienia do edycji pola"""
    try:
        current_pracownik = Pracownik.objects.get(user=user)
        target_pracownik = Pracownik.objects.get(id=target_pracownik_id)
 
        # Uprawnienia do edycji według ról
        EDITABLE_FIELDS = {
            'admin': ['id','imie', 'nazwisko','stanowisko', 'pesel', 'rola', 'zespol', 'przelozony', 'dzial', 'zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny', 'data_zatrudnienia', 'data_urodzenia'],
            'hr': ['imie', 'nazwisko', 'pesel', 'stanowisko', 'rola', 'zespol', 'przelozony', 'dzial', 'zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny', 'data_zatrudnienia', 'data_urodzenia'],
            'ceo': ['rola', 'przelozony', 'zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny'],
            'przelozony_dzialu': ['imie', 'nazwisko', 'stanowisko', 'rola', 'zespol', 'przelozony', 'dzial'],
            'kierownik': ['imie', 'nazwisko', 'zespol'],
            'marketing_spec': ['imie', 'nazwisko'],
            'sales_rep': ['imie', 'nazwisko'],
            'accountant': ['imie', 'nazwisko'],
            'support': ['imie', 'nazwisko'],
            'intern': ['imie', 'nazwisko'],
            'pracownik': ['imie', 'nazwisko'],
        }
        
        # Czy rola może edytować to pole?
        if field_name not in EDITABLE_FIELDS.get(current_pracownik.rola, []):
            return False
        
        # Admin ma pełne uprawnienia
        if current_pracownik.rola == 'admin':
            return True
            
        # CEO ma ograniczenia - nie może edytować admina, HR ani siebie
        if current_pracownik.rola == 'ceo':
            # CEO nie może edytować admina ani HR
            if target_pracownik.rola in ['admin', 'hr']:
                return False
            # CEO nie może zmieniać swojej własnej roli
            if target_pracownik.id == current_pracownik.id and field_name == 'rola':
                return False
            return True
            
        # HR też może wszystko (poza adminami) ale ma ograniczenia dla siebie
        if current_pracownik.rola == 'hr' and target_pracownik.rola != 'admin':
            # HR nie może zmieniać swojej własnej roli, zespołu ani stanowiska
            if (target_pracownik.id == current_pracownik.id and 
                field_name in ['rola', 'zespol', 'stanowisko']):
                return False
            return True
            
        # Sprawdź uprawnienia hierarchiczne
        if current_pracownik.can_manage_hierarchical(target_pracownik):
            return True
            
            
    except Pracownik.DoesNotExist:
        return False
    
    return False


def check_add_permissions(user):
    """Sprawdza uprawnienia do dodawania pracowników"""
    try:
        current_pracownik = Pracownik.objects.get(user=user)
        return current_pracownik.can_manage_employees()
    except Pracownik.DoesNotExist:
        return False


def check_delete_permissions(user, target_pracownik_id):
    """Sprawdza uprawnienia do usuwania pracowników"""
    try:
        current_pracownik = Pracownik.objects.get(user=user)
        target_pracownik = Pracownik.objects.get(id=target_pracownik_id)
        
        # Tylko admin i HR mogą usuwać
        if not current_pracownik.can_manage_employees():
            return False
            
        # Admin nie może usunąć siebie
        if current_pracownik.rola == 'admin' and target_pracownik.id == current_pracownik.id:
            return False
            
        # HR nie może usunąć admina
        if current_pracownik.rola == 'hr' and target_pracownik.rola == 'admin':
            return False
            
        return True
    except Pracownik.DoesNotExist:
        return False


def validate_field_value(field_name, field_value):
    """Waliduje wartości pól"""
    field_value = field_value.strip()
    
    if field_name == 'id':
        # ID musi być liczbą dodatnią
        try:
            id_value = int(field_value)
            if id_value <= 0:
                return False, "ID musi być liczbą dodatnią"
            return True, None
        except ValueError:
            return False, "ID musi być liczbą całkowitą"
    
    elif field_name in ['imie', 'nazwisko']:
        if len(field_value) < 2:
            return False, "Imię i nazwisko muszą mieć co najmniej 2 znaki"
        if len(field_value) > 30:
            return False, "Imię i nazwisko nie mogą mieć więcej niż 30 znaków"
        if not field_value.replace(' ', '').replace('-', '').isalpha():
            return False, "Imię i nazwisko mogą zawierać tylko litery, spacje i myślniki"
    
    elif field_name == 'pesel':
        if len(field_value) != 11 or not field_value.isdigit():
            return False, "PESEL musi składać się z dokładnie 11 cyfr"
    
    elif field_name in ['data_zatrudnienia', 'data_urodzenia']:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(field_value, '%Y-%m-%d').date()
            
            if field_name == 'data_zatrudnienia':
                # Data zatrudnienia nie może być w przyszłości
                if date_obj > timezone.now().date():
                    return False, "Data zatrudnienia nie może być w przyszłości"
                if date_obj.year < 1900:
                    return False, "Data zatrudnienia nie może być wcześniejsza niż 1900 rok"
            
            elif field_name == 'data_urodzenia':
            # Data urodzenia nie może być w przyszłości
                if date_obj > timezone.now().date():
                    return False, "Data urodzenia nie może być w przyszłości"
        except ValueError:
            return False, "Nieprawidłowy format daty (wymagany: YYYY-MM-DD)"
    
    return True, None


@login_required(login_url='/accounts/login/')
@csrf_exempt
def lista_pracownikow(request: HttpRequest) -> HttpResponse:
    try:
        pracownik = Pracownik.objects.get(user=request.user)
        
        # Obsługa edycji (POST request)
        if request.method == 'POST' and request.POST.get('action') == 'save':
            pracownik_id = request.POST.get('pracownik_id')
            field_name = request.POST.get('field_name')
            field_value = request.POST.get('field_value')
            
            if check_edit_permissions(request.user, pracownik_id, field_name):
                try:
                    target_pracownik = Pracownik.objects.get(id=pracownik_id)
                    
                    is_valid, error_message = validate_field_value(field_name, field_value)
                    if not is_valid:
                        messages.error(request, error_message)
                    else:
                        # Zmiana ID
                        if field_name == 'id':
                            new_id = int(field_value.strip())
                            # Sprawdź czy ID nie jest zajęte
                            if Pracownik.objects.filter(id=new_id).exclude(id=pracownik_id).exists():
                                messages.error(request, f"ID {new_id} jest już zajęte przez innego pracownika")
                            else:
                                old_id = target_pracownik.id
                                target_pracownik.id = new_id
                                target_pracownik.save()
                                messages.success(request, f"Pomyślnie zmieniono ID z {old_id} na {new_id}")
                        
                        # Walidacja PESEL
                        elif field_name == 'pesel':
                            existing = Pracownik.objects.filter(pesel=field_value.strip()).exclude(id=pracownik_id)
                            if existing.exists():
                                messages.error(request, "Pracownik z tym PESEL już istnieje")
                            else:
                                setattr(target_pracownik, field_name, field_value.strip())
                                target_pracownik.save()
                                messages.success(request, f"Pomyślnie zaktualizowano {field_name}")
                        else:
                            # Pola specjalne
                            if field_name == 'zespol':
                                # Sprawdź zespół
                                valid_teams = [choice[0] for choice in Pracownik.TEAM_CHOICES] + ['']
                                if field_value not in valid_teams:
                                    messages.error(request, "Nieprawidłowy zespół")
                                    return redirect(request.path)
                                else:
                                    target_pracownik.zespol = field_value if field_value else None
                            elif field_name == 'rola':
                                # Sprawdź rolę
                                valid_roles = [choice[0] for choice in Pracownik.ROLE_CHOICES]
                                if field_value not in valid_roles:
                                    messages.error(request, "Nieprawidłowa rola")
                                    return redirect(request.path)
                                else:
                                    target_pracownik.rola = field_value
                            elif field_name == 'stanowisko':
                                # Sprawdź stanowisko
                                valid_positions = [choice[0] for choice in Pracownik.STANOWISKO_CHOICES]
                                if field_value not in valid_positions:
                                    messages.error(request, "Nieprawidłowe stanowisko")
                                    return redirect(request.path)
                                else:
                                    target_pracownik.stanowisko = field_value
                            elif field_name == 'przelozony':
                                # Sprawdź przełożonego
                                if field_value == '':
                                    target_pracownik.przelozony = None
                                else:
                                    try:
                                        przelozony = Pracownik.objects.get(id=int(field_value))
                                        # Sprawdzanie czy pracownik nie jest swoim własnym przełożonym
                                        if przelozony.id == target_pracownik.id:
                                            messages.error(request, "Pracownik nie może być swoim przełożonym")
                                            return redirect(request.path)
                                        target_pracownik.przelozony = przelozony
                                    except (Pracownik.DoesNotExist, ValueError):
                                        messages.error(request, "Nieprawidłowy przełożony")
                                        return redirect(request.path)
                            else:
                                setattr(target_pracownik, field_name, field_value.strip())
                            
                            # Zapis zmian
                            target_pracownik.save()
                            messages.success(request, f"Pomyslnie zaktualizowano {field_name}")

                        # Zachowaj sortowanie w URL
                        redirect_url = request.path
                        params = []
                        if request.GET.get('sort'):
                            params.append(f"sort={request.GET.get('sort')}")
                        if request.GET.get('order'):
                            params.append(f"order={request.GET.get('order')}")
                        if params:
                            redirect_url += '?' + '&'.join(params)
                        return redirect(redirect_url)
                        
                except Pracownik.DoesNotExist:
                    messages.error(request, "Pracownik nie istnieje")
            else:
                messages.error(request, "Brak uprawnień do edycji tego pola")
        
        # Obsługa dodawania pracownika
        elif request.method == 'POST' and request.POST.get('action') == 'add':
            if check_add_permissions(request.user):
                try:
                    # Pobierz dane z formularza
                    imie = request.POST.get('imie', '').strip()
                    nazwisko = request.POST.get('nazwisko', '').strip()
                    pesel = request.POST.get('pesel', '').strip()
                    stanowisko = request.POST.get('stanowisko', '').strip()
                    rola = request.POST.get('rola', '').strip()
                    zespol = request.POST.get('zespol', '').strip()
                    przelozony_id = request.POST.get('przelozony', '').strip()
                    dzial = request.POST.get('dzial', '').strip()
                    data_zatrudnienia = request.POST.get('data_zatrudnienia', '').strip()
                    data_urodzenia = request.POST.get('data_urodzenia', '').strip()
                    
                    # Walidacja podstawowych pól
                    if not all([imie, nazwisko, pesel, stanowisko, rola, data_zatrudnienia, data_urodzenia]):
                        messages.error(request, "Wszystkie pola (oprócz zespołu, przełożonego i działu) są wymagane")
                        return redirect(request.path)
                    
                    # Walidacja PESEL
                    if len(pesel) != 11 or not pesel.isdigit():
                        messages.error(request, "PESEL musi składać się z dokładnie 11 cyfr")
                        return redirect(request.path)
                    
                    if Pracownik.objects.filter(pesel=pesel).exists():
                        messages.error(request, f"Pracownik z PESEL {pesel} już istnieje")
                        return redirect(request.path)
                    
                    # Walidacja dat
                    try:
                        data_zatrudnienia_obj = datetime.strptime(data_zatrudnienia, '%Y-%m-%d').date()
                        data_urodzenia_obj = datetime.strptime(data_urodzenia, '%Y-%m-%d').date()
                        
                        if data_zatrudnienia_obj > timezone.now().date():
                            messages.error(request, "Data zatrudnienia nie może być w przyszłości")
                            return redirect(request.path)
                        if data_urodzenia_obj > timezone.now().date():
                            messages.error(request, "Data urodzenia nie może być w przyszłości")
                            return redirect(request.path)
                    except ValueError:
                        messages.error(request, "Nieprawidłowy format daty")
                        return redirect(request.path)
                    
                    # Sprawdź czy rola jest prawidłowa
                    valid_roles = [choice[0] for choice in Pracownik.ROLE_CHOICES]
                    if rola not in valid_roles:
                        messages.error(request, "Nieprawidłowa rola")
                        return redirect(request.path)
                    
                    # Sprawdź czy stanowisko jest prawidłowe
                    valid_positions = [choice[0] for choice in Pracownik.STANOWISKO_CHOICES]
                    if stanowisko not in valid_positions:
                        messages.error(request, "Nieprawidłowe stanowisko")
                        return redirect(request.path)
                    
                    # Przygotuj dane do utworzenia pracownika
                    new_pracownik_data = {
                        'imie': imie,
                        'nazwisko': nazwisko,
                        'pesel': pesel,
                        'stanowisko': stanowisko,
                        'rola': rola,
                        'dzial': dzial if dzial else None,
                        'data_zatrudnienia': data_zatrudnienia_obj,
                        'data_urodzenia': data_urodzenia_obj,
                        'data_utworzenia': timezone.now(),
                        'data_modyfikacji': timezone.now(),
                    }
                    
                    # Obsługa zespołu
                    if zespol:
                        valid_teams = [choice[0] for choice in Pracownik.TEAM_CHOICES]
                        if zespol in valid_teams:
                            new_pracownik_data['zespol'] = zespol
                        else:
                            messages.error(request, "Nieprawidłowy zespół")
                            return redirect(request.path)
                    
                    # Obsługa przełożonego
                    if przelozony_id:
                        try:
                            przelozony = Pracownik.objects.get(id=int(przelozony_id))
                            new_pracownik_data['przelozony'] = przelozony
                        except (Pracownik.DoesNotExist, ValueError):
                            messages.error(request, "Nieprawidłowy przełożony")
                            return redirect(request.path)
                    
                    # Utwórz pracownika
                    new_pracownik = Pracownik.objects.create(**new_pracownik_data)
                    messages.success(request, f"Pomyślnie dodano pracownika: {new_pracownik.imie} {new_pracownik.nazwisko}")
                    
                except Exception as e:
                    messages.error(request, f"Błąd podczas dodawania pracownika: {str(e)}")
            else:
                messages.error(request, "Brak uprawnień do dodawania pracowników")
        
        # Obsługa usuwania pracownika
        elif request.method == 'POST' and request.POST.get('action') == 'delete':
            pracownik_id = request.POST.get('pracownik_id')
            if check_delete_permissions(request.user, pracownik_id):
                try:
                    target_pracownik = Pracownik.objects.get(id=pracownik_id)
                    imie = target_pracownik.imie
                    nazwisko = target_pracownik.nazwisko
                    target_pracownik.delete()
                    messages.success(request, f"Pomyślnie usunięto pracownika: {imie} {nazwisko}")
                except Pracownik.DoesNotExist:
                    messages.error(request, "Pracownik nie istnieje")
            else:
                messages.error(request, "Brak uprawnień do usuwania tego pracownika")
        
        # Obsługa dodawania stanowiska
        elif request.method == 'POST' and request.POST.get('action') == 'add_stanowisko':
            if pracownik.rola in ['admin', 'hr']:
                try:
                    nazwa_stanowiska = request.POST.get('nazwa_stanowiska', '').strip()
                    
                    if not nazwa_stanowiska:
                        messages.error(request, "Nazwa stanowiska jest wymagana")
                    elif Stanowisko.objects.filter(nazwa=nazwa_stanowiska).exists():
                        messages.error(request, f"Stanowisko '{nazwa_stanowiska}' już istnieje")
                    else:
                        # Generuj kod z nazwy
                        import re
                        kod_stanowiska = re.sub(r'[^a-zA-Z0-9]', '_', nazwa_stanowiska.lower())
                        if Stanowisko.objects.filter(kod=kod_stanowiska).exists():
                            kod_stanowiska = f"{kod_stanowiska}_{Stanowisko.objects.count() + 1}"
                        
                        Stanowisko.objects.create(
                            nazwa=nazwa_stanowiska,
                            kod=kod_stanowiska
                        )
                        messages.success(request, f"Pomyślnie dodano stanowisko: {nazwa_stanowiska}")
                except Exception as e:
                    messages.error(request, f"Błąd podczas dodawania stanowiska: {str(e)}")
            else:
                messages.error(request, "Brak uprawnień do dodawania stanowisk")
        
        # Obsługa dodawania roli
        elif request.method == 'POST' and request.POST.get('action') == 'add_rola':
            if pracownik.rola in ['admin']:  # Tylko admin może dodawać role
                try:
                    nazwa_roli = request.POST.get('nazwa_roli', '').strip()
                    kod_roli = request.POST.get('kod_roli', '').strip()
                    poziom_uprawnien = request.POST.get('poziom_uprawnien', '6')
                    opis_roli = request.POST.get('opis_roli', '').strip()
                    
                    if not nazwa_roli or not kod_roli:
                        messages.error(request, "Nazwa i kod roli są wymagane")
                    elif Rola.objects.filter(nazwa=nazwa_roli).exists():
                        messages.error(request, f"Rola '{nazwa_roli}' już istnieje")
                    elif Rola.objects.filter(kod=kod_roli).exists():
                        messages.error(request, f"Kod roli '{kod_roli}' już istnieje")
                    else:
                        try:
                            poziom = int(poziom_uprawnien)
                            if poziom < 0 or poziom > 7:
                                raise ValueError("Poziom musi być między 0 a 7")
                        except ValueError:
                            messages.error(request, "Nieprawidłowy poziom uprawnień (0-7)")
                            return redirect(request.path)
                        
                        Rola.objects.create(
                            nazwa=nazwa_roli,
                            kod=kod_roli,
                            poziom_uprawnien=poziom,
                            opis=opis_roli if opis_roli else None
                        )
                        messages.success(request, f"Pomyślnie dodano rolę: {nazwa_roli} (poziom {poziom})")
                except Exception as e:
                    messages.error(request, f"Błąd podczas dodawania roli: {str(e)}")
            else:
                messages.error(request, "Brak uprawnień do dodawania ról")
        
        # Obsługa dodawania zespołu
        elif request.method == 'POST' and request.POST.get('action') == 'add_zespol':
            if pracownik.rola in ['admin', 'hr', 'ceo']:
                try:
                    nazwa_zespolu = request.POST.get('nazwa_zespolu', '').strip()
                    kod_zespolu = request.POST.get('kod_zespolu', '').strip()
                    opis_zespolu = request.POST.get('opis_zespolu', '').strip()
                    
                    if not nazwa_zespolu or not kod_zespolu:
                        messages.error(request, "Nazwa i kod zespołu są wymagane")
                    elif Zespol.objects.filter(nazwa=nazwa_zespolu).exists():
                        messages.error(request, f"Zespół '{nazwa_zespolu}' już istnieje")
                    elif Zespol.objects.filter(kod=kod_zespolu).exists():
                        messages.error(request, f"Kod zespołu '{kod_zespolu}' już istnieje")
                    else:
                        Zespol.objects.create(
                            nazwa=nazwa_zespolu,
                            kod=kod_zespolu,
                            opis=opis_zespolu if opis_zespolu else None
                        )
                        messages.success(request, f"Pomyślnie dodano zespół: {nazwa_zespolu}")
                except Exception as e:
                    messages.error(request, f"Błąd podczas dodawania zespołu: {str(e)}")
            else:
                messages.error(request, "Brak uprawnień do dodawania zespołów")
        
        # Tryb edycji
        edit_id = request.GET.get('edit_id')
        edit_field = request.GET.get('edit_field')
        can_edit = False
        
        if edit_id and edit_field:
            try:
                edit_id = int(edit_id)
                can_edit = check_edit_permissions(request.user, edit_id, edit_field)
            except (ValueError, TypeError):
                edit_id = None
                edit_field = None
        
        # Sortowanie
        sort_by = request.GET.get('sort', 'id')
        order = request.GET.get('order', 'asc')  
        
        allowed_sort_fields = ['id', 'imie', 'nazwisko', 'rola', 'stanowisko', 'dzial', 'zarobki', 'ocena', 'data_zatrudnienia', 'data_urodzenia']
        if sort_by not in allowed_sort_fields:
            sort_by = 'id'
            
        if order == 'desc':
            sort_by = f'-{sort_by}'
        
        # Filtrowanie według uprawnień hierarchicznych
        if pracownik.rola in ['admin', 'hr', 'ceo']:
            # Admin, HR, CEO widzą wszystkich
            pracownicy = Pracownik.objects.select_related('przelozony', 'user').all().order_by(sort_by)
        elif pracownik.rola == 'kierownik':
            # Kierownik widzi: siebie + swoich hierarchicznych podwładnych + swój zespół (fallback)
            subordinates = pracownik.get_all_subordinates()
            subordinate_ids = [sub.id for sub in subordinates]
            subordinate_ids.append(pracownik.id)  # Dodaj siebie
            
            # Fallback: jeśli nie ma hierarchicznych podwładnych, pokaż zespół
            if not subordinates and pracownik.zespol:
                team_members = Pracownik.objects.filter(zespol=pracownik.zespol)
                subordinate_ids.extend([member.id for member in team_members])
            
            pracownicy = Pracownik.objects.select_related('przelozony', 'user').filter(id__in=subordinate_ids).order_by(sort_by)
        else:
            # Inni widzą siebie + swoich podwładnych
            subordinates = pracownik.get_all_subordinates()
            subordinate_ids = [sub.id for sub in subordinates]
            subordinate_ids.append(pracownik.id)  # Dodaj siebie
            pracownicy = Pracownik.objects.select_related('przelozony', 'user').filter(id__in=subordinate_ids).order_by(sort_by)
        
        # Lista edytowalnych pól
        EDITABLE_FIELDS_MAP = {
            'admin': ['id','imie', 'nazwisko', 'pesel', 'stanowisko', 'rola', 'zespol', 'przelozony', 'dzial', 'zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny', 'data_zatrudnienia', 'data_urodzenia'],
            'hr': ['imie', 'nazwisko', 'pesel','stanowisko','rola', 'zespol', 'przelozony', 'dzial', 'zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny', 'data_zatrudnienia', 'data_urodzenia'],
            'ceo': ['stanowisko', 'rola', 'przelozony', 'zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny'],
            'kierownik': ['imie', 'nazwisko','stanowisko', 'zespol'],
            'przelozony_dzialu': ['imie', 'nazwisko', 'stanowisko', 'rola', 'zespol', 'przelozony', 'dzial'],
            'marketing_spec': ['imie', 'nazwisko'],
            'sales_rep': ['imie', 'nazwisko'],
            'accountant': ['imie', 'nazwisko'],
            'support': ['imie', 'nazwisko'],
            'intern': ['imie', 'nazwisko'],
            'pracownik': ['imie', 'nazwisko'],
        }
        user_editable_fields = EDITABLE_FIELDS_MAP.get(pracownik.rola, [])
        
        # Przygotowanie list wyboru dla select fields
        # Używamy danych z bazy plus stałe choices z modelu dla kompatybilności
        team_choices = list(Pracownik.TEAM_CHOICES)
        role_choices = list(Pracownik.ROLE_CHOICES)
        stanowisko_choices = list(Pracownik.STANOWISKO_CHOICES)
        
        # Dodaj nowe zespoły z bazy danych
        db_teams = Zespol.objects.all().order_by('nazwa')
        for team in db_teams:
            if (team.kod, team.nazwa) not in team_choices:
                team_choices.append((team.kod, team.nazwa))
        
        # Dodaj nowe role z bazy danych
        db_roles = Rola.objects.all().order_by('poziom_uprawnien', 'nazwa')
        for role in db_roles:
            if (role.kod, role.nazwa) not in role_choices:
                role_choices.append((role.kod, role.nazwa))
        
        # Dodaj nowe stanowiska z bazy danych
        db_stanowiska = Stanowisko.objects.all().order_by('nazwa')
        for stanowisko in db_stanowiska:
            if (stanowisko.kod, stanowisko.nazwa) not in stanowisko_choices:
                stanowisko_choices.append((stanowisko.kod, stanowisko.nazwa))
        
        # Dodaj nowe obiekty dla dostępu w template
        all_role_objects = list(db_roles)
        all_team_objects = list(db_teams)
        all_stanowisko_objects = list(db_stanowiska)
        
        # Sprawdź uprawnienia do dodawania i usuwania
        can_add_employees = check_add_permissions(request.user)
        can_delete_employees = pracownik.can_manage_employees()
        
        # Lista wszystkich pracowników dla listy przełożonych
        all_pracownicy = Pracownik.objects.select_related('przelozony', 'user').all().order_by('nazwisko', 'imie')
        
        # Przygotuj listę ID pracowników, których można usunąć
        deletable_employee_ids = []
        if can_delete_employees:
            for p in pracownicy:
                if check_delete_permissions(request.user, p.id):
                    deletable_employee_ids.append(p.id)
            
        context = {
            'pracownicy': pracownicy,
            'pracownicy_count': pracownicy.count(),
            'current_user': pracownik,
            'user_role': pracownik.get_rola_display(),
            'current_sort': request.GET.get('sort', 'id'),
            'current_order': request.GET.get('order', 'asc'),
            'edit_id': edit_id,
            'edit_field': edit_field,
            'can_edit': can_edit,
            'user_editable_fields': user_editable_fields,
            'team_choices': team_choices,
            'role_choices': role_choices,
            'stanowisko_choices': stanowisko_choices,
            'can_add_employees': can_add_employees,
            'can_delete_employees': can_delete_employees,
            'deletable_employee_ids': deletable_employee_ids,
            'all_pracownicy': all_pracownicy,
            'all_role_objects': all_role_objects,
            'all_team_objects': all_team_objects,
            'all_stanowisko_objects': all_stanowisko_objects,
        }
        return render(request, 'pracownicy/lista.html', context)
        
    except Pracownik.DoesNotExist:
        # Jeśli użytkownik nie ma powiązanego pracownika, przekieruj
        return render(request, 'pracownicy/no_access.html', {'message': 'Brak dostępu - nie jesteś powiązany z żadnym pracownikiem'})


class ZespolViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows zespoly to be viewed or edited.
    """
    queryset = Zespol.objects.all().order_by('nazwa')
    serializer_class = ZespolSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['nazwa', 'lokalizacja']
    ordering_fields = ['nazwa', 'lokalizacja']
    ordering = ['nazwa']
    search_fields = ['nazwa', 'lokalizacja']

class PracownikViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows pracownicy to be viewed or edited.
    """
    queryset = Pracownik.objects.all().order_by('-data_utworzenia')
    serializer_class = PracownikSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['rola', 'zespol', 'stanowisko']
    ordering_fields = ['imie', 'nazwisko', 'data_zatrudnienia', 'data_urodzenia', 'stanowisko', 'rola']
    ordering = ['-data_utworzenia']
    search_fields = ['imie', 'nazwisko', 'pesel', 'stanowisko']

    def perform_create(self, serializer: ModelSerializer) -> None:
        serializer.save(data_utworzenia=timezone.now(), data_modyfikacji=timezone.now())

@login_required(login_url='/accounts/login/')
@csrf_exempt
def api_pracownicy(request: HttpRequest) -> JsonResponse:
    try:
        # Pobierz pracownika związanego z zalogowanym użytkownikiem
        current_pracownik = Pracownik.objects.get(user=request.user)
    except Pracownik.DoesNotExist:
        return JsonResponse({'error': 'Brak dostępu - nie jesteś powiązany z żadnym pracownikiem'}, status=403)
    
    if request.method == 'GET':
        # Pobierz parametry sortowania z request
        sort_by = request.GET.get('sort', 'id')
        order = request.GET.get('order', 'asc')
        
        # Sprawdź czy pole sortowania jest dozwolone
        allowed_sort_fields = ['id', 'imie', 'nazwisko', 'stanowisko', 'rola', 'dzial', 'zarobki', 'ocena', 'data_zatrudnienia', 'data_urodzenia']
        if sort_by not in allowed_sort_fields:
            sort_by = 'id'
            
        # Dodaj prefix dla sortowania malejącego
        if order == 'desc':
            sort_by = f'-{sort_by}'
            
        if current_pracownik.can_view_all_employees():
            # Admin, pani Anetka, CEO - widzą wszystkich
            pracownicy = Pracownik.objects.all().order_by(sort_by)
        elif current_pracownik.is_kierownik():
            # Kierownik - widzi tylko swój zespół
            if current_pracownik.zespol:
                pracownicy = Pracownik.objects.filter(zespol=current_pracownik.zespol).order_by(sort_by)
            else:
                pracownicy = Pracownik.objects.filter(id=current_pracownik.id).order_by(sort_by)
        else:
            # Pracownik - widzi tylko siebie
            pracownicy = Pracownik.objects.filter(id=current_pracownik.id).order_by(sort_by)
            
        data: List[Dict[str, Any]] = []
        for p in pracownicy:
            data.append({
                'id': p.id,
                'imie': p.imie,
                'nazwisko': p.nazwisko,
                'pesel': p.pesel,
                'stanowisko': p.stanowisko,
                'rola': p.get_rola_display(),
                'zespol': p.zespol.nazwa if p.zespol else None,
                'data_zatrudnienia': p.data_zatrudnienia.strftime('%Y-%m-%d'),
                'data_urodzenia': p.data_urodzenia.strftime('%Y-%m-%d'),
            })
        return JsonResponse({'pracownicy': data})

    elif request.method == 'POST':
        # Tylko admin i HR mogą dodawać pracowników
        if not current_pracownik.can_manage_employees():
            return JsonResponse({'error': 'Brak uprawnień do dodawania pracowników'}, status=403)
            
        try:
            dane: Dict[str, Any] = json.loads(request.body)

            if Pracownik.objects.filter(pesel=dane['pesel']).exists():
                return JsonResponse({'error': f'PESEL {dane["pesel"]} już istnieje'}, status=400)

            pracownik: Pracownik = Pracownik.objects.create(
                imie=dane['imie'],
                nazwisko=dane['nazwisko'],
                pesel=dane['pesel'],
                stanowisko=dane['stanowisko'],
                data_zatrudnienia=datetime.strptime(dane['data_zatrudnienia'], '%Y-%m-%d').date(),
                data_urodzenia=datetime.strptime(dane['data_urodzenia'], '%Y-%m-%d').date()
            )
            return JsonResponse({'message': f'Dodano pracownika: {pracownik.imie} {pracownik.nazwisko}'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    elif request.method == 'DELETE':
        # Tylko admin i HR mogą usuwać pracowników
        if not current_pracownik.can_manage_employees():
            return JsonResponse({'error': 'Brak uprawnień do usuwania pracowników'}, status=403)
            
        try:
            dane: Dict[str, Any] = json.loads(request.body)
            pracownik = Pracownik.objects.get(pesel=dane['pesel'])
            pracownik.delete()
            return JsonResponse({'message': f'Usunięto pracownika: {pracownik.imie} {pracownik.nazwisko}'})
        except Pracownik.DoesNotExist:
            return JsonResponse({'error': 'Pracownik o podanym PESEL nie istnieje'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    elif request.method == 'PUT':
        # Aktualizacja pracownika
        try:
            dane: Dict[str, Any] = json.loads(request.body)
            pracownik = Pracownik.objects.get(pesel=dane['pesel'])
            
            # Sprawdź uprawnienia do edycji
            if current_pracownik.can_manage_employees():
                # Admin i HR mogą edytować wszystkich
                pass
            elif current_pracownik.id == pracownik.id:
                to_update = dane.get('to_update', {})
                allowed_fields = ['imie', 'nazwisko']  # Pracownik może zmienić tylko imię i nazwisko
                to_update = {k: v for k, v in to_update.items() if k in allowed_fields}
                dane['to_update'] = to_update
            else:
                return JsonResponse({'error': 'Brak uprawnień do edycji tego pracownika'}, status=403)
            
            to_update: Dict[str, Any] = dane.get('to_update', {})

            if 'Imie' in to_update:
                pracownik.imie = to_update['Imie']
            if 'Nazwisko' in to_update:
                pracownik.nazwisko = to_update['Nazwisko']
            if 'Stanowisko' in to_update and current_pracownik.can_manage_employees():
                pracownik.stanowisko = to_update['Stanowisko']
            pracownik.save()
            
            return JsonResponse({'message': f'Zaktualizowano pracownika: {pracownik.imie} {pracownik.nazwisko}'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Nieprawidłowa metoda'}, status=405)


@login_required
def dashboard_page(request):
    """Strona dashboard ze statystykami"""
    try:
        pracownik = Pracownik.objects.get(user=request.user)
        
        # Przygotuj kontekst podobny do lista_pracownikow
        context = {
            'current_user': pracownik,
            'user_role': pracownik.get_rola_display() if pracownik.rola else 'Brak roli'
        }
        
        return render(request, 'pracownicy/dashboard.html', context)
        
    except Pracownik.DoesNotExist:
        messages.error(request, 'Brak dostępu - nie znaleziono profilu pracownika')
        return redirect('/accounts/login/')


@login_required
def dashboard_stats(request):
    """Zwraca statystyki w czasie rzeczywistym dla dashboard"""
    try:
        # Sprawdź czy użytkownik ma dostęp do statystyk
        pracownik = Pracownik.objects.get(user=request.user)
        
        # Statystyki zespołów
        zespoly_stats = (Pracownik.objects
                        .values('zespol')
                        .annotate(count=Count('id'))
                        .order_by('-count'))
        
        # Zamień kody zespołów na nazwy
        zespoly_data = []
        for stat in zespoly_stats:
            zespol_kod = stat['zespol']
            if zespol_kod:
                # Znajdź wyświetlaną nazwę zespołu
                zespol_nazwa = None
                for choice in Pracownik.TEAM_CHOICES:
                    if choice[0] == zespol_kod:
                        zespol_nazwa = choice[1]
                        break
                zespoly_data.append({
                    'name': zespol_nazwa or zespol_kod,
                    'count': stat['count']
                })
            else:
                zespoly_data.append({
                    'name': 'Brak zespołu',
                    'count': stat['count']
                })
        
        # Statystyki ról
        role_stats = (Pracownik.objects
                     .values('rola')
                     .annotate(count=Count('id'))
                     .order_by('-count'))
        
        role_data = []
        for stat in role_stats:
            rola_kod = stat['rola']
            if rola_kod:
                # Znajdź wyświetlaną nazwę roli
                rola_nazwa = None
                for choice in Pracownik.ROLE_CHOICES:
                    if choice[0] == rola_kod:
                        rola_nazwa = choice[1]
                        break
                role_data.append({
                    'name': rola_nazwa or rola_kod,
                    'count': stat['count']
                })
        
        # Średni wiek pracowników
        today = date.today()
        pracownicy_z_data_urodzenia = Pracownik.objects.filter(data_urodzenia__isnull=False)
        
        ages = []
        for p in pracownicy_z_data_urodzenia:
            age = today.year - p.data_urodzenia.year
            if today.month < p.data_urodzenia.month or (today.month == p.data_urodzenia.month and today.day < p.data_urodzenia.day):
                age -= 1
            ages.append(age)
        
        sredni_wiek = sum(ages) / len(ages) if ages else 0
        
        # Statystyki stanowisk
        stanowiska_stats = (Pracownik.objects
                          .values('stanowisko')
                          .annotate(count=Count('id'))
                          .order_by('-count'))
        
        stanowiska_data = []
        for stat in stanowiska_stats:
            stanowisko_kod = stat['stanowisko']
            if stanowisko_kod:
                # Znajdź wyświetlaną nazwę stanowiska
                stanowisko_nazwa = None
                for choice in Pracownik.STANOWISKO_CHOICES:
                    if choice[0] == stanowisko_kod:
                        stanowisko_nazwa = choice[1]
                        break
                stanowiska_data.append({
                    'name': stanowisko_nazwa or stanowisko_kod,
                    'count': stat['count']
                })
        
        # Ogólne statystyki
        total_pracownicy = Pracownik.objects.count()
        pracownicy_z_przelozonym = Pracownik.objects.filter(przelozony__isnull=False).count()
        
        # Statystyki wynagrodzeń
        from django.db.models import Avg, Sum, Max, Min
        pracownicy_z_zarobkami = Pracownik.objects.filter(zarobki__isnull=False)
        
        if pracownicy_z_zarobkami.exists():
            zarobki_stats = pracownicy_z_zarobkami.aggregate(
                srednie_zarobki=Avg('zarobki'),
                suma_zarobkow=Sum('zarobki'),
                max_zarobki=Max('zarobki'),
                min_zarobki=Min('zarobki')
            )
            
            # Statystyki wynagrodzeń według stanowisk
            zarobki_stanowiska = (pracownicy_z_zarobkami
                                .values('stanowisko')
                                .annotate(
                                    srednie=Avg('zarobki'),
                                    liczba=Count('id')
                                )
                                .order_by('-srednie'))
            
            zarobki_stanowiska_data = []
            for stat in zarobki_stanowiska:
                stanowisko_kod = stat['stanowisko']
                if stanowisko_kod:
                    # Znajdź wyświetlaną nazwę stanowiska
                    stanowisko_nazwa = None
                    for choice in Pracownik.STANOWISKO_CHOICES:
                        if choice[0] == stanowisko_kod:
                            stanowisko_nazwa = choice[1]
                            break
                    zarobki_stanowiska_data.append({
                        'name': stanowisko_nazwa or stanowisko_kod,
                        'average_salary': round(float(stat['srednie']), 2),
                        'count': stat['liczba']
                    })
        else:
            zarobki_stats = {
                'srednie_zarobki': 0,
                'suma_zarobkow': 0,
                'max_zarobki': 0,
                'min_zarobki': 0
            }
            zarobki_stanowiska_data = []
        
        # Statystyki ocen
        from datetime import timedelta
        pracownicy_z_ocenami = Pracownik.objects.filter(ocena__isnull=False)
        
        if pracownicy_z_ocenami.exists():
            oceny_stats = pracownicy_z_ocenami.aggregate(
                srednia_ocena=Avg('ocena'),
                liczba_ocenionych=Count('id')
            )
            
            # Rozkład ocen
            oceny_rozklad = (pracownicy_z_ocenami
                           .values('ocena')
                           .annotate(liczba=Count('id'))
                           .order_by('ocena'))
            
            oceny_rozklad_data = []
            for stat in oceny_rozklad:
                oceny_rozklad_data.append({
                    'rating': stat['ocena'],
                    'count': stat['liczba']
                })
            
            # Pracownicy wymagający oceny (bez oceny lub ocena starsza niż 12 miesięcy)
            one_year_ago = today - timedelta(days=365)
            wymagaja_oceny = Pracownik.objects.filter(
                Q(ocena__isnull=True) | Q(data_ostatniej_oceny__lt=one_year_ago)
            ).count()
            
        else:
            oceny_stats = {
                'srednia_ocena': 0,
                'liczba_ocenionych': 0
            }
            oceny_rozklad_data = []
            wymagaja_oceny = Pracownik.objects.count()
        
        stats = {
            'zespoly': zespoly_data,
            'role': role_data,
            'stanowiska': stanowiska_data,
            'sredni_wiek': round(sredni_wiek, 1),
            'total_pracownicy': total_pracownicy,
            'pracownicy_z_przelozonym': pracownicy_z_przelozonym,
            'zarobki': {
                'srednie': round(float(zarobki_stats['srednie_zarobki']) if zarobki_stats['srednie_zarobki'] else 0, 2),
                'suma': round(float(zarobki_stats['suma_zarobkow']) if zarobki_stats['suma_zarobkow'] else 0, 2),
                'max': round(float(zarobki_stats['max_zarobki']) if zarobki_stats['max_zarobki'] else 0, 2),
                'min': round(float(zarobki_stats['min_zarobki']) if zarobki_stats['min_zarobki'] else 0, 2),
                'stanowiska': zarobki_stanowiska_data
            },
            'oceny': {
                'srednia': round(float(oceny_stats['srednia_ocena']) if oceny_stats['srednia_ocena'] else 0, 2),
                'liczba_ocenionych': oceny_stats['liczba_ocenionych'],
                'rozklad': oceny_rozklad_data,
                'wymagaja_oceny': wymagaja_oceny
            },
            'ostatnia_aktualizacja': timezone.now().strftime('%H:%M:%S')
        }
        
        return JsonResponse(stats)
        
    except Pracownik.DoesNotExist:
        return JsonResponse({'error': 'Brak dostępu'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def generate_pdf_report(request):
    """Generuje raport PDF z danymi pracowników"""
    try:
        pracownik = Pracownik.objects.get(user=request.user)
        
        # Sprawdź uprawnienia - tylko admin i HR mogą generować raporty
        if pracownik.rola not in ['admin', 'hr']:
            return JsonResponse({'error': 'Brak uprawnień do generowania raportów'}, status=403)
        
        # Utwórz bufor w pamięci dla PDF
        buffer = io.BytesIO()
        
        # Utwórz dokument PDF z obsługą polskich znaków
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Używamy standardowego fontu Helvetica
        font_name = 'Helvetica'
        
        # Style z obsługą polskich znaków
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center
            fontName=font_name,
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=font_name,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_name,
        )
        
        # Tytuł raportu
        title = Paragraph("Raport Pracowników", title_style)
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Data generowania
        date_para = Paragraph(f"Wygenerowano: {timezone.now().strftime('%d.%m.%Y %H:%M')}", normal_style)
        story.append(date_para)
        story.append(Spacer(1, 12))
        
        # Pobierz dane pracowników
        if pracownik.rola == 'admin':
            pracownicy = Pracownik.objects.all()
        else:
            # HR widzi wszystkich
            pracownicy = Pracownik.objects.all()
        
        # Statystyki ogólne
        stats_para = Paragraph("Statystyki ogólne", heading_style)
        story.append(stats_para)
        
        total_count = pracownicy.count()
        stats_text = f"Łączna liczba pracowników: {total_count}"
        story.append(Paragraph(stats_text, normal_style))
        story.append(Spacer(1, 12))
        
        # Statystyki zespołów
        zespoly_stats = pracownicy.values('zespol').annotate(count=Count('id')).order_by('-count')
        if zespoly_stats:
            teams_para = Paragraph("Rozkład zespołów:", heading_style)
            story.append(teams_para)
            
            for stat in zespoly_stats:
                zespol_kod = stat['zespol']
                zespol_nazwa = 'Brak zespołu'
                if zespol_kod:
                    for choice in Pracownik.TEAM_CHOICES:
                        if choice[0] == zespol_kod:
                            zespol_nazwa = choice[1]
                            break
                team_text = f"• {zespol_nazwa}: {stat['count']} pracowników"
                story.append(Paragraph(team_text, normal_style))
            story.append(Spacer(1, 12))
        
        # Tabela pracowników
        table_para = Paragraph("Lista pracowników", heading_style)
        story.append(table_para)
        story.append(Spacer(1, 12))
        
        # Nagłówki tabeli
        data = [['ID', 'Imię', 'Nazwisko', 'Stanowisko', 'Rola', 'Zespół']]
        
        # Dodaj dane pracowników
        for p in pracownicy.order_by('nazwisko', 'imie'):
            zespol_display = 'Brak'
            if p.zespol:
                for choice in Pracownik.TEAM_CHOICES:
                    if choice[0] == p.zespol:
                        zespol_display = choice[1]
                        break
            
            rola_display = p.get_rola_display() if p.rola else 'Brak'
            stanowisko_display = p.get_stanowisko_display() if p.stanowisko else 'Brak'
            
            data.append([
                str(p.id),
                p.imie or 'Brak',
                p.nazwisko or 'Brak',
                stanowisko_display,
                rola_display,
                zespol_display
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name + '-Bold' if font_name == 'DejaVuSans' else 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        
        # Zbuduj PDF
        doc.build(story)
        buffer.seek(0)
        
        # Zwróć odpowiedź z PDF
        response = FileResponse(
            buffer,
            as_attachment=True,
            filename=f'raport_pracownikow_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf',
            content_type='application/pdf'
        )
        
        return response
        
    except Pracownik.DoesNotExist:
        return JsonResponse({'error': 'Brak dostępu'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def custom_logout(request):
    logout(request)
    return render(request, 'registration/logged_out.html')

class UploadCVView(APIView):
    serializer_class = CVUploadSerializer
    
    def post(self, request):
        request.Pracownik = Pracownik.objects.first()
        serializer = self.serializer_class(request.Pracownik, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'CV uploaded successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def upload_documents(request, pracownik_id):
    """Widok do wgrywania dokumentów dla pracownika"""
    try:
        pracownik = Pracownik.objects.get(id=pracownik_id)
        
        # Bezpieczne pobranie current_user_pracownik
        try:
            current_user_pracownik = Pracownik.objects.get(user=request.user)
        except Pracownik.DoesNotExist:
            # Jeśli user nie ma powiązanego pracownika, sprawdź czy to superuser
            if request.user.is_superuser:
                # Dla superusera pozwól na dostęp
                current_user_pracownik = None
            else:
                messages.error(request, 'Brak dostępu - nie jesteś zarejestrowanym pracownikiem.')
                return redirect('lista_pracownikow')
        
        # Sprawdź uprawnienia
        if current_user_pracownik is None:  # superuser
            can_access = request.user.is_superuser
        else:
            can_access = (current_user_pracownik.rola in ['admin', 'hr', 'ceo'] or 
                         current_user_pracownik.id == pracownik.id or
                         (current_user_pracownik.rola == 'kierownik' and 
                          current_user_pracownik.zespol == pracownik.zespol))
        
        if not can_access:
            messages.error(request, 'Brak uprawnień do zarządzania dokumentami tego pracownika.')
            return redirect('lista_pracownikow')
        
        if request.method == 'POST':
            # Obsługa wgrywania plików
            updated = False
            
            if 'cv' in request.FILES:
                pracownik.cv = request.FILES['cv']
                updated = True
                
            if 'umowa_pracy' in request.FILES:
                pracownik.umowa_pracy = request.FILES['umowa_pracy']
                updated = True
                
            if 'swiadectwo_pracy' in request.FILES:
                pracownik.swiadectwo_pracy = request.FILES['swiadectwo_pracy']
                updated = True
                
            if 'dyplom' in request.FILES:
                pracownik.dyplom = request.FILES['dyplom']
                updated = True
                
            if 'zdjecie' in request.FILES:
                pracownik.zdjecie = request.FILES['zdjecie']
                updated = True
                
            if 'inne_dokumenty' in request.FILES:
                pracownik.inne_dokumenty = request.FILES['inne_dokumenty']
                updated = True
            
            if updated:
                pracownik.save()
                messages.success(request, 'Dokumenty zostały pomyślnie wgrane.')
            else:
                messages.warning(request, 'Nie wybrano żadnych plików do wgrania.')
                
            return redirect('upload_documents', pracownik_id=pracownik.id)
        
        context = {
            'pracownik': pracownik,
            'current_user_pracownik': current_user_pracownik,
            'is_superuser': request.user.is_superuser,
            'user': request.user,
        }
        return render(request, 'pracownicy/upload_documents.html', context)
        
    except Pracownik.DoesNotExist:
        messages.error(request, 'Pracownik nie został znaleziony.')
        return redirect('lista_pracownikow')
    except Exception as e:
        # Logowanie błędu dla debugowania
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Błąd w upload_documents: {str(e)}", exc_info=True)
        messages.error(request, f'Wystąpił błąd: {str(e)}')
        return redirect('lista_pracownikow')


@login_required
def download_document(request, pracownik_id, document_type):
    """Widok do pobierania dokumentów pracownika"""
    try:
        pracownik = Pracownik.objects.get(id=pracownik_id)
        
        # Bezpieczne pobranie current_user_pracownik
        try:
            current_user_pracownik = Pracownik.objects.get(user=request.user)
        except Pracownik.DoesNotExist:
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Brak dostępu - nie jesteś zarejestrowanym pracownikiem'}, status=403)
            current_user_pracownik = None
        
        # Sprawdź uprawnienia
        if current_user_pracownik is None:  # superuser
            can_access = request.user.is_superuser
        else:
            can_access = (current_user_pracownik.rola in ['admin', 'hr', 'ceo'] or 
                         current_user_pracownik.id == pracownik.id or
                         (current_user_pracownik.rola == 'kierownik' and 
                          current_user_pracownik.zespol == pracownik.zespol))
        
        if not can_access:
            return JsonResponse({'error': 'Brak uprawnień'}, status=403)
        
        # Wybierz odpowiedni dokument
        document_field = getattr(pracownik, document_type, None)
        
        if not document_field or not document_field.name:
            return JsonResponse({'error': 'Dokument nie istnieje'}, status=404)
        
        # Zwróć plik
        response = FileResponse(
            document_field.open('rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{document_field.name.split("/")[-1]}"'
        return response
        
    except Pracownik.DoesNotExist:
        return JsonResponse({'error': 'Pracownik nie został znaleziony'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def delete_document(request, pracownik_id, document_type):
    """Widok do usuwania dokumentów pracownika"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Metoda nie dozwolona'}, status=405)
    
    try:
        pracownik = Pracownik.objects.get(id=pracownik_id)
        
        # Bezpieczne pobranie current_user_pracownik
        try:
            current_user_pracownik = Pracownik.objects.get(user=request.user)
        except Pracownik.DoesNotExist:
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Brak dostępu - nie jesteś zarejestrowanym pracownikiem'}, status=403)
            current_user_pracownik = None
        
        # Sprawdź uprawnienia (tylko admin, hr, ceo mogą usuwać dokumenty)
        if current_user_pracownik is None:  # superuser
            can_delete = request.user.is_superuser
        else:
            can_delete = current_user_pracownik.rola in ['admin', 'hr', 'ceo']
        
        if not can_delete:
            return JsonResponse({'error': 'Brak uprawnień do usuwania dokumentów'}, status=403)
        
        # Usuń dokument
        document_field = getattr(pracownik, document_type, None)
        
        if document_field and document_field.name:
            document_field.delete(save=False)
            setattr(pracownik, document_type, None)
            pracownik.save()
            return JsonResponse({'success': 'Dokument został usunięty'})
        else:
            return JsonResponse({'error': 'Dokument nie istnieje'}, status=404)
        
    except Pracownik.DoesNotExist:
        return JsonResponse({'error': 'Pracownik nie został znaleziony'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ================================
# SYSTEM OBECNOŚCI
# ================================

@login_required
def system_obecnosci(request):
    """Główny widok systemu obecności"""
    current_user = request.user
    
    try:
        current_pracownik = current_user.pracownik
    except:
        messages.error(request, "Nie jesteś przypisany do żadnego pracownika.")
        return redirect('lista_pracownikow')
    
    # Pobierz dzisiejsze wpisy obecności dla użytkownika
    from datetime import date, datetime, timedelta
    from .models import Obecnosc, DzienPracy
    
    dzisiaj = date.today()
    
    # Pobierz dzisiejsze wpisy obecności
    dzisiejsze_obecnosci = Obecnosc.objects.filter(
        pracownik=current_pracownik,
        data_czas__date=dzisiaj
    ).order_by('data_czas')
    
    # Sprawdź ostatni status
    ostatnia_obecnosc = dzisiejsze_obecnosci.last()
    aktualny_status = ostatnia_obecnosc.status if ostatnia_obecnosc else None
    
    # Pobierz lub utwórz dzień pracy
    dzien_pracy, created = DzienPracy.objects.get_or_create(
        pracownik=current_pracownik,
        data=dzisiaj
    )
    
    # Aktualizuj czasy pracy
    dzien_pracy.oblicz_czas_pracy()
    
    # Statystyki tygodniowe
    poczatek_tygodnia = dzisiaj - timedelta(days=dzisiaj.weekday())
    koniec_tygodnia = poczatek_tygodnia + timedelta(days=6)
    
    dni_pracy_tydzien = DzienPracy.objects.filter(
        pracownik=current_pracownik,
        data__range=[poczatek_tygodnia, koniec_tygodnia]
    )
    
    czas_pracy_tydzien = sum(
        [dp.czas_pracy_godziny for dp in dni_pracy_tydzien if dp.czas_pracy], 
        0.0
    )
    
    # Ostatnie 5 dni pracy
    ostatnie_dni = DzienPracy.objects.filter(
        pracownik=current_pracownik
    ).order_by('-data')[:5]
    
    context = {
        'current_pracownik': current_pracownik,
        'dzisiejsze_obecnosci': dzisiejsze_obecnosci,
        'aktualny_status': aktualny_status,
        'dzien_pracy': dzien_pracy,
        'czas_pracy_tydzien': czas_pracy_tydzien,
        'ostatnie_dni': ostatnie_dni,
        'dzisiaj': dzisiaj,
    }
    
    return render(request, 'pracownicy/system_obecnosci.html', context)


@login_required
def odbij_obecnosc(request):
    """Odbicie obecności przez pracownika"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Metoda POST wymagana'}, status=405)
    
    try:
        current_user = request.user
        current_pracownik = current_user.pracownik
        
        # Pobierz dane z formularza
        status = request.POST.get('status')
        lokalizacja = request.POST.get('lokalizacja', '')
        uwagi = request.POST.get('uwagi', '')
        
        # Sprawdź czy status jest prawidłowy
        valid_statuses = ['wejscie', 'wyjscie', 'przerwa_start', 'przerwa_koniec']
        if status not in valid_statuses:
            return JsonResponse({'error': 'Nieprawidłowy status'}, status=400)
        
        # Pobierz IP użytkownika
        def get_client_ip(request):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            return ip
        
        adres_ip = get_client_ip(request)
        
        # Sprawdź logikę odbicia
        from datetime import date
        from .models import Obecnosc
        
        dzisiaj = date.today()
        ostatnia_obecnosc = Obecnosc.objects.filter(
            pracownik=current_pracownik,
            data_czas__date=dzisiaj
        ).order_by('data_czas').last()
        
        # Walidacja sekwencji statusów
        if ostatnia_obecnosc:
            ostatni_status = ostatnia_obecnosc.status
            
            # Sprawdź czy sekwencja jest prawidłowa
            if status == 'wejscie' and ostatni_status in ['wejscie', 'przerwa_koniec']:
                return JsonResponse({
                    'error': 'Nie możesz odbić wejścia. Ostatni status: ' + ostatnia_obecnosc.get_status_display()
                }, status=400)
            
            if status == 'wyjscie' and ostatni_status in ['wyjscie', 'przerwa_start']:
                return JsonResponse({
                    'error': 'Nie możesz odbić wyjścia. Ostatni status: ' + ostatnia_obecnosc.get_status_display()
                }, status=400)
            
            if status == 'przerwa_start' and ostatni_status != 'wejscie':
                return JsonResponse({
                    'error': 'Możesz rozpocząć przerwę tylko po wejściu'
                }, status=400)
            
            if status == 'przerwa_koniec' and ostatni_status != 'przerwa_start':
                return JsonResponse({
                    'error': 'Możesz zakończyć przerwę tylko po jej rozpoczęciu'
                }, status=400)
        else:
            # Pierwszy wpis dnia - musi być wejście
            if status != 'wejscie':
                return JsonResponse({
                    'error': 'Pierwszy wpis dnia musi być wejściem'
                }, status=400)
        
        # Utwórz wpis obecności
        obecnosc = Obecnosc.objects.create(
            pracownik=current_pracownik,
            status=status,
            lokalizacja=lokalizacja,
            adres_ip=adres_ip,
            uwagi=uwagi
        )
        
        # Aktualizuj dzień pracy
        from .models import DzienPracy
        dzien_pracy, created = DzienPracy.objects.get_or_create(
            pracownik=current_pracownik,
            data=dzisiaj
        )
        dzien_pracy.oblicz_czas_pracy()
        
        return JsonResponse({
            'success': True,
            'message': f'Pomyślnie odbito: {obecnosc.get_status_display()}',
            'status': status,
            'czas': obecnosc.data_czas.strftime('%H:%M:%S'),
            'data': obecnosc.data_czas.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def raport_obecnosci(request):
    """Raport obecności dla kierowników i HR"""
    current_user = request.user
    
    try:
        current_pracownik = current_user.pracownik
    except:
        messages.error(request, "Nie jesteś przypisany do żadnego pracownika.")
        return redirect('lista_pracownikow')
    
    # Sprawdź uprawnienia
    if not (current_pracownik.rola == 'admin' or 
            (hasattr(current_pracownik, 'rola') and 
             hasattr(current_pracownik.rola, 'poziom_uprawnien') and 
             current_pracownik.rola.poziom_uprawnien <= 3)):
        messages.error(request, "Nie masz uprawnień do przeglądania raportów obecności.")
        return redirect('system_obecnosci')
    
    from datetime import date, timedelta
    from .models import DzienPracy, Obecnosc
    from django.db.models import Q, Sum, Avg
    
    # Parametry filtrowania
    dzisiaj = date.today()
    data_od = request.GET.get('data_od', (dzisiaj - timedelta(days=7)).strftime('%Y-%m-%d'))
    data_do = request.GET.get('data_do', dzisiaj.strftime('%Y-%m-%d'))
    zespol_id = request.GET.get('zespol')
    pracownik_id = request.GET.get('pracownik')
    
    # Konwersja dat
    try:
        data_od = datetime.strptime(data_od, '%Y-%m-%d').date()
        data_do = datetime.strptime(data_do, '%Y-%m-%d').date()
    except:
        data_od = dzisiaj - timedelta(days=7)
        data_do = dzisiaj
    
    # Filtry
    dni_query = DzienPracy.objects.filter(
        data__range=[data_od, data_do]
    )
    
    if zespol_id:
        dni_query = dni_query.filter(pracownik__zespol_id=zespol_id)
    
    if pracownik_id:
        dni_query = dni_query.filter(pracownik_id=pracownik_id)
    
    # Jeśli użytkownik to kierownik zespołu, pokaż tylko jego zespół
    if (hasattr(current_pracownik, 'rola') and hasattr(current_pracownik.rola, 'poziom_uprawnien') and 
        current_pracownik.rola.poziom_uprawnien == 3):  # Kierownik średni
        dni_query = dni_query.filter(pracownik__zespol=current_pracownik.zespol)
    
    dni_pracy = dni_query.select_related('pracownik', 'pracownik__zespol').order_by('-data', 'pracownik__nazwisko')
    
    # Statystyki
    statystyki = {
        'dni_obecne': dni_query.filter(status_dnia='obecny').count(),
        'dni_nieobecne': dni_query.filter(status_dnia='nieobecny').count(),
        'sredni_czas_pracy': dni_query.filter(czas_pracy__isnull=False).aggregate(
            avg=Avg('czas_pracy')
        )['avg'],
        'total_godzin': sum([dp.czas_pracy_godziny for dp in dni_query if dp.czas_pracy])
    }
    
    # Dostępne zespoły i pracownicy do filtrowania
    zespoly = Zespol.objects.all()
    pracownicy = Pracownik.objects.all().order_by('nazwisko', 'imie')
    
    context = {
        'dni_pracy': dni_pracy,
        'statystyki': statystyki,
        'data_od': data_od,
        'data_do': data_do,
        'zespol_id': int(zespol_id) if zespol_id else None,
        'pracownik_id': int(pracownik_id) if pracownik_id else None,
        'zespoly': zespoly,
        'pracownicy': pracownicy,
    }
    
    return render(request, 'pracownicy/raport_obecnosci.html', context)


@login_required
def historia_obecnosci(request, pracownik_id=None):
    """Historia obecności konkretnego pracownika"""
    current_user = request.user
    
    try:
        current_pracownik = current_user.pracownik
    except:
        messages.error(request, "Nie jesteś przypisany do żadnego pracownika.")
        return redirect('lista_pracownikow')
    
    # Jeśli nie podano ID, pokaż historię dla bieżącego użytkownika
    if not pracownik_id:
        pracownik = current_pracownik
    else:
        try:
            pracownik = Pracownik.objects.get(id=pracownik_id)
            
            # Sprawdź uprawnienia
            if (current_pracownik != pracownik and 
                (not hasattr(current_pracownik, 'rola') or current_pracownik.rola.poziom_uprawnien > 3)):
                messages.error(request, "Nie masz uprawnień do przeglądania historii tego pracownika.")
                return redirect('system_obecnosci')
                
        except Pracownik.DoesNotExist:
            messages.error(request, "Pracownik nie został znaleziony.")
            return redirect('system_obecnosci')
    
    from datetime import date, timedelta
    from .models import Obecnosc, DzienPracy
    
    # Parametry filtrowania
    dzisiaj = date.today()
    data_od = request.GET.get('data_od', (dzisiaj - timedelta(days=30)).strftime('%Y-%m-%d'))
    data_do = request.GET.get('data_do', dzisiaj.strftime('%Y-%m-%d'))
    
    try:
        data_od = datetime.strptime(data_od, '%Y-%m-%d').date()
        data_do = datetime.strptime(data_do, '%Y-%m-%d').date()
    except:
        data_od = dzisiaj - timedelta(days=30)
        data_do = dzisiaj
    
    # Pobierz obecności
    obecnosci = Obecnosc.objects.filter(
        pracownik=pracownik,
        data_czas__date__range=[data_od, data_do]
    ).order_by('-data_czas')
    
    # Pobierz dni pracy
    dni_pracy = DzienPracy.objects.filter(
        pracownik=pracownik,
        data__range=[data_od, data_do]
    ).order_by('-data')
    
    context = {
        'pracownik': pracownik,
        'obecnosci': obecnosci,
        'dni_pracy': dni_pracy,
        'data_od': data_od,
        'data_do': data_do,
        'current_pracownik': current_pracownik,
    }
    
    return render(request, 'pracownicy/historia_obecnosci.html', context)


@login_required
def zarzadzaj_statusy(request):
    """Zarządzanie statusami dni pracy (święta, delegacje, urlopy)"""
    current_user = request.user
    
    try:
        current_pracownik = current_user.pracownik
    except:
        messages.error(request, "Nie jesteś przypisany do żadnego pracownika.")
        return redirect('lista_pracownikow')
    
    # Sprawdź uprawnienia - tylko HR i kierownicy mogą zarządzać statusami
    if not (current_pracownik.rola == 'admin' or 
            (hasattr(current_pracownik, 'rola') and 
             hasattr(current_pracownik.rola, 'poziom_uprawnien') and 
             current_pracownik.rola.poziom_uprawnien <= 3)):
        messages.error(request, "Nie masz uprawnień do zarządzania statusami dni pracy.")
        return redirect('system_obecnosci')
    
    from datetime import date, timedelta
    from .models import DzienPracy, Pracownik, Zespol
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'ustaw_status':
            pracownik_id = request.POST.get('pracownik_id')
            data_str = request.POST.get('data')
            nowy_status = request.POST.get('status')
            
            try:
                data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                pracownik = Pracownik.objects.get(id=pracownik_id)
                
                # Sprawdź czy kierownik może edytować tego pracownika
                if (hasattr(current_pracownik, 'rola') and 
                    hasattr(current_pracownik.rola, 'poziom_uprawnien') and
                    current_pracownik.rola.poziom_uprawnien == 3 and 
                    pracownik.zespol != current_pracownik.zespol):
                    messages.error(request, "Nie możesz edytować pracowników spoza swojego zespołu.")
                    return redirect('zarzadzaj_statusy')
                
                # Utwórz lub zaktualizuj dzień pracy
                dzien_pracy, created = DzienPracy.objects.get_or_create(
                    pracownik=pracownik,
                    data=data_obj
                )
                dzien_pracy.status_dnia = nowy_status
                dzien_pracy.save()
                
                status_display = dict(DzienPracy.STATUS_CHOICES).get(nowy_status, nowy_status)
                messages.success(request, f"Status dnia {data_obj.strftime('%d.%m.%Y')} dla {pracownik.imie} {pracownik.nazwisko} został ustawiony na: {status_display}")
                
            except (ValueError, Pracownik.DoesNotExist) as e:
                messages.error(request, f"Błąd podczas ustawiania statusu: {str(e)}")
        
        elif action == 'ustaw_swieto_masowo':
            data_str = request.POST.get('data_swieta')
            nazwa_swieta = request.POST.get('nazwa_swieta', '')
            
            try:
                data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
                
                # Pobierz wszystkich pracowników (lub tylko z zespołu kierownika)
                if (hasattr(current_pracownik, 'rola') and 
                    hasattr(current_pracownik.rola, 'poziom_uprawnien') and
                    current_pracownik.rola.poziom_uprawnien == 3):  # Kierownik zespołu
                    pracownicy = Pracownik.objects.filter(zespol=current_pracownik.zespol)
                else:  # HR/Admin
                    pracownicy = Pracownik.objects.all()
                
                utworzone = 0
                for pracownik in pracownicy:
                    dzien_pracy, created = DzienPracy.objects.get_or_create(
                        pracownik=pracownik,
                        data=data_obj
                    )
                    dzien_pracy.status_dnia = 'swieto'
                    dzien_pracy.save()
                    if created:
                        utworzone += 1
                
                messages.success(request, f"Święto '{nazwa_swieta}' zostało ustawione dla {pracownicy.count()} pracowników na dzień {data_obj.strftime('%d.%m.%Y')}")
                
            except ValueError as e:
                messages.error(request, f"Błąd daty: {str(e)}")
    
    # Pobierz dane do wyświetlenia
    dzisiaj = date.today()
    data_od = request.GET.get('data_od', dzisiaj.strftime('%Y-%m-%d'))
    data_do = request.GET.get('data_do', (dzisiaj + timedelta(days=30)).strftime('%Y-%m-%d'))
    zespol_id = request.GET.get('zespol')
    
    try:
        data_od = datetime.strptime(data_od, '%Y-%m-%d').date()
        data_do = datetime.strptime(data_do, '%Y-%m-%d').date()
    except:
        data_od = dzisiaj
        data_do = dzisiaj + timedelta(days=30)
    
    # Filtry dla pracowników
    pracownicy_query = Pracownik.objects.all()
    if (hasattr(current_pracownik, 'rola') and 
        hasattr(current_pracownik.rola, 'poziom_uprawnien') and
        current_pracownik.rola.poziom_uprawnien == 3):  # Kierownik zespołu
        pracownicy_query = pracownicy_query.filter(zespol=current_pracownik.zespol)
    
    if zespol_id:
        pracownicy_query = pracownicy_query.filter(zespol_id=zespol_id)
    
    pracownicy = pracownicy_query.order_by('nazwisko', 'imie')
    
    # Pobierz dni pracy w zakresie
    dni_pracy = DzienPracy.objects.filter(
        data__range=[data_od, data_do],
        pracownik__in=pracownicy
    ).select_related('pracownik').order_by('-data', 'pracownik__nazwisko')
    
    # Zespoły do filtrowania
    zespoly = Zespol.objects.all()
    
    context = {
        'dni_pracy': dni_pracy,
        'pracownicy': pracownicy,
        'zespoly': zespoly,
        'data_od': data_od,
        'data_do': data_do,
        'zespol_id': int(zespol_id) if zespol_id else None,
        'current_pracownik': current_pracownik,
        'status_choices': DzienPracy.STATUS_CHOICES,
    }
    
    return render(request, 'pracownicy/zarzadzaj_statusy.html', context)


@login_required
def ustaw_urlop(request):
    """Szybkie ustawianie urlopu dla pracownika"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Metoda POST wymagana'}, status=405)
    
    current_user = request.user
    
    try:
        current_pracownik = current_user.pracownik
        
        # Sprawdź uprawnienia
        if not (current_pracownik.rola == 'admin' or 
                (hasattr(current_pracownik, 'rola') and 
                 hasattr(current_pracownik.rola, 'poziom_uprawnien') and 
                 current_pracownik.rola.poziom_uprawnien <= 3)):
            return JsonResponse({'error': 'Brak uprawnień'}, status=403)
        
        pracownik_id = request.POST.get('pracownik_id')
        data_od_str = request.POST.get('data_od')
        data_do_str = request.POST.get('data_do')
        
        # Walidacja danych
        pracownik = Pracownik.objects.get(id=pracownik_id)
        data_od = datetime.strptime(data_od_str, '%Y-%m-%d').date()
        data_do = datetime.strptime(data_do_str, '%Y-%m-%d').date()
        
        # Sprawdź czy kierownik może edytować tego pracownika
        if (hasattr(current_pracownik, 'rola') and 
            hasattr(current_pracownik.rola, 'poziom_uprawnien') and
            current_pracownik.rola.poziom_uprawnien == 3 and 
            pracownik.zespol != current_pracownik.zespol):
            return JsonResponse({'error': 'Nie możesz edytować pracowników spoza swojego zespołu'}, status=403)
        
        # Ustaw urlop dla każdego dnia w zakresie
        from datetime import timedelta
        current_date = data_od
        dni_utworzone = 0
        
        while current_date <= data_do:
            dzien_pracy, created = DzienPracy.objects.get_or_create(
                pracownik=pracownik,
                data=current_date
            )
            dzien_pracy.status_dnia = 'urlop'
            dzien_pracy.save()
            
            if created:
                dni_utworzone += 1
            
            current_date += timedelta(days=1)
        
        dni_total = (data_do - data_od).days + 1
        
        return JsonResponse({
            'success': True,
            'message': f'Urlop został ustawiony dla {pracownik.imie} {pracownik.nazwisko} od {data_od.strftime("%d.%m.%Y")} do {data_do.strftime("%d.%m.%Y")} ({dni_total} dni)'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===== POKOJE ROZMÓW GŁOSOWYCH =====

@login_required
def room_list(request):
    """Lista dostępnych pokoi rozmów"""
    rooms = [
        {'name': 'general', 'display_name': 'Pokój Ogólny'},
        {'name': 'hr', 'display_name': 'HR'},
        {'name': 'it', 'display_name': 'IT'},
        {'name': 'management', 'display_name': 'Zarządzanie'},
    ]
    return render(request, 'room_new.html', {'rooms': rooms})

@login_required
def room_detail(request, room_name):
    """Szczegóły pokoju rozmów (stary WebSocket)"""
    return render(request, 'room.html', {
        'room_name': room_name,
        'user': request.user
    })

# ===== PROSTY VOICE CHAT =====
import json
import time
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Przechowywanie wiadomości głosowych i aktywnych użytkowników w pamięci
voice_rooms = {}
active_users = {}  # {'room_name': {'user_id': last_seen_timestamp}}

@login_required
def voice_room_list(request):
    """Lista pokoi głosowych"""
    # Sprawdź ile osób jest aktywnych w pokoju ogólnym
    current_time = time.time()
    active_count = 0
    if 'general' in active_users:
        # Usuń nieaktywnych użytkowników (nie widziani przez 30s)
        active_users['general'] = {
            user_id: last_seen for user_id, last_seen in active_users['general'].items()
            if current_time - last_seen < 30
        }
        active_count = len(active_users['general'])
    
    rooms = [
        {
            'name': 'general', 
            'display_name': 'Pokój Ogólny', 
            'description': f'Główny pokój rozmów dla wszystkich pracowników. Aktywnych: {active_count} osób',
            'active_count': active_count
        },
    ]
    return render(request, 'voice_room_list.html', {
        'rooms': rooms,
        'user': request.user
    })

@login_required
def voice_room(request, room_name):
    """Pokój głosowy"""
    return render(request, 'voice_room.html', {
        'room_name': room_name,
        'user': request.user
    })

@csrf_exempt
@login_required
def send_voice_message(request, room_name):
    """Wyślij wiadomość głosową"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        audio_data = data.get('audio_data')  # base64
        
        if not audio_data:
            return JsonResponse({'error': 'No audio data'}, status=400)
        
        # Utwórz pokój jeśli nie istnieje
        if room_name not in voice_rooms:
            voice_rooms[room_name] = []
        
        # Dodaj wiadomość
        message = {
            'id': str(uuid.uuid4()),
            'user_id': request.user.id,
            'username': request.user.username,
            'audio_data': audio_data,
            'timestamp': time.time()
        }
        
        voice_rooms[room_name].append(message)
        
        # Ogranicz do 50 wiadomości
        if len(voice_rooms[room_name]) > 50:
            voice_rooms[room_name] = voice_rooms[room_name][-50:]
        
        print(f"[VOICE] User {request.user.username} sent message to {room_name}")
        
        return JsonResponse({
            'success': True,
            'message_id': message['id'],
            'total_messages': len(voice_rooms[room_name])
        })
        
    except Exception as e:
        print(f"[VOICE] Error sending message: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_voice_messages(request, room_name):
    """Pobierz wiadomości głosowe (fast polling dla real-time)"""
    last_timestamp = float(request.GET.get('last_timestamp', 0))
    timeout = 15  # Krótszy timeout dla real-time (15 sekund)
    start_time = time.time()
    
    # Oznacz użytkownika jako aktywnego
    if room_name not in active_users:
        active_users[room_name] = {}
    active_users[room_name][request.user.id] = time.time()
    
    while time.time() - start_time < timeout:
        if room_name in voice_rooms:
            # Znajdź nowe wiadomości
            new_messages = [
                msg for msg in voice_rooms[room_name] 
                if msg['timestamp'] > last_timestamp and msg['user_id'] != request.user.id
            ]
            
            if new_messages:
                print(f"[VOICE] Sending {len(new_messages)} real-time messages to {request.user.username}")
                return JsonResponse({
                    'messages': new_messages,
                    'room_name': room_name,
                    'active_users': len(active_users.get(room_name, {}))
                })
        
        time.sleep(0.5)  # Sprawdzaj co 500ms dla lepszego real-time
    
    # Timeout
    return JsonResponse({
        'messages': [], 
        'room_name': room_name,
        'active_users': len(active_users.get(room_name, {}))
    })