"""
Invoice Configuration
Cấu hình endpoint và ttxly cho từng loại hóa đơn

Quy tắc endpoint:
- /query     : Hóa đơn thường (non-POS)
                + Purchase : ttxly = 5, 6
                + Sold     : ttxly = 0, 1, 2, 3, 4, 5, 6, 7
- /sco-query : Máy tính tiền (POS), ttxly = 8
"""
from enum import Enum
from typing import Dict, List, Optional

class EndpointType(Enum):
    NORMAL = "query"   # Hóa đơn thường
    POS = "sco-query"  # Máy tính tiền

class InvoiceConfig:
    """Cấu hình cho các loại hóa đơn"""
    
    # ttxly hóa đơn thường theo invoice_type
    NORMAL_STATUSES: Dict[str, List[int]] = {
        "purchase": [5, 6],
        "sold":     [0, 1, 2, 3, 4, 5, 6, 7],
    }
    
    # ttxly máy tính tiền (dùng chung cho cả purchase và sold)
    POS_STATUS: int = 8
    
    @staticmethod
    def get_normal_statuses(invoice_type: str) -> List[int]:
        """
        Lấy danh sách ttxly hóa đơn thường theo loại hóa đơn.

        Args:
            invoice_type: "sold" hoặc "purchase"

        Returns:
            List ttxly, ví dụ [5, 6] hoặc [0,1,2,3,4,5,6,7]
        """
        return InvoiceConfig.NORMAL_STATUSES.get(invoice_type, [])

    @staticmethod
    def is_pos_status(ttxly: Optional[int]) -> bool:
        return ttxly == InvoiceConfig.POS_STATUS

    @staticmethod
    def get_endpoint(is_pos: bool, path: str = "") -> str:
        """
        Trả về đường dẫn endpoint theo loại hóa đơn.

        Args:
            is_pos: True → /sco-query, False → /query
            path  : phần path thêm vào sau endpoint gốc

        Returns:
            Ví dụ: "/query/invoices/purchase"
        """
        base = EndpointType.POS.value if is_pos else EndpointType.NORMAL.value
        return f"/{base}/{path}" if path else f"/{base}"