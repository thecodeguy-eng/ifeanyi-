#!/bin/bash

# Build script for Vercel
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python3.9 manage.py migrate --noinput

echo "Collecting static files..."
python3.9 manage.py collectstatic --noinput --clear

echo "Build completed!"