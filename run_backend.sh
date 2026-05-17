#!/bin/bash
# LexGuard Backend — Local Development Runner

echo "🛡️  Starting LexGuard Backend..."
echo "================================"

# Check for .env file
if [ ! -f backend/.env ]; then
    echo "⚠️  No .env file found. Creating from example..."
    echo "GOOGLE_CLOUD_PROJECT=your-project-id" > backend/.env
    echo "GEMINI_API_KEY=your-gemini-key" >> backend/.env
    echo "GOOGLE_CLOUD_LOCATION=us-central1" >> backend/.env
    echo "GCS_BUCKET_NAME=lexguard-uploads" >> backend/.env
    echo ""
    echo "❗ Please edit backend/.env with your actual credentials!"
    echo ""
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r backend/requirements.txt -q

# Run the server
echo "🚀 Starting FastAPI server on http://localhost:8080"
echo ""
cd "$(dirname "$0")"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
