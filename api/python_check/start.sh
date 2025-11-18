#!/bin/bash

# Script to start the FastAPI code quality analysis API

echo "Starting the API with uvicorn..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

echo "API is running at http://localhost:8000"
echo "Docs available at http://localhost:8000/docs"