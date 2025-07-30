from django.db import models
from django.contrib.auth.models import User
from .validators import validate_pesel

# Create your models here.
class Zespol(models.Model):
    nazwa = models.CharField(max_length=100, unique=True)
    kod = models.CharField(max_length=20, unique=True, help_text="Unikalny kod zespołu (np. hr, it)", default="default")
    opis = models.TextField(blank=True, null=True)
    lider = models.ForeignKey('Pracownik', on_delete=models.SET_NULL, null=True, blank=True, related_name='zespoly_liderem')
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Zespół"
        verbose_name_plural = "Zespoły"
        ordering = ['nazwa']
    
    def __str__(self):
        return self.nazwa
    
    def liczba_pracownikow(self):
        return self.pracownicy.count()


class Stanowisko(models.Model):
    """Model dla stanowisk"""
    nazwa = models.CharField(max_length=100, unique=True)
    kod = models.CharField(max_length=20, unique=True, help_text="Unikalny kod stanowiska (np. dev, manager)", default="default")
    opis = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Stanowisko"
        verbose_name_plural = "Stanowiska"
        ordering = ['nazwa']
    
    def __str__(self):
        return self.nazwa

class Pracownik(models.Model):

    cv = models.FileField(upload_to='dokumenty/cv/', blank=True, null=True, verbose_name="CV")
    uploaded_at = models.DateTimeField(null=True, blank=True)
    
    # Dodatkowe dokumenty
    umowa_pracy = models.FileField(upload_to='dokumenty/umowy/', blank=True, null=True, verbose_name="Umowa o pracę")
    swiadectwo_pracy = models.FileField(upload_to='dokumenty/swiadectwa/', blank=True, null=True, verbose_name="Świadectwo pracy")
    dyplom = models.FileField(upload_to='dokumenty/dyplomy/', blank=True, null=True, verbose_name="Dyplom/Certyfikat")
    zdjecie = models.ImageField(upload_to='dokumenty/zdjecia/', blank=True, null=True, verbose_name="Zdjęcie")
    inne_dokumenty = models.FileField(upload_to='dokumenty/inne/', blank=True, null=True, verbose_name="Inne dokumenty")
    
    # Predefiniowane role - wystarczy dopisać nowy tuple żeby dodać rolę
    ROLE_CHOICES = [
        ('admin', 'Administrator Systemu'),
        ('hr', 'Specjalista HR'),
        ('ceo', 'Dyrektor Generalny'),
        ('kierownik', 'Kierownik Zespołu'),
        ('przelozony_dzialu', 'Przełożony Działu'),
        ('marketing_spec', 'Specjalista ds. Marketingu'),
        ('sales_rep', 'Przedstawiciel Handlowy'),
        ('accountant', 'Księgowy'),
        ('support', 'Wsparcie Techniczne'),
        ('intern', 'Stażysta'),
        ('pracownik', 'Pracownik'),
        # Dodaj nową rolę tutaj - format: ('kod', 'Wyświetlana nazwa')
    ]
    
    # Hierarchia organizacyjna - kto może zarządzać kim
    HIERARCHY_MAP = {
        'admin': ['admin', 'hr', 'ceo', 'przelozony_dzialu', 'kierownik', 'marketing_spec', 'sales_rep', 'accountant', 'support', 'intern', 'pracownik'],
        'hr': ['przelozony_dzialu', 'kierownik', 'marketing_spec', 'sales_rep', 'accountant', 'support', 'intern', 'pracownik'],
        'ceo': ['przelozony_dzialu', 'kierownik', 'marketing_spec', 'sales_rep', 'accountant', 'support', 'intern', 'pracownik'],
        'przelozony_dzialu': ['kierownik', 'marketing_spec', 'sales_rep', 'accountant', 'support', 'intern', 'pracownik'],
        'kierownik': ['marketing_spec', 'sales_rep', 'accountant', 'support', 'intern', 'pracownik'],
        'marketing_spec': [],
        'sales_rep': [],
        'accountant': [],
        'support': [],
        'intern': [],
        'pracownik': [],
    }
    
    # Predefiniowane zespoły - jak role
    TEAM_CHOICES = [
        ('hr', 'HR'),
        ('it', 'IT Support'),
        ('dev', 'Development'),
        ('marketing', 'Marketing'),
        ('sales', 'Sprzedaż'), 
        ('finance', 'Finanse'),
        ('management', 'Zarządzanie'),
        ('mixed', 'Mixed Team'),
        ('bus_it', 'Bus IT Systems'),
        # Dodaj nowy zespół tutaj - format: ('kod', 'Nazwa')
    ]
    
    # Predefiniowane stanowiska
    STANOWISKO_CHOICES = [
        ('admin', 'Administrator'),
        ('junior_dev', 'Junior Developer'),
        ('senior_dev', 'Senior Developer'),
        ('team_lead', 'Team Leader'),
        ('project_manager', 'Project Manager'),
        ('hr_specialist', 'Specjalista HR'),
        ('recruiter', 'Rekruter'),
        ('accountant', 'Księgowy'),
        ('financial_analyst', 'Analityk Finansowy'),
        ('marketing_specialist', 'Specjalista Marketingu'),
        ('sales_rep', 'Przedstawiciel Handlowy'),
        ('sales_manager', 'Menedżer Sprzedaży'),
        ('support_specialist', 'Specjalista Wsparcia'),
        ('system_admin', 'Administrator Systemu'),
        ('business_analyst', 'Analityk Biznesowy'),
        ('ux_designer', 'UX Designer'),
        ('qa_tester', 'Tester QA'),
        ('intern', 'Stażysta'),
        ('ceo', 'Dyrektor Generalny'),
        ('cto', 'Dyrektor Techniczny'),
        ('cfo', 'Dyrektor Finansowy'),
        ('programista', 'Programista'),
        # Dodaj nowe stanowisko tutaj - format: ('kod', 'Nazwa')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    imie = models.CharField(max_length=30)
    nazwisko = models.CharField(max_length=30)
    pesel = models.CharField(max_length=11, validators=[validate_pesel])
    stanowisko = models.CharField(max_length=50, choices=STANOWISKO_CHOICES)
    rola = models.CharField(max_length=20, choices=ROLE_CHOICES, default='pracownik')
    zespol = models.CharField(max_length=50, choices=TEAM_CHOICES, blank=True, null=True)
    # Hierarchia - pole do przechowywania przełożonego
    przelozony = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='podwladni')
    # Departament/dział dla lepszej organizacji
    dzial = models.CharField(max_length=50, blank=True, null=True)
    zarobki = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Zarobki",
        help_text="Miesięczne wynagrodzenie brutto w PLN"
    )
    
    # Pola do oceny pracownika
    OCENA_CHOICES = [
        (1, '⭐ - Niewystarczająca'),
        (2, '⭐⭐ - Poniżej oczekiwań'),
        (3, '⭐⭐⭐ - Zadowalająca'),
        (4, '⭐⭐⭐⭐ - Dobra'),
        (5, '⭐⭐⭐⭐⭐ - Doskonała'),
    ]
    
    ocena = models.IntegerField(
        choices=OCENA_CHOICES,
        null=True,
        blank=True,
        verbose_name="Ocena pracownika",
        help_text="Ostatnia ocena pracownika (1-5 gwiazdek)"
    )
    data_ostatniej_oceny = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data ostatniej oceny",
        help_text="Kiedy była wykonana ostatnia ocena"
    )
    komentarz_oceny = models.TextField(
        blank=True,
        null=True,
        verbose_name="Komentarz do oceny",
        help_text="Dodatkowe uwagi do oceny pracownika"
    )
    
    data_zatrudnienia = models.DateField()
    data_urodzenia = models.DateField()
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            # 6.1 Admin - Pełna kontrola nad systemem
            ('can_manage_system', 'Can manage system (reset DB, import/export)'),
            ('can_manage_users_and_roles', 'Can manage users and roles'),
            ('can_view_all_data', 'Can view and modify all data (employees, reports, logs)'),
            
            # 6.2 Pani Anetka - Uprawnienia kadrowo-organizacyjne
            ('can_manage_employees', 'Can add/remove/edit employees'),
            ('can_view_personal_data', 'Can access personal employee data'),
            
            # 6.3 CEO - Dostęp do podglądu strategicznych danych
            ('can_view_all_users', 'Can view all users'),
            ('can_view_strategic_data', 'Can view strategic data and insights'),
            
            # 6.4 Kierownik - Zarządzanie zespołem
            ('can_manage_team', 'Can manage employees in own team'),
            ('can_view_team_data', 'Can view team data and reports'),
            
            # 6.5 Pracownik - Użytkownik końcowy
            ('can_view_own_profile', 'Can view own profile'),
            ('can_update_own_contact', 'Can update own contact info and password'),
        ]

    def get_ocena_display(self):
        """Zwraca opis oceny w formie gwiazdek"""
        if self.ocena:
            stars = "⭐" * self.ocena
            return f"{stars} ({self.ocena}/5)"
        return "Brak oceny"
    
    def get_ocena_color_class(self):
        """Zwraca klasę CSS dla koloru oceny"""
        if not self.ocena:
            return "text-muted"
        elif self.ocena <= 2:
            return "text-danger"
        elif self.ocena == 3:
            return "text-warning"
        else:
            return "text-success"
    
    def potrzebuje_oceny(self):
        """Sprawdza czy pracownik potrzebuje oceny (brak oceny lub stara ocena > 12 miesięcy)"""
        from datetime import date, timedelta
        if not self.data_ostatniej_oceny:
            return True
        # Jeśli ostatnia ocena była ponad rok temu
        rok_temu = date.today() - timedelta(days=365)
        return self.data_ostatniej_oceny < rok_temu

    def get_documents_count(self):
        """Zwraca liczbę wgranych dokumentów"""
        count = 0
        if self.cv: count += 1
        if self.umowa_pracy: count += 1
        if self.swiadectwo_pracy: count += 1
        if self.dyplom: count += 1
        if self.zdjecie: count += 1
        if self.inne_dokumenty: count += 1
        return count
    
    def get_documents_list(self):
        """Zwraca listę nazw dostępnych dokumentów"""
        docs = []
        if self.cv: docs.append('CV')
        if self.umowa_pracy: docs.append('Umowa')
        if self.swiadectwo_pracy: docs.append('Świadectwo')
        if self.dyplom: docs.append('Dyplom')
        if self.zdjecie: docs.append('Zdjęcie')
        if self.inne_dokumenty: docs.append('Inne')
        return docs

    def __str__(self):
        return f"{self.imie} {self.nazwisko}"
    
    def get_zespol_display_name(self):
        """Zwraca pełną nazwę zespołu"""
        for code, name in self.TEAM_CHOICES:
            if code == self.zespol:
                return name
        return self.zespol or "Brak zespołu"
    
    def is_admin(self):
        return self.rola == 'admin'
    
    def is_hr(self):
        return self.rola == 'hr'
    
    def is_ceo(self):
        return self.rola == 'ceo'
    
    def is_kierownik(self):
        return self.rola == 'kierownik'
    
    def is_pracownik(self):
        return self.rola == 'pracownik'
    
    def can_view_all_employees(self):
        return self.rola in ['admin', 'hr', 'ceo']
    
    def can_manage_employees(self):
        return self.rola in ['admin', 'hr']
    
    def can_view_team(self):
        return self.rola in ['admin', 'hr', 'ceo', 'kierownik']

    def can_view_employee(self, target_employee):
        if self.rola == 'admin':
            return True  # Admin widzi wszystkich
        elif self.rola == 'hr':
            return True  # HR widzi wszystkich
        elif self.rola == 'ceo':
            return True  # CEO widzi wszystkich
        elif self.rola == 'kierownik':
            return target_employee.zespol == self.zespol  # Kierownik widzi tylko swój zespół
        elif self.rola == 'pracownik':
            return target_employee.id == self.id  # Pracownik widzi tylko siebie
        return False
    
    # Nowe metody hierarchiczne
    def get_subordinates(self):
        """Zwraca wszystkich bezpośrednich podwładnych"""
        return Pracownik.objects.filter(przelozony=self)
    
    def get_all_subordinates(self):
        """Zwraca wszystkich podwładnych (rekurencyjnie w dół hierarchii)"""
        subordinates = []
        direct_subordinates = self.get_subordinates()
        
        for subordinate in direct_subordinates:
            subordinates.append(subordinate)
            subordinates.extend(subordinate.get_all_subordinates())
        
        return subordinates
    
    def can_manage_hierarchical(self, target_employee):
        """Sprawdza czy może zarządzać pracownikiem na podstawie hierarchii"""
        # Admin może wszystko
        if self.rola == 'admin':
            return True
            
        # HR może zarządzać wszystkimi poza adminami
        if self.rola == 'hr' and target_employee.rola != 'admin':
            return True
            
        # CEO może zarządzać wszystkimi poza adminami i HR
        if self.rola == 'ceo' and target_employee.rola not in ['admin', 'hr']:
            # CEO nie może zarządzać samym sobą (zmieniać swojej roli)
            if target_employee.id == self.id:
                return False
            return True
            
        # Sprawdź czy docelowa rola jest w hierarchii pod tą rolą
        allowed_roles = self.HIERARCHY_MAP.get(self.rola, [])
        if target_employee.rola in allowed_roles:
            return True
            
        # Sprawdź czy jest bezpośrednim przełożonym
        if target_employee.przelozony == self:
            return True
            
        # Sprawdź czy jest w hierarchii podwładnych
        all_subordinates = self.get_all_subordinates()
        if target_employee in all_subordinates:
            return True
            
        return False
    
    def get_hierarchy_level(self):
        """Zwraca poziom w hierarchii (0 = najwyższy)"""
        hierarchy_levels = {
            'admin': 0,
            'ceo': 1,
            'hr': 1,
            'przelozony_dzialu': 2,
            'kierownik': 3,
            'pracownik': 4,
            'marketing_spec': 4,
            'sales_rep': 4,
            'accountant': 4,
            'support': 4,
            'intern': 5,
        }
        return hierarchy_levels.get(self.rola, 99)


