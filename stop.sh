#!/bin/bash

# Stop the backend server
pkill -f "python manage.py runserver 0.0.0.0:8000"

# Stop the frontend server
pkill -f "npm run dev"