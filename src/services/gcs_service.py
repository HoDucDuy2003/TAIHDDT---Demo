"""
Google Cloud Storage Service
Upload invoice data (header + detail JSON) to GCS
"""

import json
import os
from typing import Any, Dict, List

from google.cloud import storage

from ..core import config


class GCSService:
    """Service upload file lên Google Cloud Storage"""

    def __init__(self, credentials_path: str = "", bucket_name: str = ""):
        creds = credentials_path or config.GCP_CREDENTIALS_PATH
        self.bucket_name = bucket_name or config.GCS_BUCKET_NAME

        if not self.bucket_name:
            raise ValueError(
                "Chưa cấu hình GCS_BUCKET_NAME. Kiểm tra deploy.sh có dòng "
                "`export GCS_BUCKET_NAME=\"...\"` hoặc set env var thủ công."
            )

        # Use service account JSON if exists, otherwise use Application Default Credentials
        if creds and os.path.exists(creds):
            self.client = storage.Client.from_service_account_json(creds)
        else:
            self.client = storage.Client(project=config.GCP_PROJECT_ID)

        self.bucket = self.client.bucket(self.bucket_name)

    @staticmethod
    def _build_gcs_path(
        mst: str,
        invoice_type: str,
        start_date: str,
        end_date: str,
        file_label: str,
    ) -> str:
        """
        Build GCS object path.

        Returns:
            e.g. invoices/0102233518/purchase/2026/04/header_01042026_13042026.json
        """
        # start_date comes as dd/mm/yyyy — extract year/month
        parts = start_date.replace("/", "")
        end_clean = end_date.replace("/", "")

        # Extract year/month from dd/mm/yyyy
        date_parts = start_date.split("/")
        year = date_parts[2] if len(date_parts) == 3 else "unknown"
        # month = date_parts[1] if len(date_parts) == 3 else "unknown"

        return f"invoices/{mst}/{invoice_type}/{year}/{file_label}_{parts}_{end_clean}.json"

    def blob_exists(self, gcs_path: str) -> bool:
        """Check xem file đã tồn tại trên GCS chưa."""
        return self.bucket.blob(gcs_path).exists()

    def upload_json(
        self,
        data: Any,
        gcs_path: str,
        overwrite: bool = False,
    ) -> str:
        """
        Upload JSON data to GCS.

        Args:
            data: Data to serialize as JSON
            gcs_path: Destination path in bucket
            overwrite: True = ghi đè nếu đã tồn tại, False = skip

        Returns:
            GCS URI (gs://bucket/path), or empty string if skipped
        """
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"

        if not overwrite and self.blob_exists(gcs_path):
            print(f"⏭️  Already exists, skipped: {gcs_uri}")
            return gcs_uri

        blob = self.bucket.blob(gcs_path)
        # BigQuery expects NDJSON (one JSON object per line) for load jobs.
        if isinstance(data, list):
            json_str = "\n".join(json.dumps(row, ensure_ascii=False) for row in data)
        else:
            json_str = json.dumps(data, ensure_ascii=False)
        blob.upload_from_string(json_str, content_type="application/json")

        print(f"☁️  Uploaded: {gcs_uri}")
        return gcs_uri

    def upload_invoices(
        self,
        invoice_dicts: List[Dict[str, Any]],
        mst: str,
        invoice_type: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, str]:
        """
        Upload header + detail JSON to GCS.

        Splits invoice_dicts into:
          - header JSON (invoice info without items)
          - detail JSON (invoice_id + items)

        Args:
            invoice_dicts: List of invoice dicts (from Invoice.to_dict())
            mst: Ma so thue
            invoice_type: "sold" / "purchase"
            start_date: dd/mm/yyyy
            end_date: dd/mm/yyyy

        Returns:
            Dict with keys: header_uri, detail_uri
        """
        # Split into header + detail
        headers = []
        details = []

        for inv in invoice_dicts:
            # Header = everything except items
            header = {k: v for k, v in inv.items() if k != "items"}
            headers.append(header)

            # Detail = invoice_id + each item
            invoice_id = inv.get("invoice_id", "")
            for item in inv.get("items", []):
                detail_row = {"invoice_id": invoice_id, **item}
                details.append(detail_row)

        # Build paths
        header_path = self._build_gcs_path(mst, invoice_type, start_date, end_date, "header")
        detail_path = self._build_gcs_path(mst, invoice_type, start_date, end_date, "detail")

        # Upload
        header_uri = self.upload_json(headers, header_path)
        detail_uri = self.upload_json(details, detail_path) if details else ""

        return {"header_uri": header_uri, "detail_uri": detail_uri}
