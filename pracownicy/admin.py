from django.contrib import admin
from .models import Pracownik, Zespol, ChatMessage, Rola, Stanowisko

# Register your models here.
# Usunięto PracownikInline bo zespoły są teraz CharField choices

@admin.register(Zespol)
class ZespolAdmin(admin.ModelAdmin):
    list_display = ['nazwa', 'kod', 'lider', 'liczba_pracownikow', 'data_utworzenia']
    list_filter = ['data_utworzenia', 'data_modyfikacji']
    search_fields = ['nazwa', 'kod', 'opis']
    readonly_fields = ['data_utworzenia', 'data_modyfikacji']
    ordering = ['nazwa']
    
    def liczba_pracownikow(self, obj):
        """Liczy pracowników przypisanych do tego zespołu"""
        from .models import Pracownik
        # Jeśli mamy kod zespołu, sprawdź przez choices (backwards compatibility)
        team_code = obj.kod
        if team_code:
            return Pracownik.objects.filter(zespol=team_code).count()
        return 0
    
    liczba_pracownikow.short_description = 'Liczba pracowników'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        try:
            pracownik = Pracownik.objects.get(user=request.user)
            if pracownik.is_kierownik() and pracownik.zespol:
                return qs.filter(id=pracownik.zespol.id)
        except Pracownik.DoesNotExist:
            pass
        return qs
    
    fieldsets = (
        ('Informacje podstawowe', {
            'fields': ('nazwa', 'opis')
        }),
        ('Zarządzanie', {
            'fields': ('lider',)
        }),
        ('Informacje systemowe', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Pracownik)
class PracownikAdmin(admin.ModelAdmin):
    list_display = ['imie', 'nazwisko', 'pesel', 'stanowisko', 'rola', 'zespol', 'zarobki', 'ocena', 'data_ostatniej_oceny', 'has_documents', 'user', 'data_zatrudnienia', 'data_utworzenia']
    list_filter = ['stanowisko', 'rola', 'zespol', 'ocena', 'data_zatrudnienia', 'data_utworzenia']
    search_fields = ['imie', 'nazwisko', 'pesel', 'user__username']
    readonly_fields = ['data_utworzenia', 'data_modyfikacji']
    ordering = ['-data_utworzenia']
    
    def has_documents(self, obj):
        """Pokazuje czy pracownik ma wgrane dokumenty"""
        docs = []
        if obj.cv: docs.append('CV')
        if obj.umowa_pracy: docs.append('Umowa')
        if obj.swiadectwo_pracy: docs.append('Świadectwo')
        if obj.dyplom: docs.append('Dyplom')
        if obj.zdjecie: docs.append('Zdjęcie')
        if obj.inne_dokumenty: docs.append('Inne')
        return ', '.join(docs) if docs else 'Brak'
    
    has_documents.short_description = 'Dokumenty'
    
    
    def has_add_permission(self, request):
        """Kto może dodawać pracowników w panelu admina"""
        try:
            pracownik = Pracownik.objects.get(user=request.user)
            return (request.user.has_perm('pracownicy.can_manage_employees') or 
                    pracownik.rola in ['admin', 'hr'])
        except Pracownik.DoesNotExist:
            return request.user.has_perm('pracownicy.can_manage_employees')
    
    def has_change_permission(self, request, obj=None):
        """Kto może edytować pracowników w panelu admina"""
        try:
            pracownik = Pracownik.objects.get(user=request.user)
            # Kierownik może edytować tylko pracowników ze swojego zespołu
            if pracownik.rola == 'kierownik':
                if obj and obj.zespol != pracownik.zespol:
                    return False
                return True
            return (request.user.has_perm('pracownicy.can_manage_employees') or 
                    pracownik.rola in ['admin', 'hr'])
        except Pracownik.DoesNotExist:
            return request.user.has_perm('pracownicy.can_manage_employees')
    
    def has_delete_permission(self, request, obj=None):
        """Kto może usuwać pracowników w panelu admina"""
        try:
            pracownik = Pracownik.objects.get(user=request.user)
            # Kierownik może usuwać tylko pracowników ze swojego zespołu
            if pracownik.rola == 'kierownik':
                if obj and obj.zespol != pracownik.zespol:
                    return False
                return True
            return (request.user.has_perm('pracownicy.can_manage_employees') or 
                    pracownik.rola in ['admin', 'hr'])
        except Pracownik.DoesNotExist:
            return request.user.has_perm('pracownicy.can_manage_employees')
    
    def has_view_permission(self, request, obj=None):
        """Kto może przeglądać pracowników w panelu admina"""
        try:
            pracownik = Pracownik.objects.get(user=request.user)
            # Kierownik może przeglądać pracowników ze swojego zespołu
            if pracownik.rola == 'kierownik':
                if obj and obj.zespol != pracownik.zespol:
                    return False
                return True
            return (request.user.has_perm('pracownicy.can_view_all_users') or 
                    request.user.has_perm('pracownicy.can_manage_employees') or
                    pracownik.rola in ['admin', 'hr', 'ceo'])
        except Pracownik.DoesNotExist:
            return (request.user.has_perm('pracownicy.can_view_all_users') or 
                    request.user.has_perm('pracownicy.can_manage_employees'))
    
    def get_queryset(self, request):
        """Filtruj pracowników w zależności od roli"""
        qs = super().get_queryset(request)
        try:
            pracownik = Pracownik.objects.get(user=request.user)
            if pracownik.rola == 'kierownik' and pracownik.zespol:
                # Kierownik widzi tylko swój zespół
                return qs.filter(zespol=pracownik.zespol)
            elif pracownik.rola == 'pracownik':
                # Pracownik widzi tylko siebie
                return qs.filter(id=pracownik.id)
        except Pracownik.DoesNotExist:
            pass
        return qs
    
    def get_fields(self, request, obj=None):
        """Które pola pokazać w zależności od uprawnień"""
        fields = ['imie', 'nazwisko', 'stanowisko', 'rola', 'zespol', 'user']
        
        # Dokumenty dostępne dla wszystkich uprawnionych użytkowników
        fields.extend(['cv', 'umowa_pracy', 'swiadectwo_pracy', 'dyplom', 'zdjecie', 'inne_dokumenty'])
        
        # Pokaż dane osobowe tylko osobom z uprawnieniem
        if request.user.has_perm('pracownicy.can_view_personal_data'):
            fields.extend(['pesel', 'data_urodzenia', 'data_zatrudnienia'])
        
        # Pokaż zarobki i oceny tylko dla HR/Admin/CEO
        try:
            pracownik = Pracownik.objects.get(user=request.user)
            if pracownik.rola in ['admin', 'hr', 'ceo']:
                fields.extend(['zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny'])
        except Pracownik.DoesNotExist:
            if request.user.has_perm('pracownicy.can_manage_employees'):
                fields.extend(['zarobki', 'ocena', 'data_ostatniej_oceny', 'komentarz_oceny'])
        
        return fields

    fieldsets = (
        ('Dane osobowe', {
            'fields': ('imie', 'nazwisko', 'pesel', 'data_urodzenia')
        }),
        ('Dane zawodowe', {
            'fields': ('stanowisko', 'rola', 'zespol', 'data_zatrudnienia', 'zarobki')
        }),
        ('Ocena pracownika', {
            'fields': ('ocena', 'data_ostatniej_oceny', 'komentarz_oceny')
        }),
        ('Dokumenty', {
            'fields': ('cv', 'umowa_pracy', 'swiadectwo_pracy', 'dyplom', 'zdjecie', 'inne_dokumenty'),
            'description': 'Dokumenty i pliki pracownika'
        }),
        ('Konto użytkownika', {
            'fields': ('user',)
        }),
        ('Informacje systemowe', {
            'fields': ('data_utworzenia', 'data_modyfikacji'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user_display_name', 'message_preview', 'timestamp', 'is_deleted']
    list_filter = ['timestamp', 'is_deleted', 'user']
    search_fields = ['message', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    list_per_page = 50
    
    def message_preview(self, obj):
        """Pokazuje skróconą wersję wiadomości"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Wiadomość'
    
    def user_display_name(self, obj):
        """Pokazuje czytelną nazwę użytkownika"""
        return obj.user_display_name
    user_display_name.short_description = 'Użytkownik'
    
    actions = ['mark_as_deleted', 'mark_as_not_deleted']
    
    def mark_as_deleted(self, request, queryset):
        """Oznacz wiadomości jako usunięte"""
        queryset.update(is_deleted=True)
        self.message_user(request, f"Oznaczono {queryset.count()} wiadomości jako usunięte.")
    mark_as_deleted.short_description = "Oznacz jako usunięte"
    
    def mark_as_not_deleted(self, request, queryset):
        """Przywróć wiadomości"""
        queryset.update(is_deleted=False)
        self.message_user(request, f"Przywrócono {queryset.count()} wiadomości.")
    mark_as_not_deleted.short_description = "Przywróć wiadomości"


@admin.register(Rola)
class RolaAdmin(admin.ModelAdmin):
    list_display = ['nazwa', 'kod', 'poziom_uprawnien', 'opis']
    search_fields = ['nazwa', 'kod', 'opis']
    ordering = ['poziom_uprawnien', 'nazwa']
    list_filter = ['poziom_uprawnien']


@admin.register(Stanowisko)
class StanowiskoAdmin(admin.ModelAdmin):
    list_display = ['nazwa', 'kod', 'opis']
    search_fields = ['nazwa', 'kod', 'opis']
    ordering = ['nazwa']


