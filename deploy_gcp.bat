@echo off
echo ==================================================================
echo  S.I.A. (SMART INSURANCE ASSISTANT) - GOOGLE CLOUD RUN DEPLOYMENT
echo ==================================================================

if "%GCP_PROJECT_ID%"=="" (
    set /p GCP_PROJECT_ID="Enter your Google Cloud Project ID: "
)

set REGION=asia-south1
set SERVICE_NAME=sia-claims-assistant

echo [*] Target GCP Project: %GCP_PROJECT_ID%
echo [*] Target Region: %REGION%
echo [*] Service Name: %SERVICE_NAME%

echo [*] Enabling Google Cloud Run & Cloud Build APIs...
call gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project=%GCP_PROJECT_ID%

echo [*] Building and submitting container image via Cloud Build...
call gcloud builds submit --tag gcr.io/%GCP_PROJECT_ID%/%SERVICE_NAME%:latest --project=%GCP_PROJECT_ID%

echo [*] Deploying service to Google Cloud Run...
call gcloud run deploy %SERVICE_NAME% ^
    --image gcr.io/%GCP_PROJECT_ID%/%SERVICE_NAME%:latest ^
    --platform managed ^
    --region %REGION% ^
    --allow-unauthenticated ^
    --memory 1Gi ^
    --cpu 1 ^
    --min-instances 0 ^
    --max-instances 10 ^
    --project=%GCP_PROJECT_ID%

echo ==================================================================
echo  DEPLOYMENT COMPLETE! S.I.A. IS LIVE ON GOOGLE CLOUD RUN.
echo ==================================================================
