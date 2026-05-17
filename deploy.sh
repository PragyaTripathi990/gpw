#!/bin/bash
# =============================================================
# LexGuard — Deploy to Google Cloud Run
# =============================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$DEFAULT_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
BACKEND_SERVICE="${BACKEND_SERVICE:-lexguard-api}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-lexguard-web}"
UPLOAD_BUCKET="lexguard-uploads-${PROJECT_ID}"

echo "LexGuard deployment"
echo "==================="
echo "Project: ${PROJECT_ID:-<unset>}"
echo "Region:  $REGION"
echo ""

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT is not set and gcloud has no active project."
  exit 1
fi

echo "Setting gcloud project..."
gcloud config set project "$PROJECT_ID"

echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  documentai.googleapis.com \
  vision.googleapis.com \
  translate.googleapis.com \
  language.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com

echo "Ensuring upload bucket exists..."
gcloud storage buckets create "gs://${UPLOAD_BUCKET}" --location="$REGION" >/dev/null 2>&1 || true

BACKEND_ENV_VARS="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GCS_BUCKET_NAME=${UPLOAD_BUCKET}"
BACKEND_SECRET_FLAGS=()

if gcloud secrets describe gemini-api-key --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "Using Secret Manager secret: gemini-api-key"
  BACKEND_SECRET_FLAGS=(--set-secrets "GEMINI_API_KEY=gemini-api-key:latest")
elif [[ -n "${GEMINI_API_KEY:-}" ]]; then
  echo "Using GEMINI_API_KEY from the current shell environment"
  BACKEND_ENV_VARS="${BACKEND_ENV_VARS},GEMINI_API_KEY=${GEMINI_API_KEY}"
else
  echo "No Gemini secret found. Backend will still deploy and use deterministic fallback mode."
fi

echo "Deploying backend to Cloud Run..."
cd "${ROOT_DIR}/backend"
gcloud run deploy "$BACKEND_SERVICE" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="$BACKEND_ENV_VARS" \
  "${BACKEND_SECRET_FLAGS[@]}" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10

BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --region "$REGION" --format='value(status.url)')"
echo "Backend URL: $BACKEND_URL"

echo "Deploying frontend to Cloud Run..."
cd "${ROOT_DIR}/frontend"
gcloud run deploy "$FRONTEND_SERVICE" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-build-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 120 \
  --min-instances 0 \
  --max-instances 3

FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --format='value(status.url)')"
echo "Frontend URL: $FRONTEND_URL"

echo "Updating backend with explicit frontend origin..."
cd "${ROOT_DIR}/backend"
gcloud run services update "$BACKEND_SERVICE" \
  --region "$REGION" \
  --update-env-vars="ADDITIONAL_ALLOWED_ORIGINS=${FRONTEND_URL}"

echo ""
echo "=============================================="
echo "LexGuard deployed successfully"
echo "=============================================="
echo "Backend API: $BACKEND_URL"
echo "Frontend:    $FRONTEND_URL"
echo "=============================================="
