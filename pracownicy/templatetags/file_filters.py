from django import template
from django.template.defaultfilters import filesizeformat
import os

register = template.Library()

@register.filter
def safe_filesize(file_field):
    """
    Safely get file size, return 'N/A' if file doesn't exist
    """
    if not file_field:
        return "N/A"
    
    try:
        return filesizeformat(file_field.size)
    except (FileNotFoundError, OSError, AttributeError):
        return "Plik niedostępny"

@register.filter
def file_exists(file_field):
    """
    Check if file actually exists on disk
    """
    if not file_field:
        return False
    
    try:
        return os.path.exists(file_field.path)
    except (AttributeError, ValueError):
        return False
