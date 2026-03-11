"""
Core Configuration Module
Quản lý tất cả cấu hình của hệ thống
"""

import os
from typing import Optional


class Config:
    """Cấu hình hệ thống"""
    
    # ================= AUTHENTICATION =================
    TOKEN: str = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIwMTAyMjMzNTE4IiwidHlwZSI6MiwiZXhwIjoxNzczMjgwNzc4LCJpYXQiOjE3NzMxOTQzNzh9.QoXmMxOoYtcDY7eGIYDBgxEe-Vj1rduB3KbSzzlIMjRzLxcYpzLiAraG0zgGXtzJj6RYpT1yLckkEdg5ZoSrDw"
    
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
