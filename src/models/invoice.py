"""
Invoice Model
Data models cho hóa đơn
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class InvoiceStatus(Enum):
    """Enum cho trạng thái hóa đơn"""
    NEW = 1  # Hóa đơn mới
    REPLACEMENT = 2  # Hóa đơn thay thế
    ADJUSTMENT = 3  # Hóa đơn điều chỉnh
    REPLACED = 4  # Hóa đơn đã bị thay thế
    ADJUSTED = 5  # Hóa đơn đã bị điều chỉnh
    CANCELLED = 6  # Hóa đơn đã bị hủy
    
    @classmethod
    def from_value(cls, value: Optional[int]) -> Optional['InvoiceStatus']:
        """Tạo InvoiceStatus từ giá trị số"""
        if value is None:
            return None
        try:
            return cls(value)
        except ValueError:
            return None
    
    def to_vietnamese(self) -> str:
        """Chuyển status thành text tiếng Việt"""
        status_map = {
            InvoiceStatus.NEW: "Hóa đơn mới",
            InvoiceStatus.REPLACEMENT: "Hóa đơn thay thế",
            InvoiceStatus.ADJUSTMENT: "Hóa đơn điều chỉnh",
            InvoiceStatus.REPLACED: "Hóa đơn đã bị thay thế",
            InvoiceStatus.ADJUSTED: "Hóa đơn đã bị điều chỉnh",
            InvoiceStatus.CANCELLED: "Hóa đơn đã bị hủy"
        }
        return status_map.get(self, "Không xác định")
    



class ProcessingStatus(Enum):
    """Enum cho trạng thái xử lý hóa đơn (ttxly)"""
    TAX_RECEIVED = 0  # Cục thuế đã nhận
    CHECKING_CONDITIONS = 1  # Đang tiến hành kiểm tra điều kiện cấp
    TAX_REJECTED = 2  # CQT từ chối hóa đơn theo từng lần phát sinh
    ELIGIBLE_FOR_CODE = 3  # Hóa đơn đủ điều kiện cấp mã
    NOT_ELIGIBLE_FOR_CODE = 4  # Hóa đơn không đủ điều kiện cấp mã
    CODE_ISSUED = 5  # Đã cấp mã hóa đơn
    TAX_RECEIVED_NO_CODE = 6  # Cục thuế đã nhận không mã
    PERIODIC_CHECK_NO_CODE = 7  # Đã kiểm tra định kỳ HDDT không có mã
    TAX_RECEIVED_WITH_POS_CODE = 8  # Cục thuế đã nhận hóa đơn có mã khởi tạo từ máy tính tiền
    
    @classmethod
    def from_value(cls, value: Optional[int]) -> Optional['ProcessingStatus']:
        """Tạo ProcessingStatus từ giá trị số"""
        if value is None:
            return None
        try:
            return cls(value)
        except ValueError:
            return None
    
    def to_vietnamese(self) -> str:
        """Chuyển processing status thành text tiếng Việt"""
        status_map = {
            ProcessingStatus.TAX_RECEIVED: "Cục thuế đã nhận",
            ProcessingStatus.CHECKING_CONDITIONS: "Đang tiến hành kiểm tra điều kiện cấp",
            ProcessingStatus.TAX_REJECTED: "CQT từ chối hóa đơn theo từng lần phát sinh",
            ProcessingStatus.ELIGIBLE_FOR_CODE: "Hóa đơn đủ điều kiện cấp mã",
            ProcessingStatus.NOT_ELIGIBLE_FOR_CODE: "Hóa đơn không đủ điều kiện cấp mã",
            ProcessingStatus.CODE_ISSUED: "Đã cấp mã hóa đơn",
            ProcessingStatus.TAX_RECEIVED_NO_CODE: "Cục thuế đã nhận không mã",
            ProcessingStatus.PERIODIC_CHECK_NO_CODE: "Đã kiểm tra định kỳ HDDT không có mã",
            ProcessingStatus.TAX_RECEIVED_WITH_POS_CODE: "Cục thuế đã nhận hóa đơn có mã khởi tạo từ máy tính tiền"
        }
        return status_map.get(self, "Không xác định")
    

@dataclass
class InvoiceItem:
    """Model cho một hàng hóa trong hóa đơn"""
    
    stt : int  # Số thứ tự
    name: str  # Tên hàng hóa
    quantity: float  # Số lượng
    unit: str  # Đơn vị tính
    unit_price: float  # Đơn giá
    value_notax: float  # Thành tiền chưa thuế
    type_tax_rate: str  # Loại thuế suất (GTGT, TTĐB, ...)
    tax_rate: float  # Tỷ suất thuế (%)
    discount: float = 0.0  # Chiết khấu
    value_tax: float = 0.0  # Tiền thuế
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvoiceItem':
        """Tạo InvoiceItem từ dict"""

        tax_rate = float(data.get('tsuat') or 0)
        
        # Lấy thành tiền
        value_notax = float(data.get('thtien') or 0)
        
        # Tính tiền thuế = thành tiền × thuế suất
        return cls(
            stt=data.get('stt'),
            name=data.get('ten') or 'N/A',
            quantity=float(data.get('sluong') or 0),
            unit=data.get('dvtinh') or 'N/A',
            unit_price=float(data.get('dgia') or 0),
            value_notax=value_notax,
            discount=data.get('tlckhau'),
            type_tax_rate = data.get('ltsuat') or "",
            tax_rate = tax_rate,
            value_tax=data.get('tthue') or 0
        )


@dataclass
class Invoice:
    """Model cho hóa đơn điện tử"""
    
    # Thông tin cơ bản
    invoice_template: str  #Mẫu số hóa đơn
    invoice_serial: str  # Ký hiệu hóa đơn
    invoice_number: str  # Số hóa đơn
    invoice_date: str  # Ngày lập
    lookup_code: Optional[str] = None  # Mã tra cứu
    invoice_currency: Optional[str] = None  # Đơn vị tiền tệ
    
    # Người bán
    seller_name: str = ""
    seller_tax_code: str = ""
    seller_address: str = ""
    seller_phone: Optional[str] = None
    
    # Người mua
    buyer_name: str = ""
    buyer_tax_code: str = ""
    buyer_address: str = ""
    buyer_phone: Optional[str] = None
    
    # Tiền
    total_before_tax: float = 0.0  # Tổng tiền chưa thuế
    tax_amount: float = 0.0  # Tiền thuế
    total_amount: float = 0.0  # Tổng thanh toán
    
    #Ghi chú
    note : Optional[str] = None

    # Danh sách hàng hóa
    items: List[InvoiceItem] = field(default_factory=list)
    
    # Trạng thái
    status: Optional[InvoiceStatus] = None,
    processing_status: Optional[ProcessingStatus] = None

    payment_method: Optional[str] = None  # Hình thức thanh toán
    
    # Raw data
    raw_data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Invoice':
        """
        Tạo Invoice từ dict (dữ liệu từ API)
        
        Args:
            data: Dict chứa dữ liệu hóa đơn
            
        Returns:
            Invoice instance
        """
        # Parse items
        items_data = (data.get("hdhhdvu") or [])
        items = [InvoiceItem.from_dict(item) for item in items_data]
        
        return cls(
            # Thông tin cơ bản
            invoice_template=data.get('khmshdon') or '',
            invoice_serial=data.get('khhdon') or '',
            invoice_number=data.get('shdon') or '',
            invoice_date=data.get('ntao') or '',
            lookup_code=data.get('mhdon'),
            invoice_currency = data.get('dvtte'),
            
            # Người bán
            seller_name=data.get('nbten') or '',
            seller_tax_code=data.get('nbmst') or '',
            seller_address=data.get('nbdchi') or '',
            seller_phone=data.get('nbsdthoai'),
            
            # Người mua
            buyer_name=data.get('nmten') or data.get('nmtnmua'),
            buyer_tax_code=data.get('nmmst') or '',
            buyer_address=data.get('nmdchi') or '',
            buyer_phone=data.get('nmsdthoai'),
            
            # Tiền
            total_before_tax=float(data.get('tgtcthue') or 0),
            tax_amount=float(data.get('tgtthue') or 0),
            total_amount=float(data.get('tgtttbso') or 0),
            
            # Danh sách hàng hóa
            items=items,
            
            # Trạng thái
            status=InvoiceStatus.from_value(data.get('tthai')),
            payment_method=data.get('thtttoan'),
            processing_status=ProcessingStatus.from_value(data.get('ttxly')),

            # Ghi chú
            note=data.get('gchu'),
            
            # Raw
            raw_data=data
        )
    
    
    

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển Invoice thành dict"""
        return {
            'invoice_template': self.invoice_template,
            'invoice_serial': self.invoice_serial,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'invoice_currency': self.invoice_currency,
            'lookup_code': self.lookup_code,
            'seller_name': self.seller_name,
            'seller_tax_code': self.seller_tax_code,
            'seller_address': self.seller_address,
            'seller_phone': self.seller_phone,
            'buyer_name': self.buyer_name,
            'buyer_tax_code': self.buyer_tax_code,
            'buyer_address': self.buyer_address,
            'buyer_phone': self.buyer_phone,
            'total_before_tax': self.total_before_tax,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'items': [
                {
                    'stt': item.stt,
                    'name': item.name,
                    'quantity': item.quantity,
                    'unit': item.unit,
                    'unit_price': item.unit_price,
                    'value_notax': item.value_notax,
                    'tax_rate': item.tax_rate,
                    'type_tax_rate': item.type_tax_rate,
                    'discount': item.discount,
                    'value_tax': item.value_tax
                }
                for item in self.items
            ],
            'status': self.get_status_text(),
            'payment_method': self.payment_method, 
            'processing status':self.get_processing_status_text(),
            'note' : self.note
        }
    
    def __str__(self) -> str:
        """String representation"""
        return f"Invoice({self.invoice_serial}-{self.invoice_number}, {self.total_amount:,.0f} VNĐ)"
    
    def get_status_text(self) -> str:
        """Lấy text mô tả trạng thái"""
        if self.status is None:
            return "Không xác định"
        return self.status.to_vietnamese()
    
    def get_processing_status_text(self) -> str:
        """Lấy text mô tả trạng thái xử lý"""
        if self.processing_status is None:
            return "Không xác định"
        return self.processing_status.to_vietnamese()