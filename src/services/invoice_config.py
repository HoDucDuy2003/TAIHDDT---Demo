"""
Invoice Configuration
Cấu hình ttxly cho từng loại hóa đơn

LƯU Ý: 
- Endpoint /query: Lấy TẤT CẢ trừ POS (không cần filter ttxly)
- Endpoint /sco-query: Chỉ lấy POS (ttxly=8)
- Config này chỉ dùng để hiển thị message, KHÔNG dùng để filter API
"""
from enum import Enum
from typing import Dict, List, Any

class EndpointType(Enum):
    NORMAL = "query"   # Hóa đơn thường
    POS = "sco-query"  # Máy tính tiền

class InvoiceConfig:
    """Cấu hình cho các loại hóa đơn"""
    
    # Cấu hình ttxly cho Purchase
    PURCHASE_CONFIG = {
        "non_pos_statuses": [5, 6],
        "pos_statuses": [8],
        "status_msg": "5, 6"
    }
    
    # Cấu hình ttxly cho Sold
    SOLD_CONFIG = {
        "non_pos_statuses": [0, 1, 2, 3, 4, 5, 6, 7],
        "pos_statuses": [8],
        "status_msg": "0-7"
    }
    
    @staticmethod
    def get_default_statuses(invoice_type: str) -> Dict[str, Any]:
        if invoice_type == "purchase":
            return InvoiceConfig.PURCHASE_CONFIG.copy()
        else:  # sold
            return InvoiceConfig.SOLD_CONFIG.copy()
    
    @staticmethod
    def is_pos_status(status: int) -> bool:
        return status == 8
    

    @staticmethod
    def get_normal_invoice(path: str = "") -> str:
        return f"/query/{path}"
    

    @staticmethod
    def get_pos_invoice(path: str = "") -> str:
        return f"/sco-query/{path}"
    

    @staticmethod
    def split_statuses(statuses: List[int]) -> tuple:
        pos_statuses = [s for s in statuses if InvoiceConfig.is_pos_status(s)]
        non_pos_statuses = [s for s in statuses if not InvoiceConfig.is_pos_status(s)]
        return pos_statuses, non_pos_statuses