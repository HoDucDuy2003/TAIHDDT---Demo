"""
Invoice Helpers
Các class helper để gọi API và xử lý kết quả hóa đơn
"""

from typing import Dict, List, Any, Optional
from .invoice_config import InvoiceConfig
from ..core import APIClient


class InvoiceEndpointCaller:
    """Helper class để gọi API endpoint"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def call_endpoint(
        self,
        invoice_type: str,
        start_date: str,
        end_date: str,
        page: int,
        size: int,
        sort_by: str,
        is_pos: bool,
        ttxly_filter: Optional[List[int]] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gọi API để lấy hóa đơn từ 1 endpoint cụ thể.

        Args:
            invoice_type       : "sold" hoặc "purchase"
            start_date         : Ngày bắt đầu (dd/mm/yyyy)
            end_date           : Ngày kết thúc (dd/mm/yyyy)
            page               : Trang (bắt đầu từ 1)
            size               : Số lượng mỗi trang
            sort_by            : Cách sắp xếp, ví dụ "tdlap:desc"
            is_pos             : True → /sco-query | False → /query
            additional_filters : Bộ lọc bổ sung (tuỳ chọn)
            verbose            : In log hay không

        Returns:
            Kết quả thô từ api_client.get()
        """

        search_parts = [
            f"tdlap=ge={start_date}T00:00:00",
            f"tdlap=le={end_date}T23:59:59",
        ]

        # Filter ttxly theo endpoint
        if is_pos:
            search_parts.append(f"ttxly=={InvoiceConfig.POS_STATUS}")
        elif ttxly_filter:
            # /query: filter ttxly theo invoice_type
            # Truyền tay để test: ttxly_filter=[5] hoặc [6] hoặc [5,6]
            status_str = ",".join(str(s) for s in ttxly_filter)
            search_parts.append(f"ttxly=in=({status_str})")
        # else: để trống → API tự filter theo invoice_type

        # Additional filters
        if additional_filters:
            for key, value in additional_filters.items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        search_parts.append(f"{key}={op}={val}")
                else:
                    search_parts.append(f"{key}=={value}")

        params = {
            "sort":   sort_by,
            "size":   size,
            "page":   page - 1,  # API dùng 0-based index
            "search": ";".join(search_parts),
        }
        if state:
            params["state"] = state

        endpoint = InvoiceConfig.get_endpoint(
            is_pos=is_pos,
            path=f"invoices/{invoice_type}"
        )

        if verbose:
            label = "🖥️  /sco-query (POS)" if is_pos else "📋 /query"
            print(f"{label}")
            print(f"   • Endpoint : {endpoint}")
            print(f"   • Search   : {params['search']}\n")
            print(f"   • State    : {params.get('state', 'KHÔNG CÓ')}\n")  # thêm dòng này

        return self.api_client.get(
            endpoint=endpoint,
            params=params,
            invoice_type=invoice_type
        )


class InvoiceResultMerger:
    """Helper class để xử lý và merge kết quả từ API"""

    @staticmethod
    def merge_results(
        result_normal: Dict[str, Any],
        result_pos: Dict[str, Any],
        page: int,
        size: int,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Merge kết quả từ /query và /sco-query.
        Chỉ lo data + phân trang, không trả state.
    
        Returns:
            Dict với keys: success, total, invoices, page, total_pages, has_next, has_prev
        """
        all_invoices = []
        grand_total = 0


        # Xử lý kết quả /query
        if result_normal["success"]:
            invoices_normal, total_normal, _ = InvoiceResultMerger._extract_invoices(result_normal["data"])
            all_invoices.extend(invoices_normal)
            grand_total += total_normal
            if verbose:
                print(f"   ✓ /query      : {len(invoices_normal)} hóa đơn (tổng server: {total_normal})")
        else:
            if verbose:
                error_msg = result_normal.get("message") or result_normal.get("error")
                print(f"   ✗ /query      : Lỗi - {error_msg}")


        
        # Xử lý kết quả /sco-query
        if result_pos["success"]:
            invoices_pos, total_pos , _ = InvoiceResultMerger._extract_invoices(result_pos["data"])
            all_invoices.extend(invoices_pos)
            grand_total += total_pos
            if verbose:
                print(f"   ✓ /sco-query  : {len(invoices_pos)} hóa đơn (tổng server: {total_pos})")
        else:
            if verbose:
                error_msg = result_pos.get("message") or result_pos.get("error")
                print(f"   ✗ /sco-query  : Lỗi - {error_msg}")

        total_pages = max(1, (grand_total + size - 1) // size) if grand_total > 0 else 1
        has_next    = page < total_pages

        if verbose:
            print(f"\n📊 Tổng kết:")
            print(f"   • Tổng server : {grand_total} hóa đơn")
            print(f"   • Trang       : {page}/{total_pages}")
            print(f"   • Còn tiếp    : {'Có' if has_next else 'Không'}\n")

        return {
            "success":     True,
            "total":       grand_total,
            "invoices":    all_invoices,
            "page":        page,
            "total_pages": total_pages,
            "has_next":    has_next,
            "has_prev":    page > 1,
        }

    @staticmethod
    def build_single_result(
        result: Dict[str, Any],
        page: int,
        size: int,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Build kết quả chuẩn từ 1 endpoint duy nhất (không merge).

        Args:
            result  : Kết quả thô từ call_endpoint()
            page    : Trang hiện tại
            size    : Kích thước trang
            verbose : In log hay không

        Returns:
            Dict với keys: success, total, invoices, page, total_pages, has_next, has_prev
        """
        if not result["success"]:
            return result

        invoices, total, state  = InvoiceResultMerger._extract_invoices(result["data"])
        total_pages     = max(1, (total + size - 1) // size) if total > 0 else 1
        has_next        = page < total_pages

        if verbose:
            print(f"✅ Thành công!")
            print(f"   • Tổng server : {total} hóa đơn")
            print(f"   • Lấy được   : {len(invoices)} hóa đơn")
            print(f"   • Trang       : {page}/{total_pages}\n")

        return {
            "success":     True,
            "total":       total,
            "invoices":    invoices,
            "page":        page,
            "state":       state,
            "total_pages": total_pages,
            "has_next":    has_next,
            "has_prev":    page > 1,
        }


    # Extract
    @staticmethod
    def extract_states(
        result_normal: Dict[str, Any],
        result_pos: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Extract cursor state từ 2 endpoint riêng biệt.
        Tách khỏi merge_results để mỗi hàm chỉ làm 1 việc.

        Returns:
            Dict với keys: state_normal, state_pos
        """
        state_normal = ""
        state_pos    = ""

        if result_normal.get("success") and result_normal.get("data"):
            _, _, state_normal = InvoiceResultMerger._extract_invoices(result_normal["data"])

        if result_pos.get("success") and result_pos.get("data"):
            _, _, state_pos = InvoiceResultMerger._extract_invoices(result_pos["data"])

        return {
            "state_normal": state_normal,
            "state_pos":    state_pos,
        }
    @staticmethod
    def _extract_invoices(data: Any) -> tuple:
        """
        Extract danh sách hóa đơn và tổng số từ response data.
        Hỗ trợ 2 format: list trực tiếp hoặc dict với key datas/content.

        Returns:
            Tuple (invoices: list, total: int)
        """
        if isinstance(data, list):
            return data, len(data)

        invoices = data.get("datas") or []
        total    = data.get("total") or 0
        state    = data.get("state") or ""

        return invoices, total, state