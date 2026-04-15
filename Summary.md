# Tổng kết session 2026-04-15

Ghi lại toàn bộ bug đã fix, feature đã thêm, và config đã thay đổi khi chuyển từ **GCP free trial** sang **paid account**.

---

## 1. Bug fix

### 1.1. `IndexError: string index out of range` khi upload GCS
**File:** [src/core/config.py](src/core/config.py), [src/services/gcs_service.py](src/services/gcs_service.py), [src/services/bigquery_service.py](src/services/bigquery_service.py)

**Nguyên nhân:** `GCS_BUCKET_NAME` env var rỗng → `storage.Client.bucket("")` crash vì `name[0].isalnum()` trên chuỗi rỗng. Lý do env trống: user chạy `source deploy.sh` ở bash nhưng launch Python từ terminal khác → env không kế thừa.

**Fix:**
- Thêm `_load_deploy_sh_env()` trong [config.py](src/core/config.py) tự parse `export KEY="VALUE"` từ `deploy.sh` khi import (`os.environ.setdefault` — env thật vẫn ưu tiên).
- Thêm validation `ValueError` trong `GCSService.__init__` và `BigQueryService.__init__` nếu thiếu `bucket_name` / `project_id` → báo lỗi tiếng Việt thay vì traceback SDK khó hiểu.

### 1.2. `DefaultCredentialsError: File credentials/sa-key.json was not found`
**File:** [src/core/config.py](src/core/config.py)

**Nguyên nhân:** `_load_deploy_sh_env()` auto-set `GOOGLE_APPLICATION_CREDENTIALS` → `google.auth` đi tìm file không có trên free trial (SA key bị restricted).

**Fix:** Skip set biến này nếu file path không tồn tại → cho phép fallback sang ADC (`gcloud auth application-default login`).

### 1.3. ADC dùng nhầm tài khoản (Forbidden 403)
**Nguyên nhân:** `gcloud config set account` (CLI) và `gcloud auth application-default login` (Python SDK/ADC) là **2 credential store tách biệt**. User đổi account ở config nhưng ADC vẫn cache account cũ.

**Fix (bằng command):**
```bash
gcloud auth application-default revoke
gcloud auth application-default login
```

### 1.4. BigQuery load fail: `Start of array encountered without start of object`
**File:** [src/services/gcs_service.py](src/services/gcs_service.py), [src/services/bigquery_service.py](src/services/bigquery_service.py)

**Nguyên nhân:** Upload GCS dùng `json.dumps(data, indent=2)` (JSON array) nhưng BQ load yêu cầu **NDJSON** (1 object/dòng, không array wrapper).

**Fix:** Chuyển sang NDJSON format:
```python
ndjson = "\n".join(json.dumps(row, ensure_ascii=False) for row in data)
```

### 1.5. Field `processing_status` NULL trên BQ
**File:** [src/models/invoice.py](src/models/invoice.py), [src/utils/formatter.py](src/utils/formatter.py)

**Nguyên nhân:** Typo — key JSON là `"processing status"` (có space) nhưng BQ schema là `processing_status` → không map được.

**Fix:** Sửa 3 chỗ dùng sai key.

### 1.6. `value_tax` luôn = 0 ở BQ invoice_details
**Không phải bug** — API Vietnam tax portal không trả `tthue` ở item level (tax chỉ ở invoice level qua `tax_amount`). Mapping đã đúng.

**Khuyến nghị:** Khi báo cáo tổng thuế → SUM `tax_amount` từ `invoice_headers`, không phải SUM `value_tax` từ `invoice_details`.

---

## 2. Feature thêm mới

### 2.1. Field `invoice_type` phân biệt sold/purchase trong cùng bảng
**File:** [app_ui.py:783-784](app_ui.py#L783), [src/services/bigquery_service.py](src/services/bigquery_service.py) HEADER_SCHEMA

Inject `invoice_type` vào `invoice_dicts` sau khi build → tự động có trong GCS upload + BQ schema.

**Query mẫu:**
```sql
SELECT invoice_type, COUNT(*) FROM invoice_headers GROUP BY invoice_type
```

**Lưu ý:** Data cũ NULL ở cột này → phải drop table + backfill để có giá trị cho toàn bộ lịch sử.

### 2.2. Auto-provision service account trong `deploy.sh`
**File:** [deploy.sh](deploy.sh)

Thêm block tự động:
- Create SA `invoice-loader@PROJECT.iam.gserviceaccount.com` (idempotent — describe trước, create sau)
- Grant 3 roles: `storage.objectAdmin`, `bigquery.dataEditor`, `bigquery.jobUser`
- Download key vào `credentials/sa-key.json` (chỉ tạo nếu file chưa có — tránh generate N key mỗi lần source)

### 2.3. Chuyển dedup từ Python sang MERGE SQL
**File:** [src/services/bigquery_service.py](src/services/bigquery_service.py)

**Trước (free trial):** Query all invoice_ids → filter Python → re-upload GCS → WRITE_APPEND load.
**Sau (paid):** Load GCS → temp table → MERGE vào main → drop temp.

| | Python dedup | MERGE |
|---|---|---|
| Query BQ trước | SELECT all IDs | Không |
| Filter ở đâu | Python (client) | BQ (server) |
| Re-upload GCS | Có | Không |
| Scale | Kém (>100K rows) | Tốt |

---

## 3. Config changes

### 3.1. `deploy.sh` (project mới paid account)
```bash
export GCP_PROJECT_ID="minhhai"
export GCS_BUCKET_NAME="invoices-tax-portal-vn"   # phải lowercase + globally unique
export BQ_DATASET="invoices"
export GCP_REGION="asia-southeast1"
export GOOGLE_APPLICATION_CREDENTIALS="credentials/sa-key.json"
```

### 3.2. Workflow migration free trial → paid
1. Upgrade billing trên project mới
2. Set budget alert (GCP Console → Billing → Budgets)
3. Update `deploy.sh` với project/bucket mới
4. `source deploy.sh` → auto-tạo SA + key + bucket + dataset
5. Drop tables cũ (nếu cần backfill `invoice_type`):
   ```bash
   bq rm -f -t PROJECT:invoices.invoice_headers
   bq rm -f -t PROJECT:invoices.invoice_details
   ```
6. Chạy app → fetch + upload lại

---

## 4. Files modified

| File | Thay đổi |
|---|---|
| [src/core/config.py](src/core/config.py) | `_load_deploy_sh_env()` auto-load, skip missing cred file |
| [src/services/gcs_service.py](src/services/gcs_service.py) | Validate bucket_name, NDJSON format |
| [src/services/bigquery_service.py](src/services/bigquery_service.py) | Validate project_id, `invoice_type` schema, MERGE dedup, comment Python dedup |
| [src/models/invoice.py](src/models/invoice.py) | Fix key `processing status` → `processing_status` |
| [src/utils/formatter.py](src/utils/formatter.py) | Fix label + column list cho `processing_status` |
| [app_ui.py](app_ui.py) | Inject `invoice_type`, bỏ param `invoice_dicts` khi gọi BQ |
| [deploy.sh](deploy.sh) | Auto-create SA + roles + key, idempotent |

---

## 5. Lưu ý sau session

- **Trước khi chạy nhiều query paid:** set budget alert 10$ để tránh bill sốc.
- **Best practice query:** dùng `SELECT col1, col2` thay vì `SELECT *` để tiết kiệm scan cost ($6.25/TB).
- **SA key security:** `credentials/` đã nằm trong `.gitignore`, không commit key file.
- **Rollback free trial:** code Python dedup vẫn giữ dạng comment trong `bigquery_service.py` — uncomment lại nếu cần.
