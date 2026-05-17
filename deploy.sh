#!/bin/bash
# =============================================================
# LexGuard — Deploy to Google Cloud
# =============================================================

set -e

echo "🛡️ LexGuard Deployment Script"
echo "=============================="

# CONFIGURATION — Update these!
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
REGION="us-central1"
BACKEND_SERVICE="lexguard-api"
FRONTEND_BUCKET="lexguard-frontend"

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# ----- Step 1: Set GCP Project -----
echo "📌 Setting GCP project..."
gcloud config set project $PROJECT_ID

# ----- Step 2: Enable APIs -----
echo "🔧 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    documentai.googleapis.com \
    vision.googleapis.com \
    translate.googleapis.com \
    language.googleapis.com \
    storage.googleapis.com \
    firestore.googleapis.com \
    bigquery.googleapis.com \
    aiplatform.googleapis.com

# ----- Step 3: Create GCS Bucket -----
echo "📦 Creating Cloud Storage bucket..."
gsutil mb -l $REGION gs://lexguard-uploads-$PROJECT_ID 2>/dev/null || echo "Bucket exists"

# ----- Step 4: Build & Deploy Backend to Cloud Run -----
echo "🚀 Building and deploying backend to Cloud Run..."
cd backend

gcloud run deploy $BACKEND_SERVICE \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GCS_BUCKET_NAME=lexguard-uploads-$PROJECT_ID" \
    --set-secrets="GEMINI_API_KEY=gemini-api-key:latest" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --min-instances 0 \
    --max-instances 10

# Get the backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)')
echo "✅ Backend deployed at: $BACKEND_URL"

cd ..

# ----- Step 5: Build & Deploy Frontend to Firebase -----
echo "🌐 Building and deploying frontend..."
cd frontend

# Set the backend URL for the frontend
echo "NEXT_PUBLIC_API_URL=$BACKEND_URL" > .env.local

npm run build

# Deploy to Firebase Hosting
firebase deploy --only hosting

cd ..

echo ""
echo "================================================"
echo "🎉 LexGuard deployed successfully!"
echo "================================================"
echo "Backend API: $BACKEND_URL"
echo "Frontend:    Check Firebase Hosting URL above"
echo "================================================"
