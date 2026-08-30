#!/bin/bash
set -e

echo "=================================================================="
echo " S.I.A. (SMART INSURANCE ASSISTANT) - GOOGLE CLOUD RUN DEPLOYMENT "
echo "=================================================================="

if [ -z "$GCP_PROJECT_ID" ]; then
    read -p "Enter your Google Cloud Project ID: " GCP_PROJECT_ID
fi

REGION="asia-south1"
SERVICE_NAME="sia-claims-assistant"

echo "[*] Enabling Google Cloud Run & Cloud Build APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project="$GCP_PROJECT_ID"

echo "[*] Building container image via Cloud Build..."
gcloud builds submit --tag "gcr.io/$GCP_PROJECT_ID/$SERVICE_NAME:latest" --project="$GCP_PROJECT_ID"

echo "[*] Deploying service to Google Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$GCP_PROJECT_ID/$SERVICE_NAME:latest" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --project="$GCP_PROJECT_ID"

echo "=================================================================="
echo " DEPLOYMENT COMPLETE! S.I.A. IS LIVE ON GOOGLE CLOUD RUN."
echo "=================================================================="
