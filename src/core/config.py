"""
Core Configuration Module
Quản lý tất cả cấu hình của hệ thống
"""

import os
import re
from pathlib import Path
from typing import Optional


def _load_deploy_sh_env() -> None:
    """Load `export KEY="VALUE"` dòng từ deploy.sh vào os.environ.

    Env var đã set sẵn sẽ được ưu tiên (setdefault). Giúp app chạy được từ
    PowerShell/cmd/IDE mà không cần `source deploy.sh` trong cùng shell.
    """
    deploy_path = Path(__file__).resolve().parents[2] / "deploy.sh"
    if not deploy_path.exists():
        return

    pattern = re.compile(r'^\s*export\s+([A-Z_][A-Z0-9_]*)=(.+?)\s*$')
    project_root = deploy_path.parent
    for line in deploy_path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        key, raw_value = match.group(1), match.group(2).strip()
        # Strip surrounding quotes
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in ('"', "'"):
            raw_value = raw_value[1:-1]
        # Skip GOOGLE_APPLICATION_CREDENTIALS if file missing — let google.auth
        # fall back to ADC (`gcloud auth application-default login`). Free trial
        # accounts can't download service account JSON keys.
        if key == "GOOGLE_APPLICATION_CREDENTIALS":
            cred_path = Path(raw_value)
            if not cred_path.is_absolute():
                cred_path = project_root / cred_path
            if not cred_path.exists():
                continue
        os.environ.setdefault(key, raw_value)


_load_deploy_sh_env()


class Config:
    """Cấu hình hệ thống"""
    
    # ================= AUTHENTICATION =================
    TOKEN: str = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIwMTAyMjMzNTE4IiwidHlwZSI6MiwiZXhwIjoxNzc2MzE1NjI0LCJpYXQiOjE3NzYyMjkyMjR9.HYbv1bN0AK30tOUhgZ3R29A4PAIAEJtLX31h75VAlwHRJ3bvw8RQvH7ZHvULfmfszGpfx6mbYutkSEwBOqRmcg"
    
    # ================= API ENDPOINTS =================
    BASE_URL: str = "https://hoadondientu.gdt.gov.vn:30000"
    DOMAIN: str = "https://hoadondientu.gdt.gov.vn"
    
    # ================= DEFAULT SETTINGS =================
    DEFAULT_PAGE_SIZE: int = 50
    DEFAULT_TIMEOUT: int = 30
    DEFAULT_DELAY: float = 1.0  # seconds
    
    # ================= INVOICE TYPES =================
    INVOICE_TYPE_SOLD: str = "sold"
    INVOICE_TYPE_PURCHASE: str = "purchase"
    
    # ================= REFERER PATHS =================
    REFERER_PATHS = {
        "sold": "tra-cuu/tra-cuu-hoa-don-ban-ra",
        "purchase": "tra-cuu/tra-cuu-hoa-don-mua-vao"
    }
    
    # ================= FILE PATHS =================
    DATA_DIR: str = "data"
    LOG_DIR: str = "logs"

    # ================= GCP =================
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    BQ_DATASET: str = os.getenv("BQ_DATASET", "invoices")
    GCP_CREDENTIALS_PATH: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials/sa-key.json")

    # ================= LOGGING =================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    

    def get_token(self) -> str:
        """Lấy TOKEN, ưu tiên từ environment variable"""
        return os.getenv("INVOICE_TOKEN", self.TOKEN)
    
    def validate(self) -> bool:
        """Kiểm tra cấu hình hợp lệ"""
        if self.get_token() == "":
            return False
        return True


# Singleton instance
config = Config()
