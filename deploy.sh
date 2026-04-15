#!/bin/bash
# ============================================================
# GCP Configuration for Invoice System
# Usage: source deploy.sh
# ============================================================

# ================= CONFIG =================
export GCP_PROJECT_ID="minhhai"
export GCS_BUCKET_NAME="invoices-tax-portal-vn"
export BQ_DATASET="invoices_tax_portal"
export GCP_REGION="asia-southeast1"
export GOOGLE_APPLICATION_CREDENTIALS="credentials/sa-key.json"

SA_NAME="invoice-loader"
SA_EMAIL="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
SA_ROLES=(
  "roles/storage.objectAdmin"
  "roles/bigquery.dataEditor"
  "roles/bigquery.jobUser"
)

# ================= SET PROJECT =================
echo "🔧 Setting project: $GCP_PROJECT_ID"
gcloud config set project "$GCP_PROJECT_ID" 2>/dev/null

# ================= SERVICE ACCOUNT =================
echo "🔑 Setting up service account: $SA_EMAIL"

# Create SA if missing (idempotent)
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
  echo "  Service account already exists"
else
  gcloud iam service-accounts create "$SA_NAME" \
    --project="$GCP_PROJECT_ID" \
    --display-name="Invoice Loader SA" \
    && echo "  Created service account"
fi

# Grant roles (add-iam-policy-binding is idempotent)
for ROLE in "${SA_ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE" \
    --condition=None \
    --quiet >/dev/null 2>&1 \
    && echo "  Granted $ROLE"
done

# Download key only if file missing (tránh tạo key mới mỗi lần chạy)
mkdir -p credentials
if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  echo "  Key file đã tồn tại: $GOOGLE_APPLICATION_CREDENTIALS"
else
  echo "  Tạo mới key file..."
  gcloud iam service-accounts keys create "$GOOGLE_APPLICATION_CREDENTIALS" \
    --iam-account="$SA_EMAIL" \
    && echo "  Saved key: $GOOGLE_APPLICATION_CREDENTIALS"
fi

# ================= CLOUD STORAGE =================
echo "📦 Creating GCS bucket..."
gsutil mb -p "$GCP_PROJECT_ID" -l "$GCP_REGION" "gs://${GCS_BUCKET_NAME}" 2>/dev/null || echo "  Bucket already exists"

# Create folder structure
echo "" | gsutil cp - "gs://${GCS_BUCKET_NAME}/invoices/.gitkeep" 2>/dev/null || true

# ================= BIGQUERY =================
echo "📊 Creating BigQuery dataset..."
bq --location="$GCP_REGION" mk --dataset "${GCP_PROJECT_ID}:${BQ_DATASET}" 2>/dev/null || echo "  Dataset already exists"

echo ""
echo "✅ Deploy complete!"
echo "   Project : $GCP_PROJECT_ID"
echo "   Bucket  : gs://$GCS_BUCKET_NAME"
echo "   Dataset : $BQ_DATASET"
echo "   Region  : $GCP_REGION"
echo "   SA      : $SA_EMAIL"
echo "   Key     : $GOOGLE_APPLICATION_CREDENTIALS"
