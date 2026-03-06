"""
Main Entry Point
Chạy hệ thống hóa đơn điện tử
"""

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
    
    START_DATE = "01/02/2026"
    END_DATE = "28/02/2026"
    INVOICE_TYPE = "purchase"

    result = service.get_all_invoices_with_details(
        invoice_type=INVOICE_TYPE,
        start_date=START_DATE,
        end_date=END_DATE,
        size=50,
        return_models=False  # Trả về Invoice objects
    )
    
    if result.get("success"):
        invoices = result["all_invoices_with_details"]
        summary = result["summary"]
        
        # In thống kê tổng hợp
        print(f"\n📊 TỔNG KẾT:")
        print(f"  • Tổng số hóa đơn: {summary.get('total_invoices', 0)}")
        print(f"  • Số trang đã lấy: {summary.get('pages_fetched', 0)}")
        if 'details_success' in summary:
            print(f"  • Chi tiết thành công: {summary['details_success']}")
            print(f"  • Chi tiết thất bại: {summary['details_failed']}")
        
        # Lưu file JSON
        print(f"\n💾 Đang lưu {len(invoices)} hóa đơn...")
        json_file = file_handler.save_to_json(invoices, invoice_type=INVOICE_TYPE)
        
        # Chuyển Invoice objects thành dicts
        # invoices_as_dicts = [invoice.to_dict() for invoice in invoices]
        
        # # Lưu Excel với cột được chọn và đổi tên tiếng Việt - chỉ chạy được khi đã convert sang dict
        # excel_file = file_handler.save_to_excel(
        #     invoices_as_dicts,
        #     invoice_type=INVOICE_TYPE,
        #     start_date=START_DATE,
        #     end_date=END_DATE,
        #     selected_columns=DataFormatter.DEFAULT_EXPORT_COLUMNS,
        #     column_names=DataFormatter.VIETNAMESE_COLUMN_NAMES
        # )
        
        
        print(f"\n✅ HOÀN THÀNH!")
        print(f"📁 JSON: {json_file}")
        # print(f"📁 EXCEL: {excel_file}")



        print(f"📊 Tổng: {len(invoices)} hóa đơn")
        
        logger.info(f"Hoàn thành! Lấy được {len(invoices)} hóa đơn")
    else:
        error_msg = result.get('error', 'Unknown')
        print(f"\n❌ Lỗi: {error_msg}")
        print(f"💡 Chi tiết: {result.get('message', 'Không có thông tin')}")
        logger.error(f"Lỗi: {error_msg}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()