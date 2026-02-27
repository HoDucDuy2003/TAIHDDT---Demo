"""
Invoice Service
Business logic xử lý hóa đơn
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from ..core import config, APIClient
from ..models import Invoice
from .invoice_config import InvoiceConfig,EndpointType
from .invoice_helpers import InvoiceEndpointCaller, InvoiceResultMerger


class InvoiceService:
    """Service xử lý nghiệp vụ hóa đơn"""
    
    def __init__(self, api_client: Optional[APIClient] = None):
        """
        Khởi tạo service
        
        Args:
            api_client: API client instance
        """
        self.api_client = api_client or APIClient()
        self.endpoint_caller = InvoiceEndpointCaller(self.api_client)
    
    def get_invoices(
        self,
        invoice_type: str = "sold",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        size: Optional[int] = None,
        sort_by: str = "tdlap:desc",
        additional_filters: Optional[Dict[str, Any]] = None,
        include_processing_status: Optional[List[int]] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Lấy danh sách hóa đơn
        
        Args:
            invoice_type: "sold" hoặc "purchase"
            start_date: Ngày bắt đầu (dd/mm/yyyy)
            end_date: Ngày kết thúc (dd/mm/yyyy)
            page: Trang (bắt đầu từ 1)
            size: Số lượng mỗi trang
            sort_by: Cách sắp xếp
            additional_filters: Bộ lọc bổ sung
            include_processing_status: Danh sách trạng thái xử lý để lọc
                - None (default): Tự động lấy tất cả ttxly phù hợp
                    + Purchase: gọi /query (5,6) + /sco-query (8)
                    + Sold: gọi /query (0-7) + /sco-query (8)
                - [8]: Chỉ lấy máy tính tiền từ /sco-query
                - [5,6]: Chỉ lấy từ /query
                - []: Lấy tất cả từ /query (không filter)
            verbose: Có in log không
            
        Returns:
            Dict với keys: success, total, invoices, page, total_pages, has_next, has_prev
        """
        size = size or config.DEFAULT_PAGE_SIZE
        
        # Xử lý ngày mặc định
        if not end_date:
            end_date = datetime.now().strftime("%d/%m/%Y")
        
        if not start_date:
            start = datetime.now() - timedelta(days=30)
            start_date = start.strftime("%d/%m/%Y")
        
        if verbose:
            print(f"🔍 Đang tìm hóa đơn {invoice_type}...")
            print(f"📅 Từ {start_date} đến {end_date}")
            print(f"📄 Trang {page}, mỗi trang {size} hóa đơn\n")
        
        # CASE 1: Default behavior - gọi cả 2 endpoint
        if include_processing_status is None:
            return self._get_invoices_default(
                invoice_type=invoice_type,
                start_date=start_date,
                end_date=end_date,
                page=page,
                size=size,
                sort_by=sort_by,
                additional_filters=additional_filters,
                verbose=verbose
            )
        
        # CASE 2: Custom request với POS và non-POS
        pos_statuses, non_pos_statuses = InvoiceConfig.split_statuses(include_processing_status)
        
        if pos_statuses and non_pos_statuses:
            return self._get_invoices_mixed(
                invoice_type=invoice_type,
                start_date=start_date,
                end_date=end_date,
                page=page,
                size=size,
                sort_by=sort_by,
                pos_statuses=pos_statuses,
                non_pos_statuses=non_pos_statuses,
                additional_filters=additional_filters,
                verbose=verbose
            )
        
        # CASE 3 & 4: Chỉ POS hoặc chỉ non-POS
        return self._get_invoices_single_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            include_processing_status=include_processing_status,
            is_pos_only=bool(pos_statuses),
            additional_filters=additional_filters,
            verbose=verbose
        )
    
    def _get_invoices_default(
        self,
        invoice_type: str,
        start_date: str,
        end_date: str,
        page: int,
        size: int,
        sort_by: str,
        additional_filters: Optional[Dict[str, Any]],
        verbose: bool
    ) -> Dict[str, Any]:
        """
        Lấy hóa đơn với cấu hình mặc định (gọi cả 2 endpoint)
        """
        # Lấy cấu hình ttxly cho loại hóa đơn
        status_config = InvoiceConfig.get_default_statuses(invoice_type)
        non_pos_statuses = status_config["non_pos_statuses"]
        pos_statuses = status_config["pos_statuses"]
        status_msg = status_config["status_msg"]
        
        if verbose:
            print(f"ℹ️  Mặc định: Gọi /query (tất cả trừ POS) + /sco-query (ttxly=8)\n")
        
        # Bước 1: Gọi /query
        if verbose:
            print(f"[1/2] Lấy hóa đơn từ /query (tất cả trừ POS)...")
        
        result_normal = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            endpoint_type="query",
            include_processing_status=non_pos_statuses,
            additional_filters=additional_filters,
            verbose=verbose
        )
        
        # Bước 2: Gọi /sco-query
        if verbose:
            print(f"[2/2] Lấy hóa đơn từ /sco-query (ttxly = 8)...")
        
        result_pos = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            endpoint_type="sco-query",
            include_processing_status=pos_statuses,
            additional_filters=additional_filters,
            verbose=verbose
        )
        
        # Merge kết quả
        return InvoiceResultMerger.merge_results(
            result_normal=result_normal,
            result_pos=result_pos,
            page=page,
            size=size,
            verbose=verbose
        )
    
    def _get_invoices_mixed(
        self,
        invoice_type: str,
        start_date: str,
        end_date: str,
        page: int,
        size: int,
        sort_by: str,
        pos_statuses: List[int],
        non_pos_statuses: List[int],
        additional_filters: Optional[Dict[str, Any]],
        verbose: bool
    ) -> Dict[str, Any]:
        """
        Lấy hóa đơn có cả POS và non-POS (gọi 2 endpoint)
        """
        if verbose:
            print("🔄 Gọi 2 endpoint: /query + /sco-query\n")
        
        # Gọi /query cho non-POS
        result_normal = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            endpoint_type="query",
            include_processing_status=non_pos_statuses,
            additional_filters=additional_filters,
            verbose=verbose
        )
        
        # Gọi /sco-query cho POS
        result_pos = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            endpoint_type="sco-query",
            include_processing_status=pos_statuses,
            additional_filters=additional_filters,
            verbose=verbose
        )
        
        return InvoiceResultMerger.merge_results(
            result_normal=result_normal,
            result_pos=result_pos,
            page=page,
            size=size,
            verbose=verbose
        )
    
    def _get_invoices_single_endpoint(
        self,
        invoice_type: str,
        start_date: str,
        end_date: str,
        page: int,
        size: int,
        sort_by: str,
        include_processing_status: List[int],
        is_pos_only: bool,
        additional_filters: Optional[Dict[str, Any]],
        verbose: bool
    ) -> Dict[str, Any]:
        """
        Lấy hóa đơn từ 1 endpoint duy nhất
        """
        if is_pos_only:
            endpoint_type = "sco-query"
            if verbose:
                print("🖥️  Chỉ lấy từ máy tính tiền (/sco-query)\n")
        else:
            endpoint_type = "query"
            if verbose:
                print("📋 Chỉ lấy từ /query\n")
        
        result = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            endpoint_type=endpoint_type,
            include_processing_status=include_processing_status,
            additional_filters=additional_filters,
            verbose=verbose
        )
        
        if not result["success"]:
            return result
        
        # Extract invoices
        invoices, total = InvoiceResultMerger._extract_invoices(result["data"])
        total_pages = max(1, (total + size - 1) // size) if total > 0 else 1
        
        if verbose:
            print(f"✅ Thành công!")
            print(f"📈 Tổng: {total} | Lấy được: {len(invoices)} hóa đơn\n")
        
        return {
            "success": True,
            "total": total,
            "invoices": invoices,
            "page": page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    
    def get_invoice_detail(
        self,
        invoice_summary: Dict[str, Any],
        invoice_type: str,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Lấy chi tiết hóa đơn
        
        Args:
            invoice_summary: Dict hóa đơn tóm tắt
            invoice_type: "sold" hoặc "purchase"
            verbose: Có in log không
            
        Returns:
            Dict với keys: success, data
        """
        nbmst = invoice_summary.get("nbmst")
        khhdon = invoice_summary.get("khhdon")
        shdon = invoice_summary.get("shdon")
        khmshdon = invoice_summary.get("khmshdon")
        ttxly = invoice_summary.get("ttxly")
        
        if not all([nbmst, khhdon, shdon, khmshdon]):
            return {
                "success": False,
                "error": "Missing required parameters"
            }
        
        params = {
            "nbmst": nbmst,
            "khhdon": khhdon,
            "shdon": shdon,
            "khmshdon": khmshdon
        }
        
        if verbose:
            print(f"  📋 {khhdon}-{shdon}", end=" ")
        
        # Chọn endpoint dựa vào ttxly
        if InvoiceConfig.is_pos_status(ttxly):
            endpoint_detail = "/sco-query/invoices/detail"
        else:
            endpoint_detail = "/query/invoices/detail"
        
        result = self.api_client.get(
            endpoint=endpoint_detail,
            params=params,
            invoice_type=invoice_type
        )
        
        if result["success"]:
            if verbose:
                print("✓")
            return {
                "success": True,
                "data": result["data"]
            }
        else:
            if verbose:
                print("✗")
            return result
    
    def get_all_invoices(
        self,
        invoice_type: str = "sold",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        size: Optional[int] = None,
        max_pages: Optional[int] = None,
        delay: Optional[float] = None,
        include_processing_status: Optional[List[int]] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Lấy TẤT CẢ hóa đơn (tự động phân trang)
        
        Args:
            invoice_type: "sold" hoặc "purchase"
            start_date: Ngày bắt đầu
            end_date: Ngày kết thúc
            size: Số lượng mỗi trang
            max_pages: Giới hạn số trang
            delay: Delay giữa requests
            include_processing_status: Danh sách trạng thái xử lý để lọc 
            verbose: Có in log không
            
        Returns:
            Dict với keys: success, total, all_invoices, pages_fetched
        """
        size = size or config.DEFAULT_PAGE_SIZE
        delay = delay if delay is not None else config.DEFAULT_DELAY
        
        all_invoices = []
        page = 1
        
        while True:
            if verbose:
                print(f"{'='*60}")
                print(f"📄 TRANG {page}")
                print(f"{'='*60}")
            
            result = self.get_invoices(
                invoice_type=invoice_type,
                start_date=start_date,
                end_date=end_date,
                page=page,
                size=size,
                include_processing_status=include_processing_status,
                verbose=verbose
            )
            
            if not result["success"]:
                return result
            
            all_invoices.extend(result["invoices"])
            
            if not result.get("has_next"):
                break
            
            if max_pages and page >= max_pages:
                if verbose:
                    print(f"⚠️  Đạt giới hạn {max_pages} trang\n")
                break
            
            page += 1
            
            if delay > 0:
                time.sleep(delay)
        
        if verbose:
            print(f"\n🎉 Hoàn thành! Lấy được {len(all_invoices)} hóa đơn\n")
        
        return {
            "success": True,
            "total": len(all_invoices),
            "all_invoices": all_invoices,
            "pages_fetched": page
        }
    
    def get_all_invoices_with_details(
        self,
        invoice_type: str = "sold",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        size: Optional[int] = None,
        max_pages: Optional[int] = None,
        delay: Optional[float] = None,
        verbose: bool = True,
        include_processing_status: Optional[List[int]] = None,
        return_models: bool = False
    ) -> Dict[str, Any]:
        """
        Lấy TẤT CẢ hóa đơn KÈM CHI TIẾT
        
        Args:
            invoice_type: "sold" hoặc "purchase"
            start_date: Ngày bắt đầu
            end_date: Ngày kết thúc
            size: Số lượng mỗi trang
            max_pages: Giới hạn số trang
            delay: Delay giữa requests
            verbose: Có in log không
            include_processing_status: Danh sách trạng thái xử lý để lọc
            return_models: Trả về Invoice objects thay vì dict
            
        Returns:
            Dict với keys: success, all_invoices_with_details, summary
        """
        delay = delay if delay is not None else config.DEFAULT_DELAY
        
        # Bước 1: Lấy tất cả hóa đơn tóm tắt
        result = self.get_all_invoices(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            size=size,
            max_pages=max_pages,
            delay=delay,
            include_processing_status=include_processing_status,
            verbose=verbose
        )
        
        if not result["success"]:
            return result
        
        invoices_summary = result["all_invoices"]
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"📦 LẤY CHI TIẾT {len(invoices_summary)} HÓA ĐƠN")
            print(f"{'='*60}\n")
        
        # Bước 2: Lấy chi tiết
        invoices_with_details = []
        success_count = 0
        failed_count = 0
        
        for idx, inv_summary in enumerate(invoices_summary, 1):
            if verbose:
                print(f"[{idx}/{len(invoices_summary)}]", end=" ")
            
            detail_result = self.get_invoice_detail(
                invoice_summary=inv_summary,
                invoice_type=invoice_type,
                verbose=verbose
            )
            
            if detail_result["success"]:
                invoice_data = detail_result["data"]
                
                if return_models:
                    # Chuyển thành Invoice object
                    invoice_data = Invoice.from_dict(invoice_data)
                
                invoices_with_details.append(invoice_data)
                success_count += 1
            else:
                failed_count += 1
            
            if delay > 0 and idx < len(invoices_summary):
                time.sleep(delay)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"✅ Hoàn thành!")
            print(f"   • Thành công: {success_count}")
            print(f"   • Thất bại: {failed_count}")
            print(f"{'='*60}\n")
        
        return {
            "success": True,
            "all_invoices_with_details": invoices_with_details,
            "summary": {
                "total_invoices": len(invoices_summary),
                "details_success": success_count,
                "details_failed": failed_count,
                "pages_fetched": result["pages_fetched"]
            }
        }