"""
Module xử lý format và chuyển đổi dữ liệu hóa đơn
Bao gồm: làm phẳng dữ liệu, chọn cột, đổi tên cột, chuẩn hóa dữ liệu
"""

from typing import Dict, Any, List, Optional


class DataFormatter:
    """Class xử lý format và chuyển đổi dữ liệu hóa đơn cho export"""
    
    VIETNAMESE_COLUMN_NAMES = {
        # Thông tin hóa đơn
        'invoice_template': 'Mẫu số HĐ',
        'invoice_serial': 'Ký hiệu HĐ',
        'invoice_number': 'Số HĐ',
        'invoice_date': 'Ngày lập',
        'invoice_currency': 'Đơn vị tiền tệ',
        'lookup_code': 'Mã tra cứu',

        # Thông tin người bán
        'seller_tax_code': 'MST người bán',
        'seller_mst': 'MST người bán',
        'seller_name': 'Tên người bán',
        'seller_address': 'Địa chỉ người bán',
        'seller_phone': 'SĐT người bán',

        # Thông tin người mua
        'buyer_mst': 'MST người mua',
        'buyer_name': 'Tên người mua',
        'buyer_tax_code': 'MST người mua',
        'buyer_address': 'Địa chỉ người mua',
        'buyer_phone': 'SĐT người mua',

        # Thông tin thanh toán
        'total_before_tax': 'Tổng tiền trước thuế',
        'tax_amount': 'Tổng tiền thuế',
        'total_amount': 'Tổng thanh toán',
        'payment_method': 'Hình thức TT',

        # Trạng thái
        'status': 'Trạng thái HĐ',
        'processing status': 'Trạng thái xử lý',
        'note': 'Ghi chú',
        
        # Chi tiết hàng hóa
        'stt': 'STT',
        'name': 'Tên hàng hóa/dịch vụ',
        'unit': 'ĐVT',
        'quantity': 'Số lượng',
        'unit_price': 'Đơn giá',
        'tax_rate': 'Thuế suất',
        'discount': 'Chiết khấu',
        'value_notax': 'Thành tiền chưa thuế',
        'discount' : 'Chiết khấu',
        'value_tax': 'Tiền thuế GTGT',
    }
    
    DEFAULT_EXPORT_COLUMNS = [
        'invoice_template', 'invoice_serial', 'invoice_number', 'invoice_date', 'invoice_currency','lookup_code', 
        'seller_tax_code', 'seller_name', 'seller_address', 
        'buyer_name', 'buyer_address', 'buyer_tax_code',
        'stt', 'name', 'unit', 'quantity', 'unit_price', 'tax_rate', 
        'discount', 'value_notax', 'value_tax', 
        'tax_amount', 'total_amount', 'payment_method', 'status', 'processing status','note'
    ]
    
    REQUIRED_FIELDS = [
        'invoice_template', 'invoice_serial', 'invoice_number', 'invoice_date',
        'seller_name', 'buyer_name', 'total_amount'
    ]
    
    @staticmethod
    def flatten_invoices(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Làm phẳng dữ liệu hóa đơn (mỗi item thành một hàng riêng)
        
        Mỗi hàng = thông tin hóa đơn + thông tin một hàng hóa
        Thông tin tổng tiền chỉ hiện ở dòng đầu tiên
        
        Args:
            invoices: List các hóa đơn có nested items
            
        Returns:
            List dữ liệu làm phẳng (mỗi row = hóa đơn + 1 item)
        """
        flattened_data = []
        
        for invoice in invoices:
            # Lấy thông tin hóa đơn chung (loại trừ items)
            invoice_common = {k: v for k, v in invoice.items() if k != 'items'}
            
            # Lấy danh sách items
            items = invoice.get('items', [])
            
            # Nếu không có items, vẫn thêm hàng chính
            if not items:
                flattened_data.append(invoice_common)
            else:
                # Lặp qua từng item
                for idx, item in enumerate(items):
                    # Merge thông tin hóa đơn với thông tin item
                    row = {**invoice_common, **item}
                    
                    # Chỉ giữ tổng tiền ở dòng đầu tiên
                    if idx > 0:  # Dòng thứ 2 trở đi
                        row['total_before_tax'] = ''
                        row['tax_amount'] = ''
                        row['total_amount'] = ''
                    
                    flattened_data.append(row)
        
        return flattened_data
    
    @staticmethod
    def select_columns(
        data: List[Dict[str, Any]], 
        columns: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Chọn các cột cụ thể từ dữ liệu
        
        Args:
            data: List các dict (dữ liệu đầu vào)
            columns: List tên cột cần giữ
            
        Returns:
            List dict chỉ chứa các cột được chọn
        """
        if not data:
            return []
        
        result = []
        for row in data:
            selected_row = {
                col: row.get(col) 
                for col in columns 
                if col in row
            }
            result.append(selected_row)
        
        return result
    
    @staticmethod
    def rename_columns(
        data: List[Dict[str, Any]], 
        mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Đổi tên cột sử dụng mapping dict
        
        Args:
            data: List các dict (dữ liệu đầu vào)
            mapping: Dict {tên_cột_cũ: tên_cột_mới}
                    Nếu None, sử dụng VIETNAMESE_COLUMN_NAMES
            
        Returns:
            List dict với cột đã được đổi tên
        """
        if mapping is None:
            mapping = DataFormatter.VIETNAMESE_COLUMN_NAMES
        
        if not data:
            return []
        
        result = []
        for row in data:
            renamed_row = {}
            for old_name, value in row.items():
                new_name = mapping.get(old_name, old_name)
                renamed_row[new_name] = value
            result.append(renamed_row)
        
        return result
    
    @staticmethod
    def validate_invoice_data(invoice: Dict[str, Any]) -> bool:
        """
        Kiểm tra hóa đơn có đầy đủ các trường bắt buộc
        
        Args:
            invoice: Dict chứa dữ liệu hóa đơn
            
        Returns:
            True nếu hợp lệ, False nếu thiếu trường
        """
        for field in DataFormatter.REQUIRED_FIELDS:
            if field not in invoice or invoice[field] is None:
                return False
        return True
    

    # Hàm này chưa sử dụng trong module
    @staticmethod
    def validate_invoices(invoices: List[Dict[str, Any]]) -> tuple[bool, List[int]]:
        """
        Kiểm tra danh sách hóa đơn
        
        Args:
            invoices: List các hóa đơn
            
        Returns:
            Tuple (all_valid, invalid_indices)
            - all_valid: True nếu toàn bộ hợp lệ
            - invalid_indices: List index của hóa đơn không hợp lệ
        """
        invalid_indices = []
        
        for idx, invoice in enumerate(invoices):
            if not DataFormatter.validate_invoice_data(invoice):
                invalid_indices.append(idx)
        
        return len(invalid_indices) == 0, invalid_indices
    
    @staticmethod
    def transform_for_export(
        invoices: List[Dict[str, Any]],
        selected_columns: Optional[List[str]] = None,
        use_vietnamese_names: bool = True,
        flatten: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Pipeline chuyển đổi đầy đủ cho export (Excel, JSON, v.v.)
        
        Bước:
        1. Làm phẳng dữ liệu (nếu flatten=True)
        2. Chọn cột (nếu specified)
        3. Đổi tên cột tiếng Việt (nếu use_vietnamese_names=True)
        
        Args:
            invoices: List các hóa đơn
            selected_columns: List cột cần giữ (None = giữ hết)
            use_vietnamese_names: Có đổi sang tên tiếng Việt không
            flatten: Có làm phẳng dữ liệu không
            
        Returns:
            List dict đã được format
        """
        if not invoices:
            return []
        
        # Bước 1: Làm phẳng
        if flatten:
            data = DataFormatter.flatten_invoices(invoices)
        else:
            data = invoices
        
        # Bước 2: Chọn cột
        if selected_columns:
            data = DataFormatter.select_columns(data, selected_columns)
        
        # Bước 3: Đổi tên cột
        if use_vietnamese_names:
            data = DataFormatter.rename_columns(data)
        
        return data
