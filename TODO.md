# TODO: Push Data to BigQuery via Cloud Storage

## Architecture
```
[App UI] → [Save locally] → [Upload to GCS] → [Load to BigQuery]
```

## Implementation Steps

- [ ] **Step 1: deploy.sh** — Set env vars: GCP_PROJECT_ID, GCS_BUCKET_NAME, BQ_DATASET, GOOGLE_APPLICATION_CREDENTIALS
- [ ] **Step 2: config.py** — Add GCP settings that read from env vars
- [ ] **Step 3: gcs_service.py** — Upload JSON to GCS with folder structure `gs://bucket/invoices/{mst}/{type}/{year}/{month}/`
- [ ] **Step 4: bigquery_service.py** — Load from GCS URI to BigQuery tables (invoice_headers + invoice_details)
- [ ] **Step 5: app_ui.py** — Add "Upload to Cloud" button to trigger upload + load
- [ ] **Step 6: .gitignore** — Ignore `credentials/` folder

## BigQuery Table Structure

### Dataset: `invoices`

### Table: `invoice_headers`
- invoice_id (STRING, PK)
- invoice_template, invoice_serial, invoice_number, invoice_date
- invoice_type ("sold" / "purchase")
- seller_tax_code, seller_name, seller_address
- buyer_tax_code, buyer_name, buyer_address
- total_before_tax, tax_amount, total_amount
- payment_method, status, processing_status, note

### Table: `invoice_details`
- invoice_id (STRING, FK → invoice_headers)
- stt, name, unit, quantity, unit_price
- tax_rate, value_notax, value_tax

## GCS Folder Structure
```
gs://bucket/invoices/{mst}/{type}/{year}/{month}/header_{start}_{end}.json
gs://bucket/invoices/{mst}/{type}/{year}/{month}/detail_{start}_{end}.json
```

## Future: Automation
- GCS event trigger → Cloud Function → auto load to BigQuery on file upload
