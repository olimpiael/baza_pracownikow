# 🚨 BŁĄD ZNALEZIONY: Tabela pracownicy_ocenapracownika nie istnieje

## BŁĄD:
```
psycopg2.errors.UndefinedTable: relation "pracownicy_ocenapracownika" does not exist
```

## ROZWIĄZANIE - 3 opcje:

### ⚡ OPCJA 1: Automatyczne (po wdrożeniu)
Railway powinien automatycznie uruchomić migracje dzięki zmodyfikowanemu Procfile i railway.toml

### 🔧 OPCJA 2: Manual przez Railway CLI
```bash
# W terminalu Railway
railway shell
python migrate_railway.py
```

### 🎯 OPCJA 3: Manual przez Railway Dashboard
1. Otwórz Terminal w Railway Dashboard
2. Uruchom: `python manage.py migrate --noinput`
3. Sprawdź: `python manage.py showmigrations pracownicy`

## CO ZOSTAŁO NAPRAWIONE:
✅ Procfile - dodano automatyczne migracje
✅ railway.toml - dodano lifecycle.prestart  
✅ migrate_railway.py - skrypt do manual migration
✅ start.sh - bash script (backup)

## WERYFIKACJA:
Po zastosowaniu migracji sprawdź:
- https://twoja-domena/oceny/ - powinien działać
- https://twoja-domena/debug/all/ - info debugowe
- https://twoja-domena/debug/migrations/ - status migracji

## JEŚLI NADAL NIE DZIAŁA:
Użyj bezpiecznych wersji:
- https://twoja-domena/safe/oceny/
- https://twoja-domena/safe/zadania/

## LOGI RAILWAY:
```bash
railway logs
```
Powinieneś zobaczyć:
- "Running migrations..."
- "✅ Migrations completed successfully"
