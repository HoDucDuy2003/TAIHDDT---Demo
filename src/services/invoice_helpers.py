"""
Invoice Helpers
Các hàm helper để xử lý hóa đơn
"""

from typing import Dict, List, Any, Optional
from .invoice_config import EndpointType, InvoiceConfig
from ..core import APIClient


class InvoiceEndpointCaller:
    """Helper class để gọi API endpoint"""
    
    def __init__(self, api_client: APIClient):
        """
        Khởi tạo caller
        
        Args:
            api_client: API client instance
        """
        self.api_client = api_client
    
    def call_endpoint(
        self,
        invoice_type: str,
        start_date: str,
        end_date: str,
        page: int,
        size: int,
        sort_by: str,
        endpoint_type: str,
        include_processing_status: Optional[List[int]] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Gọi API để lấy hóa đơn từ endpoint cụ thể
        
        Args:
            invoice_type: "sold" hoặc "purchase"
            start_date: Ngày bắt đầu (dd/mm/yyyy)
            end_date: Ngày kết thúc (dd/mm/yyyy)
            page: Trang (bắt đầu từ 1)
            size: Số lượng mỗi trang
            sort_by: Cách sắp xếp
            endpoint_type: "query" (bình thường) hoặc "sco-query" (máy tính tiền)
            include_processing_status: Danh sách trạng thái xử lý
            additional_filters: Bộ lọc bổ sung
            verbose: Có in log không
            
        Returns:
            Kết quả từ API
        """
        # Tạo search query
        search_parts = [
            f"tdlap=ge={start_date}T00:00:00",
            f"tdlap=le={end_date}T23:59:59"
        ]
        
        # Thêm điều kiện trạng thái xử lý
        # CHÚ Ý: 
        # - /sco-query: CHỈ filter ttxly==8 (máy tính tiền)
        if endpoint_type == "sco-query":
            search_parts.append("ttxly==8")
        
        # Thêm additional filters (chưa dùng đến)
        if additional_filters:
            for key, value in additional_filters.items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        search_parts.append(f"{key}={op}={val}")
                else:
                    search_parts.append(f"{key}=={value}")
        
        # Tạo params
        params = {
            "sort": sort_by,
            "size": size,
            "page": page - 1,
            "search": ";".join(search_parts)
        }
        

        # path = f"invoices/{invoice_type}"

        # Xác định endpoint
        if endpoint_type == "sco-query":
            endpoint = f"/sco-query/invoices/{invoice_type}"
            if verbose:
                print(f"🖥️  Gọi /sco-query (máy tính tiền)...")
                print(f"   • Search: {params['search']}")
                print(f"  EndPoint: {endpoint}\n")
        else:
            endpoint = f"/query/invoices/{invoice_type}"
            if verbose:
                print(f"📋 Gọi /query (bình thường)...")
                print(f"   • Search: {params['search']}")
                print(f"  EndPoint: {endpoint}\n")
        
        # Gọi API
        result = self.api_client.get(
            endpoint=endpoint,
            params=params,
            invoice_type=invoice_type
        )
        
        return result


class InvoiceResultMerger:
    """Helper class để merge kết quả từ nhiều endpoint"""
    
    @staticmethod
    def merge_results(
        result_normal: Dict[str, Any],
        result_pos: Dict[str, Any],
        page: int,
        size: int,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Merge kết quả từ 2 endpoint (/query và /sco-query)
        
        Args:
            result_normal: Kết quả từ /query (tất cả trừ POS)
            result_pos: Kết quả từ /sco-query (chỉ POS - ttxly=8)
            page: Trang hiện tại
            size: Kích thước trang
            verbose: Có in log không
            
        Returns:
            Dict merged với keys: success, total, invoices, page, total_pages, has_next, has_prev
        """
        all_invoices = []
        total_count = 0
        
        if result_normal["success"]:
            invoices_normal, total_normal = InvoiceResultMerger._extract_invoices(result_normal["data"])
            all_invoices.extend(invoices_normal)
            total_count += len(invoices_normal)
            
            if verbose:
                print(f"   ✓ Lấy được {len(invoices_normal)} hóa đơn\n")
        else:
            if verbose:
                error_msg = result_normal.get('message', result_normal.get('error'))
                print(f"   ✗ Lỗi: {error_msg}\n")
        
        # Xử lý kết quả từ /sco-query (chỉ POS)
        if result_pos["success"]:
            invoices_pos, total_pos = InvoiceResultMerger._extract_invoices(result_pos["data"])
            all_invoices.extend(invoices_pos)
            total_count += len(invoices_pos)
            
            if verbose:
                print(f"   ✓ Lấy được {len(invoices_pos)} hóa đơn\n")
        else:
            if verbose:
                error_msg = result_pos.get('message', result_pos.get('error'))
                print(f"   ✗ Lỗi: {error_msg}\n")
        
        # Tính toán phân trang
        total_pages = max(1, (total_count + size - 1) // size) if total_count > 0 else 1
        has_next = page < total_pages
        
        if verbose:
            print(f"📊 Tổng kết:")
            print(f"   • Tổng số: {total_count} hóa đơn")
            print(f"   • Trang {page}/{total_pages}")
            print(f"   • Còn trang tiếp: {'Có' if has_next else 'Không'}\n")
        
        return {
            "success": True,
            "total": total_count,
            "invoices": all_invoices,
            "page": page,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": page > 1
        }
    
    @staticmethod
    def _extract_invoices(data: Any) -> tuple:
        """
        Extract danh sách hóa đơn và tổng số từ response data
        
        Args:
            data: Response data từ API
            
        Returns:
            Tuple (invoices, total)
        """
        if isinstance(data, list):
            return data, len(data)
        else:
            invoices = data.get("datas", []) or data.get("content", [])
            total = data.get("total", 0) or data.get("totalElements", 0)
            return invoices, total