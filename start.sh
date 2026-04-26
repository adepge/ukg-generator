#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Migrate the database
python backend/manage.py migrate

# Install dependencies and start the frontend server
cd frontend && npm install

# Start the frontend server in the background
npm run dev &

# Change to the backend directory
cd ../backend

# Open the frontend in the browser
xdg-open http://localhost:5173

# Start the backend server
python manage.py runserver 0.0.0.0:8000