class ChatMessage(models.Model):
    """Model dla wiadomości czatu zespołowego"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField(max_length=1000)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Wiadomość czatu"
        verbose_name_plural = "Wiadomości czatu"
        ordering = ['-timestamp']  # Najnowsze na górze
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}..."
    
    @property
    def user_display_name(self):
        """Zwraca nazwę użytkownika do wyświetlenia"""
        try:
            pracownik = self.user.pracownik
            return f"{pracownik.imie} {pracownik.nazwisko}"
        except:
            return self.user.username


class Rola(models.Model):
    """Model dla ról użytkowników"""
    
    POZIOM_UPRAWNIEN_CHOICES = [
        (0, 'Administrator (najwyższy poziom)'),
        (1, 'Kierownictwo wysokie (CEO, CTO)'),
        (2, 'HR i zarządzanie'),
        (3, 'Kierownictwo średnie (kierownik działu)'),
        (4, 'Kierownictwo niskie (team leader)'),
        (5, 'Specjalista'),
        (6, 'Pracownik podstawowy'),
        (7, 'Stażysta (najniższy poziom)'),
    ]
    
    nazwa = models.CharField(max_length=50, unique=True)
    kod = models.CharField(max_length=20, unique=True, help_text="Unikalny kod roli (np. admin, hr)", default="default")
    opis = models.TextField(blank=True, null=True)
    poziom_uprawnien = models.IntegerField(
        choices=POZIOM_UPRAWNIEN_CHOICES, 
        default=6,
        help_text="Poziom uprawnień - niższa liczba = wyższe uprawnienia"
    )
    
    class Meta:
        verbose_name = "Rola"
        verbose_name_plural = "Role"
        ordering = ['poziom_uprawnien', 'nazwa']
    
    def __str__(self):
        return f"{self.nazwa} (poziom {self.poziom_uprawnien})"


class Obecnosc(models.Model):
    """Model dla systemu obecności pracowników"""
    
    STATUS_CHOICES = [
        ('wejscie', 'Wejście'),
        ('wyjscie', 'Wyjście'),
        ('przerwa_start', 'Początek przerwy'),
        ('przerwa_koniec', 'Koniec przerwy'),
    ]
    
    pracownik = models.ForeignKey(
        Pracownik, 
        on_delete=models.CASCADE, 
        related_name='obecnosci'
    )
    data_czas = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    lokalizacja = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Opcjonalna lokalizacja odbicia (np. biuro, praca zdalna)"
    )
    adres_ip = models.GenericIPAddressField(blank=True, null=True)
    uwagi = models.TextField(blank=True, null=True)
    
    # Pola automatyczne
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    zmodyfikowane_przez = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Użytkownik który zmodyfikował rekord"
    )
    
    class Meta:
        verbose_name = "Obecność"
        verbose_name_plural = "Obecności"
        ordering = ['-data_czas']
        indexes = [
            models.Index(fields=['pracownik', 'data_czas']),
            models.Index(fields=['data_czas']),
        ]
    
    def __str__(self):
        return f"{self.pracownik} - {self.get_status_display()} ({self.data_czas.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def data(self):
        """Zwraca samą datę bez czasu"""
        return self.data_czas.date()
    
    @property
    def czas(self):
        """Zwraca sam czas bez daty"""
        return self.data_czas.time()


class DzienPracy(models.Model):
    """Model agregujący informacje o dniu pracy pracownika"""
    
    pracownik = models.ForeignKey(
        Pracownik, 
        on_delete=models.CASCADE, 
        related_name='dni_pracy'
    )
    data = models.DateField()
    czas_wejscia = models.TimeField(null=True, blank=True)
    czas_wyjscia = models.TimeField(null=True, blank=True)
    czas_przerw = models.DurationField(null=True, blank=True, help_text="Łączny czas przerw")
    czas_pracy = models.DurationField(null=True, blank=True, help_text="Łączny czas pracy")
    
    # Status dnia
    STATUS_CHOICES = [
        ('obecny', 'Obecny'),
        ('nieobecny', 'Nieobecny'),
        ('urlop', 'Urlop'),
        ('choroba', 'Zwolnienie lekarskie'),
        ('swieto', 'Święto'),
        ('delegacja', 'Delegacja'),
    ]
    status_dnia = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='nieobecny'
    )
    
    # Pola automatyczne
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dzień pracy"
        verbose_name_plural = "Dni pracy"
        unique_together = ['pracownik', 'data']
        ordering = ['-data']
        indexes = [
            models.Index(fields=['pracownik', 'data']),
            models.Index(fields=['data']),
        ]
    
    def __str__(self):
        return f"{self.pracownik} - {self.data} ({self.get_status_dnia_display()})"
    
    @property
    def czas_pracy_godziny(self):
        """Zwraca czas pracy w godzinach jako float"""
        if self.czas_pracy:
            return self.czas_pracy.total_seconds() / 3600
        return 0.0
    
    def oblicz_czas_pracy(self):
        """Oblicza i aktualizuje czas pracy na podstawie wpisów obecności"""
        from datetime import timedelta
        
        obecnosci = self.pracownik.obecnosci.filter(
            data_czas__date=self.data
        ).order_by('data_czas')
        
        if not obecnosci.exists():
            self.status_dnia = 'nieobecny'
            self.czas_pracy = timedelta(0)
            self.save()
            return
        
        # Znajdź pierwsze wejście i ostatnie wyjście
        wejscia = obecnosci.filter(status='wejscie')
        wyjscia = obecnosci.filter(status='wyjscie')
        
        if wejscia.exists():
            self.czas_wejscia = wejscia.first().data_czas.time()
        
        if wyjscia.exists():
            self.czas_wyjscia = wyjscia.last().data_czas.time()
        
        # Oblicz czas przerw
        przerwy_start = obecnosci.filter(status='przerwa_start')
        przerwy_koniec = obecnosci.filter(status='przerwa_koniec')
        
        czas_przerw = timedelta(0)
        for i, start in enumerate(przerwy_start):
            if i < przerwy_koniec.count():
                koniec = przerwy_koniec[i]
                czas_przerw += koniec.data_czas - start.data_czas
        
        self.czas_przerw = czas_przerw
        
        # Oblicz całkowity czas pracy
        if self.czas_wejscia and self.czas_wyjscia:
            from datetime import datetime, time
            dt_wejscie = datetime.combine(self.data, self.czas_wejscia)
            dt_wyjscie = datetime.combine(self.data, self.czas_wyjscia)
            
            # Jeśli wyjście jest przed wejściem, to znaczy że jest następnego dnia
            if dt_wyjscie < dt_wejscie:
                dt_wyjscie += timedelta(days=1)
            
            self.czas_pracy = (dt_wyjscie - dt_wejscie) - czas_przerw
            self.status_dnia = 'obecny'
        else:
            self.czas_pracy = timedelta(0)
        
        self.save()

class VoiceRoom(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)