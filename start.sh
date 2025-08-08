#!/bin/bash
# Railway startup script that runs migrations before starting the server

echo "=== Railway Startup Script ==="
echo "Running migrations..."

# Run migrations
python manage.py migrate --noinput

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migrations failed"
    exit 1
fi

echo "Starting server..."
# Start the main application
exec DJANGO_SETTINGS_MODULE=baza_pracownikow.settings daphne -b 0.0.0.0 -p $PORT baza_pracownikow.asgi:application
