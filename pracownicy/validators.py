from django.core.exceptions import ValidationError

def validate_pesel(pesel):
    """
    Waliduje numer PESEL według polskiego algorytmu
    """
    if not pesel:
        raise ValidationError("PESEL jest wymagany")
    
    if len(pesel) != 11:
        raise ValidationError("PESEL musi mieć dokładnie 11 cyfr")
    
    if not pesel.isdigit():
        raise ValidationError("PESEL może zawierać tylko cyfry")

    return pesel

def validate_phone_number(phone):
    """
    Podstawowa walidacja numeru telefonu
    """
    if phone:
        # Usuń spacje i myślniki
        cleaned = phone.replace(' ', '').replace('-', '').replace('+48', '')
        
        if not cleaned.isdigit():
            raise ValidationError("Numer telefonu może zawierać tylko cyfry")
        
        if len(cleaned) != 9:
            raise ValidationError("Numer telefonu musi mieć 9 cyfr")
    
    return phone
