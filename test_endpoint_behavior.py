"""
TEST
"""

from numpy import iterable
import json

from src.core import config
from src.services import InvoiceService
from src.utils import DataFormatter, FileHandler, setup_logger



def main():
    """Hàm main chính"""
    
    # Setup logger
    logger = setup_logger(log_file=True, console=True)
    
    print("=" * 80)
    print("🏦 HỆ THỐNG HÓA ĐƠN ĐIỆN TỬ v2.0")
    print("=" * 80)
    print()
    
    # Validate config
    if not config.validate():
        print("⚠️  CẢNH BÁO: Token chưa được cập nhật!")
        return
    
    # Khởi tạo services
    logger.info("Khởi tạo services...")
    service = InvoiceService()
    file_handler = FileHandler()
    
    # ========== LẤY HÓA ĐƠN KÈM CHI TIẾT ==========
    logger.info("Bắt đầu lấy hóa đơn...")
    
    START_DATE = "01/01/2026"
    END_DATE = "31/01/2026"
    INVOICE_TYPE = "purchase"

    # Trang 1
    result_p1 = service.get_all_invoices_with_details(
        invoice_type=INVOICE_TYPE,
        start_date = START_DATE,
        end_date = END_DATE,
        include_pos=False,
        size=50)
    

    #Trang 2
    # result_p2 = service.get_invoices(
    #     invoice_type=INVOICE_TYPE,
    #     start_date = START_DATE,
    #     end_date = END_DATE,
    #     include_pos=False,
    #     ttxly_filter=[5],
    #     page=2,
    #     size=15)
    # with open("page2.json", "w", encoding="utf-8") as f:
    #     json.dump(result_p2, f, ensure_ascii=False, indent=2)




if __name__ == "__main__":
    main()