"""
Invoice Service
Business logic xử lý hóa đơn
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from ..core import config, APIClient
from ..models import Invoice
from .invoice_config import InvoiceConfig
from .invoice_helpers import InvoiceEndpointCaller, InvoiceResultMerger


class InvoiceService:
    """Service xử lý nghiệp vụ hóa đơn"""

    def __init__(self, api_client: Optional[APIClient] = None):
        self.api_client      = api_client or APIClient()
        self.endpoint_caller = InvoiceEndpointCaller(self.api_client)

    # ------------------------------------------------------------------ #
    #  PUBLIC: get_invoices
    # ------------------------------------------------------------------ #

    def get_invoices(
        self,
        invoice_type: str = "sold",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        size: Optional[int] = None,
        sort_by: str = "tdlap:desc",
        include_pos: Optional[bool] = None,
        ttxly_filter: Optional[List[int]] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
        state: str = "",
        state_normal: str = "",
        state_pos: str = "",
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Lấy danh sách hóa đơn theo trang.

        Args:
            invoice_type       : "sold" hoặc "purchase"
            start_date         : Ngày bắt đầu (dd/mm/yyyy), mặc định 30 ngày trước
            end_date           : Ngày kết thúc (dd/mm/yyyy), mặc định hôm nay
            page               : Trang (bắt đầu từ 1)
            size               : Số lượng mỗi trang
            sort_by            : Cách sắp xếp
            include_pos        : None  → lấy tất cả (gọi cả /query + /sco-query)
                                 False → chỉ hóa đơn thường (/query)
                                 True  → chỉ máy tính tiền (/sco-query)
            ttxly_filter       : Filter ttxly tùy chỉnh cho /query (dùng để test)
                                 Ví dụ: [5] hoặc [6] hoặc [5, 6]
                                 Chỉ có tác dụng khi include_pos=False hoặc None
            additional_filters : Bộ lọc bổ sung
            state              : Cursor token cho pagination (lấy từ response trang trước)
            verbose            : In log hay không

        Returns:
            Dict với keys: success, total, invoices, page, total_pages, has_next, has_prev, state
        """
        size     = size or config.DEFAULT_PAGE_SIZE
        end_date = end_date or datetime.now().strftime("%d/%m/%Y")

        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%d/%m/%Y")

        if verbose:
            pos_label = {None: "Tất cả", True: "Chỉ POS", False: "Chỉ thường"}.get(include_pos)
            print(f"🔍 Hóa đơn {invoice_type} | {pos_label}")
            print(f"📅 Từ {start_date} đến {end_date}")
            print(f"📄 Trang {page}, mỗi trang {size}\n")

        # CASE 1: Lấy tất cả → gọi cả 2 endpoint rồi merge
        if include_pos is None:
            return self._get_all_sources(
                invoice_type=invoice_type,
                start_date=start_date,
                end_date=end_date,
                page=page,
                size=size,
                sort_by=sort_by,
                ttxly_filter=ttxly_filter,
                additional_filters=additional_filters,
                state_normal=state_normal,
                state_pos=state_pos,
                verbose=verbose,
            )

        # CASE 2: Chỉ 1 endpoint
        return self._get_single_source(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            is_pos=include_pos,
            ttxly_filter=ttxly_filter,
            additional_filters=additional_filters,
            state=state,
            verbose=verbose,
        )

    # ------------------------------------------------------------------ #
    #  PUBLIC: get_invoice_detail
    # ------------------------------------------------------------------ #

    def get_invoice_detail(
        self,
        invoice_summary: Dict[str, Any],
        invoice_type: str,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Lấy chi tiết 1 hóa đơn.

        Args:
            invoice_summary : Dict tóm tắt hóa đơn (cần có nbmst, khhdon, shdon, khmshdon, ttxly)
            invoice_type    : "sold" hoặc "purchase"
            verbose         : In log hay không

        Returns:
            Dict với keys: success, data
        """
        nbmst    = invoice_summary.get("nbmst")
        khhdon   = invoice_summary.get("khhdon")
        shdon    = invoice_summary.get("shdon")
        khmshdon = invoice_summary.get("khmshdon")
        ttxly    = invoice_summary.get("ttxly")

        if not all([nbmst, khhdon, shdon, khmshdon]):
            return {"success": False, "error": "Missing required parameters"}

        params   = {"nbmst": nbmst, "khhdon": khhdon, "shdon": shdon, "khmshdon": khmshdon}
        is_pos   = InvoiceConfig.is_pos_status(ttxly)
        endpoint = InvoiceConfig.get_endpoint(is_pos=is_pos, path="invoices/detail")

        if verbose:
            print(f"  📋 {khhdon}-{shdon}", end=" ")

        result = self.api_client.get(
            endpoint=endpoint,
            params=params,
            invoice_type=invoice_type
        )

        if result["success"]:
            if verbose:
                print("✓")
            return {"success": True, "data": result["data"]}
        else:
            if verbose:
                print("✗")
            return result

    # ------------------------------------------------------------------ #
    #  PUBLIC: get_all_invoices
    # ------------------------------------------------------------------ #

    def get_all_invoices(
        self,
        invoice_type: str = "sold",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        size: Optional[int] = None,
        max_pages: Optional[int] = None,
        delay: Optional[float] = None,
        include_pos: Optional[bool] = None,
        ttxly_filter: Optional[List[int]] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """
        Lấy TẤT CẢ hóa đơn (tự động phân trang).

        Returns:
            Dict với keys: success, total, all_invoices, pages_fetched
        """
        size  = size or config.DEFAULT_PAGE_SIZE
        delay = delay if delay is not None else config.DEFAULT_DELAY

        all_invoices  = []
        seen_ids      = set()
        page          = 1
        state         = ""   # dùng cho _get_single_source
        state_normal  = ""   # dùng cho /query trong _get_all_sources
        state_pos     = ""   # dùng cho /sco-query trong _get_all_sources

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
                include_pos=include_pos,
                ttxly_filter=ttxly_filter,
                state=state,
                state_normal=state_normal,
                state_pos=state_pos,
                verbose=verbose,
            )

            if not result["success"]:
                return result

            # Lấy state cursor cho trang tiếp theo
            state        = result.get("state", "")
            state_normal = result.get("state_normal", "")
            state_pos    = result.get("state_pos", "")

            # Dedup theo id
            prev_count = len(all_invoices)
            for inv in result["invoices"]:
                inv_id = inv.get("id")
                if inv_id and inv_id not in seen_ids:
                    seen_ids.add(inv_id)
                    all_invoices.append(inv)

            if verbose:
                print(f"📦 Đã lấy: {len(all_invoices)}/{result['total']} hóa đơn\n")

            # Dừng nếu API trả lặp (không có hóa đơn mới)
            if len(all_invoices) == prev_count:
                if verbose:
                    print(f"⚠️  API trả dữ liệu lặp, dừng sớm tại trang {page}\n")
                break

            # Dừng nếu đã đủ tổng từ server
            if len(all_invoices) >= result["total"]:
                break

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
            "success":       True,
            "total":         len(all_invoices),
            "all_invoices":  all_invoices,
            "pages_fetched": page,
        }

    # ------------------------------------------------------------------ #
    #  PUBLIC: get_all_invoices_with_details
    # ------------------------------------------------------------------ #

    def get_all_invoices_with_details(
        self,
        invoice_type: str = "sold",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        size: Optional[int] = None,
        max_pages: Optional[int] = None,
        delay: Optional[float] = None,
        include_pos: Optional[bool] = None,
        ttxly_filter: Optional[List[int]] = None,
        return_models: bool = False,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Lấy TẤT CẢ hóa đơn KÈM CHI TIẾT.

        Returns:
            Dict với keys: success, all_invoices_with_details, summary
        """
        delay = delay if delay is not None else config.DEFAULT_DELAY

        # Bước 1: Lấy toàn bộ danh sách tóm tắt
        result = self.get_all_invoices(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            size=size,
            max_pages=max_pages,
            delay=delay,
            include_pos=include_pos,
            ttxly_filter=ttxly_filter,
            verbose=verbose,
        )

        if not result["success"]:
            return result

        invoices_summary = result["all_invoices"]

        if verbose:
            print(f"\n{'='*60}")
            print(f"📦 LẤY CHI TIẾT {len(invoices_summary)} HÓA ĐƠN")
            print(f"{'='*60}\n")

        # Bước 2: Lấy chi tiết từng hóa đơn
        invoices_with_details = []
        success_count         = 0
        failed_count          = 0

        for idx, inv_summary in enumerate(invoices_summary, 1):
            if verbose:
                print(f"[{idx}/{len(invoices_summary)}]", end=" ")

            detail_result = self.get_invoice_detail(
                invoice_summary=inv_summary,
                invoice_type=invoice_type,
                verbose=verbose,
            )

            if detail_result["success"]:
                invoice_data = detail_result["data"]
                if return_models:
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
            print(f"   • Thành công : {success_count}")
            print(f"   • Thất bại   : {failed_count}")
            print(f"{'='*60}\n")

        return {
            "success": True,
            "all_invoices_with_details": invoices_with_details,
            "summary": {
                "total_invoices":  len(invoices_summary),
                "details_success": success_count,
                "details_failed":  failed_count,
                "pages_fetched":   result["pages_fetched"],
            },
        }

    # ------------------------------------------------------------------ #
    #  PRIVATE
    # ------------------------------------------------------------------ #

    def _get_all_sources(
        self,
        invoice_type: str,
        start_date: str,
        end_date: str,
        page: int,
        size: int,
        sort_by: str,
        ttxly_filter: Optional[List[int]],
        additional_filters: Optional[Dict[str, Any]],
        state_normal: str,
        state_pos: str,
        verbose: bool,
    ) -> Dict[str, Any]:
        """Gọi cả /query và /sco-query rồi merge."""
        if verbose:
            print("[1/2] Lấy hóa đơn thường từ /query...")

        result_normal = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            is_pos=False,
            ttxly_filter=ttxly_filter,
            additional_filters=additional_filters,
            state=state_normal,
            verbose=verbose,
        )

        if verbose:
            print("[2/2] Lấy máy tính tiền từ /sco-query...")

        result_pos = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            is_pos=True,
            additional_filters=additional_filters,
            state=state_pos,
            verbose=verbose,
        )

        merged = InvoiceResultMerger.merge_results(
            result_normal=result_normal,
            result_pos=result_pos,
            page=page,
            size=size,
            verbose=verbose,
        )

        states = InvoiceResultMerger.extract_states(
            result_normal=result_normal,
            result_pos=result_pos,
        )

        return {**merged, **states}

    def _get_single_source(
        self,
        invoice_type: str,
        start_date: str,
        end_date: str,
        page: int,
        size: int,
        sort_by: str,
        is_pos: bool,
        ttxly_filter: Optional[List[int]],
        additional_filters: Optional[Dict[str, Any]],
        state: str,
        verbose: bool,
    ) -> Dict[str, Any]:
        """Gọi 1 endpoint duy nhất."""
        result = self.endpoint_caller.call_endpoint(
            invoice_type=invoice_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
            sort_by=sort_by,
            is_pos=is_pos,
            ttxly_filter=ttxly_filter,
            additional_filters=additional_filters,
            state=state,
            verbose=verbose,
        )

        return InvoiceResultMerger.build_single_result(
            result=result,
            page=page,
            size=size,
            verbose=verbose,
        )