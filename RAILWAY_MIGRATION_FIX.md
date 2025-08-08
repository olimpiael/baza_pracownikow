# Railway Migration Instructions for OcenaPracownika Model

## PROBLEM:
Railway serwer pokazuje błąd 500 dla stron /zadania/ i /oceny/ ponieważ nie została zastosowana migracja 0022_ocenapracownika.py

## ROZWIĄZANIE:

### Opcja 1: Przez Railway Dashboard
1. Wejdź w Railway Dashboard
2. Otwórz Terminal dla swojego projektu
3. Uruchom: `python manage.py migrate`

### Opcja 2: Przez Railway CLI
```bash
railway shell
python manage.py migrate
```

### Opcja 3: Automatyczne migracje w railway.toml
Dodaj do railway.toml w sekcji [build]:
```toml
[build]
builder = "nixpacks"

[deploy]
healthcheckPath = "/"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[[deploy.environmentVariables]]
name = "DJANGO_MIGRATE_ON_START"
value = "true"
```

### Opcja 4: Dodaj migrację do Procfile
Zmień Procfile na:
```
release: python manage.py migrate
web: gunicorn baza_pracownikow.wsgi --bind 0.0.0.0:$PORT
```

## SPRAWDŹ CZY DZIAŁA:
Po zastosowaniu migracji sprawdź:
- /oceny/ - powinien pokazać system ocen 360°
- /zadania/ - powinien pokazać kanban board
- /admin/ - sprawdź czy model OcenaPracownika jest dostępny

## MODELE DO MIGRACJI:
- OcenaPracownika (migracja 0022)
- Zadanie (migracja 0021)

## JEŚLI NADAL NIE DZIAŁA:
Sprawdź logi Railway:
```bash
railway logs
```

Lub sprawdź w Django Shell czy modele istnieją:
```python
from pracownicy.models import OcenaPracownika, Zadanie
print("Modele załadowane pomyślnie!")
```
