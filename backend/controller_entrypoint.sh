#!/bin/bash

# Runs the database migration if needed
python -m flask db upgrade
python -m flask db-seeds

# Starts the production server
gunicorn -b :$PORT -w 3 controller_app:app

