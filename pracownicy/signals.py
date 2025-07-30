from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Pracownik
from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Pracownik
from django.utils import timezone
import random



channel_layer = get_channel_layer()

@receiver(post_save, sender=Pracownik)
def pracownik_saved(sender, instance, created, **kwargs):
    """Wysyła powiadomienie WebSocket gdy pracownik zostanie utworzony lub zaktualizowany"""
    action = 'created' if created else 'updated'
    message = f"Pracownik {instance.imie} {instance.nazwisko} został {'dodany' if created else 'zaktualizowany'}"
    
    async_to_sync(channel_layer.group_send)(
        'pracownicy_pracownicy_updates',
        {
            'type': 'employee_update',
            'action': action,
            'employee_id': instance.id,
            'employee_name': f"{instance.imie} {instance.nazwisko}",
            'message': message
        }
    )

@receiver(post_delete, sender=Pracownik)
def pracownik_deleted(sender, instance, **kwargs):
    """Wysyła powiadomienie WebSocket gdy pracownik zostanie usunięty"""
    message = f"Pracownik {instance.imie} {instance.nazwisko} został usunięty"
    
    async_to_sync(channel_layer.group_send)(
        'pracownicy_pracownicy_updates',
        {
            'type': 'employee_update',
            'action': 'deleted',
            'employee_id': instance.id,
            'employee_name': f"{instance.imie} {instance.nazwisko}",
            'message': message
        }
    )

def send_system_notification(message, level='info'):
    """Funkcja pomocnicza do wysyłania powiadomień systemowych"""
    async_to_sync(channel_layer.group_send)(
        'pracownicy_pracownicy_updates',
        {
            'type': 'system_notification',
            'message': message,
            'level': level
        }
    )

@receiver(user_signed_up)
def create_pracownik_for_social_user(request, user, **kwargs):
    if not hasattr(user, 'pracownik'):
        extra_data = {}
        if user.socialaccount_set.exists():
            extra_data = user.socialaccount_set.first().extra_data
        imie = extra_data.get('given_name', user.first_name or 'Imię')
        nazwisko = extra_data.get('family_name', user.last_name or 'Nazwisko')
        email = extra_data.get('email', user.email)
        base_username = (nazwisko or 'user').lower()
        random_digits = str(random.randint(100, 999))
        username = f"{base_username}{random_digits}"
        while User.objects.filter(username=username).exists():
            random_digits = str(random.randint(100, 999))
            username = f"{base_username}{random_digits}"
        user.username = username
        user.email = email
        user.save()
        pracownik = Pracownik.objects.create(
            user=user,
            imie=imie,
            nazwisko=nazwisko,
            pesel='00000000000',
            stanowisko='pracownik',
            rola='pracownik',
            data_zatrudnienia=timezone.now().date(),
            data_urodzenia=timezone.now().date(),
        )

        request.session['set_password_after_social'] = True
