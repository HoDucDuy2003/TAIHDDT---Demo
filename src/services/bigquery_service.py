"""
BigQuery Service
Load invoice data from GCS into BigQuery tables
"""

import os
from typing import Dict
from google.cloud import bigquery

from ..core import config


# Schema for invoice_headers table
HEADER_SCHEMA = [
    bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("invoice_type", "STRING"),
    bigquery.SchemaField("invoice_template", "STRING"),
    bigquery.SchemaField("invoice_serial", "STRING"),
    bigquery.SchemaField("invoice_number", "STRING"),
    bigquery.SchemaField("invoice_date", "STRING"),
    bigquery.SchemaField("invoice_currency", "STRING"),
    bigquery.SchemaField("lookup_code", "STRING"),
    bigquery.SchemaField("seller_tax_code", "STRING"),
    bigquery.SchemaField("seller_name", "STRING"),
    bigquery.SchemaField("seller_address", "STRING"),
    bigquery.SchemaField("seller_phone", "STRING"),
    bigquery.SchemaField("buyer_name", "STRING"),
    bigquery.SchemaField("buyer_tax_code", "STRING"),
    bigquery.SchemaField("buyer_address", "STRING"),
    bigquery.SchemaField("buyer_phone", "STRING"),
    bigquery.SchemaField("total_before_tax", "FLOAT"),
    bigquery.SchemaField("tax_amount", "FLOAT"),
    bigquery.SchemaField("total_amount", "FLOAT"),
    bigquery.SchemaField("payment_method", "STRING"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("processing_status", "STRING"),
    bigquery.SchemaField("note", "STRING"),
]

# Schema for invoice_details table
DETAIL_SCHEMA = [
    bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("id_detail", "STRING"),
    bigquery.SchemaField("stt", "INTEGER"),
    bigquery.SchemaField("name", "STRING"),
    bigquery.SchemaField("unit", "STRING"),
    bigquery.SchemaField("quantity", "FLOAT"),
    bigquery.SchemaField("unit_price", "FLOAT"),
    bigquery.SchemaField("tax_rate", "FLOAT"),
    bigquery.SchemaField("type_tax_rate", "STRING"),
    bigquery.SchemaField("discount", "FLOAT"),
    bigquery.SchemaField("value_notax", "FLOAT"),
    bigquery.SchemaField("value_tax", "FLOAT"),
]


class BigQueryService:
    """Service load data từ GCS vào BigQuery"""

    def __init__(self, credentials_path: str = "", project_id: str = ""):
        creds = credentials_path or config.GCP_CREDENTIALS_PATH
        self.project_id = project_id or config.GCP_PROJECT_ID
        self.dataset = config.BQ_DATASET

        if not self.project_id:
            raise ValueError(
                "Chưa cấu hình GCP_PROJECT_ID. Kiểm tra deploy.sh có dòng "
                "`export GCP_PROJECT_ID=\"...\"` hoặc set env var thủ công."
            )

        # Use service account JSON if exists, otherwise use Application Default Credentials
        if creds and os.path.exists(creds):
            self.client = bigquery.Client.from_service_account_json(creds, project=self.project_id)
        else:
            self.client = bigquery.Client(project=self.project_id)

    def _ensure_table(self, table_name: str, schema: list):
        """Tạo table nếu chưa tồn tại."""
        table_id = f"{self.project_id}.{self.dataset}.{table_name}"
        table = bigquery.Table(table_id, schema=schema)
        self.client.create_table(table, exists_ok=True)

    # ------------------------------------------------------------------ #
    #  DEDUP VỚI MERGE (paid account)
    # ------------------------------------------------------------------ #
    def _load_from_gcs_dedup_merge(self, gcs_uri, table_name, schema, dedup_key="invoice_id"):
        """
        Flow: GCS → temp table → MERGE vào main table (skip existing invoice_id)
        Yêu cầu: BigQuery on-demand/reserved (không hỗ trợ free trial sandbox)
        """
        main_table = f"{self.project_id}.{self.dataset}.{table_name}"
        temp_table = f"{self.project_id}.{self.dataset}._temp_{table_name}"
    
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            ignore_unknown_values=True,
        )
        load_job = self.client.load_table_from_uri(gcs_uri, temp_table, job_config=job_config)
        load_job.result()
    
        columns = ", ".join(f.name for f in schema)
        source_columns = ", ".join(f"s.{f.name}" for f in schema)
        merge_sql = f"""
        MERGE `{main_table}` AS t
        USING `{temp_table}` AS s
        ON t.{dedup_key} = s.{dedup_key}
        WHEN NOT MATCHED THEN
            INSERT ({columns}) VALUES ({source_columns})
        """
        merge_job = self.client.query(merge_sql)
        merge_job.result()
        new_rows = merge_job.num_dml_affected_rows or 0
        self.client.delete_table(temp_table, not_found_ok=True)
        return new_rows

    # ------------------------------------------------------------------ #
    #  DEDUP VỚI PYTHON (free trial — giữ lại phòng khi cần rollback)
    # ------------------------------------------------------------------ #
    # def _get_existing_ids(self, table_name: str) -> set:
    #     """Query tất cả invoice_id đã có trong table."""
    #     table_id = f"{self.project_id}.{self.dataset}.{table_name}"
    #     try:
    #         query = f"SELECT DISTINCT invoice_id FROM `{table_id}`"
    #         rows = self.client.query(query).result()
    #         return {row.invoice_id for row in rows}
    #     except Exception:
    #         return set()
    #
    # def _upload_deduped_json(self, data: list, gcs_uri: str):
    #     """Upload deduped JSON lên GCS (ghi đè file cũ)."""
    #     import json
    #     from google.cloud import storage as gcs_storage
    #
    #     bucket_name = gcs_uri.replace("gs://", "").split("/")[0]
    #     blob_path = "/".join(gcs_uri.replace("gs://", "").split("/")[1:])
    #
    #     if config.GCP_CREDENTIALS_PATH and os.path.exists(config.GCP_CREDENTIALS_PATH):
    #         gcs_client = gcs_storage.Client.from_service_account_json(config.GCP_CREDENTIALS_PATH)
    #     else:
    #         gcs_client = gcs_storage.Client(project=self.project_id)
    #
    #     bucket = gcs_client.bucket(bucket_name)
    #     blob = bucket.blob(blob_path)
    #     ndjson = "\n".join(json.dumps(row, ensure_ascii=False) for row in data)
    #     blob.upload_from_string(ndjson, content_type="application/json")

    def load_invoices_from_gcs(
        self,
        header_uri: str,
        detail_uri: str = "",
    ) -> Dict[str, int]:
        """
        Load header + detail vào BigQuery với dedup bằng MERGE (paid account).

        Flow:
        1. Load GCS → temp table (WRITE_TRUNCATE)
        2. MERGE temp → main (skip existing invoice_id)
        3. Drop temp table

        Args:
            header_uri: GCS URI cho header JSON
            detail_uri: GCS URI cho detail JSON
        """
        self._ensure_table("invoice_headers", HEADER_SCHEMA)
        self._ensure_table("invoice_details", DETAIL_SCHEMA)

        result = {}
        header_rows = self._load_from_gcs_dedup_merge(
            header_uri, "invoice_headers", HEADER_SCHEMA
        )
        result["invoice_headers"] = header_rows
        print(f"📊 BigQuery invoice_headers: +{header_rows} new rows")

        if detail_uri:
            detail_rows = self._load_from_gcs_dedup_merge(
                detail_uri, "invoice_details", DETAIL_SCHEMA
            )
            result["invoice_details"] = detail_rows
            print(f"📊 BigQuery invoice_details: +{detail_rows} new rows")

        return result
