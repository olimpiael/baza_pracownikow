from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def preserve_params(request, **kwargs):
    """
    Zachowuje obecne parametry URL i dodaje nowe
    """
    params = request.GET.copy()
    for key, value in kwargs.items():
        params[key] = value
    return '?' + urlencode(params) if params else ''

@register.simple_tag
def edit_url(request, edit_id, edit_field):
    """
    Tworzy URL do edycji z zachowaniem sortowania
    """
    params = request.GET.copy()
    params['edit_id'] = edit_id
    params['edit_field'] = edit_field
    return '?' + urlencode(params)

@register.simple_tag
def cancel_edit_url(request):
    """
    Tworzy URL powrotu z edycji z zachowaniem sortowania
    """
    params = request.GET.copy()
    if 'edit_id' in params:
        del params['edit_id']
    if 'edit_field' in params:
        del params['edit_field']
    return '?' + urlencode(params) if params else request.path

@register.simple_tag
def can_edit_field(request, employee_id, field_name):
    """
    Sprawdza czy użytkownik może edytować konkretne pole konkretnego pracownika
    """
    from pracownicy.views import check_edit_permissions
    return check_edit_permissions(request.user, employee_id, field_name)
