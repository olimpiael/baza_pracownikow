from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views_set_password import set_password_after_social
from . import voice_views, voice_sse

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
    
    # ===== VOICE CHAT ALTERNATYWY =====
    # Strona wyboru metody
    path('voice/', views.voice_methods, name='voice_methods'),
    
    # Opcja 1: HTTP Long Polling
    path('voice/polling/send/', voice_views.send_voice_chunk, name='send_voice_chunk'),
    path('voice/polling/get/<str:room_id>/', voice_views.get_voice_messages, name='get_voice_messages'),
    path('voice/polling/join/<str:room_id>/', voice_views.join_voice_room, name='join_voice_room_polling'),
    path('voice/polling/leave/<str:room_id>/', voice_views.leave_voice_room, name='leave_voice_room_polling'),
    path('voice/polling/<str:room_name>/', views.voice_polling_room, name='voice_polling_room'),
    
    # Opcja 2: Server-Sent Events
    path('voice/sse/stream/<str:room_id>/', voice_sse.voice_room_stream, name='voice_room_stream'),
    path('voice/sse/send/', voice_sse.send_voice_sse, name='send_voice_sse'),
    path('voice/sse/<str:room_name>/', views.voice_sse_room, name='voice_sse_room'),
    
    # Opcja 3: Socket.IO
    path('voice/socketio/<str:room_name>/', views.voice_socketio_room, name='voice_socketio_room'),
    
    # Pokoje rozmów głosowych (stare WebSocket)
    path('room/', views.room_list, name='room_list'),
    path('room/<str:room_name>/', views.room_detail, name='room_detail'),
]