#!/bin/bash

echo "BUILD START"

# Install dependencies
echo "Installing dependencies..."
python3.9 -m pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python3.9 manage.py collectstatic --noinput --clear

# Run migrations
echo "Running migrations..."
python3.9 manage.py migrate --noinput

echo "BUILD END"