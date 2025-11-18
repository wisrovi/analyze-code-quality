#!/bin/bash

echo "Starting GitHub Download API..."

if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using .env.example as template."
    cp .env.example .env
    echo "Please edit .env file with your GitHub token."
fi

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload