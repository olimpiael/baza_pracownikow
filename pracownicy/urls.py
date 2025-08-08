from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views_set_password import set_password_after_social
from . import debug_views
from . import safe_views
from . import migration_views

urlpatterns = [
    path('', views.lista_pracownikow, name='lista_pracownikow'),
    path('api/', views.api_pracownicy, name='api_pracownicy'),
    path('dashboard/', views.dashboard_page, name='dashboard_page'),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('dashboard/pdf-report/', views.generate_pdf_report, name='generate_pdf_report'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('reset_password/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_sent.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('set_password', set_password_after_social, name='ustaw_haslo_po_social'),
    path('upload_cv/', views.UploadCVView.as_view(), name='upload_cv'),
    path('pracownik/<int:pracownik_id>/dokumenty/', views.upload_documents, name='upload_documents'),
    path('pracownik/<int:pracownik_id>/dokument/<str:document_type>/pobierz/', views.download_document, name='download_document'),
    path('pracownik/<int:pracownik_id>/dokument/<str:document_type>/usun/', views.delete_document, name='delete_document'),
    path('obecnosc/', views.system_obecnosci, name='system_obecnosci'),
    path('obecnosc/odbij/', views.odbij_obecnosc, name='odbij_obecnosc'),
    path('obecnosc/raport/', views.raport_obecnosci, name='raport_obecnosci'),
    path('obecnosc/historia/', views.historia_obecnosci, name='historia_obecnosci'),
    path('obecnosc/historia/<int:pracownik_id>/', views.historia_obecnosci, name='historia_obecnosci_pracownik'),
    path('obecnosc/statusy/', views.zarzadzaj_statusy, name='zarzadzaj_statusy'),
    path('obecnosc/ustaw-urlop/', views.ustaw_urlop, name='ustaw_urlop'),
    
    # === SYSTEM POWIADOMIEŃ ===
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    
    # === SYSTEM ZADAŃ ===
    path('zadania/', views.zadania_view, name='zadania_view'),
    
    # === SYSTEM OCEN 360° ===
    path('oceny/', views.oceny_pracownikow, name='oceny_pracownikow'),
    path('oceny/ocen/<int:pracownik_id>/', views.ocen_pracownika, name='ocen_pracownika'),
    
    # === SYSTEM ANALITYKI I RAPORTOWANIA ===
    path('analityka/', views.analityka_dashboard, name='analityka_dashboard'),
    path('analityka/generuj/', views.generuj_raport, name='generuj_raport'),
    path('analityka/raport/<int:raport_id>/', views.pokaz_raport, name='pokaz_raport'),
    
    # === PROSTY VOICE CHAT ===
    path('voice/', views.voice_room_list, name='voice_room_list'),
    path('voice/<str:room_name>/', views.voice_room, name='voice_room'),
    path('voice/<str:room_name>/send/', views.send_voice_message, name='send_voice_message'),
    path('voice/<str:room_name>/messages/', views.get_voice_messages, name='get_voice_messages'),
    
    # === DEBUG VIEWS FOR RAILWAY ===
    path('debug/models/', debug_views.debug_models, name='debug_models'),
    path('debug/templates/', debug_views.debug_templates, name='debug_templates'),
    path('debug/views/', debug_views.debug_views, name='debug_views'),
    path('debug/migrations/', debug_views.debug_migrations, name='debug_migrations'),
    path('debug/all/', debug_views.debug_all, name='debug_all'),
    
    # === SAFE FALLBACK VIEWS ===
    path('safe/oceny/', safe_views.safe_oceny_view, name='safe_oceny'),
    path('safe/zadania/', safe_views.safe_zadania_view, name='safe_zadania'),
    
    # === MIGRATION TOOLS FOR RAILWAY ===
    path('force-migrate/', migration_views.force_migrate, name='force_migrate'),
    path('migration-status/', migration_views.migration_status, name='migration_status'),
]