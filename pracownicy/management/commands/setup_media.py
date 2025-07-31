from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from pracownicy.models import Pracownik
import os
import shutil

class Command(BaseCommand):
    help = 'Copy example images for employees without photos'

    def handle(self, *args, **options):
        # Create media directories
        media_path = settings.MEDIA_ROOT / 'dokumenty' / 'zdjecia'
        os.makedirs(media_path, exist_ok=True)
        
        # Default image path (you can add a default image to your project)
        default_image_path = settings.BASE_DIR / 'staticfiles' / 'default_profile.jpg'
        
        # Find employees without photos
        employees_without_photos = Pracownik.objects.filter(
            models.Q(zdjecie='') | models.Q(zdjecie__isnull=True)
        )
        
        self.stdout.write(f"Found {employees_without_photos.count()} employees without photos")
        
        # If you have a default image, copy it for employees without photos
        if os.path.exists(default_image_path):
            for employee in employees_without_photos:
                target_path = media_path / f'default_profile_{employee.id}.jpg'
                if not os.path.exists(target_path):
                    shutil.copy2(default_image_path, target_path)
                    employee.zdjecie = f'dokumenty/zdjecia/default_profile_{employee.id}.jpg'
                    employee.save()
                    self.stdout.write(f"Added default photo for {employee.imie} {employee.nazwisko}")
        
        self.stdout.write(self.style.SUCCESS('Successfully processed employee photos'))
