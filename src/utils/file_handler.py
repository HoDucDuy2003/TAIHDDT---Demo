"""
Module xử lý lưu trữ file
Bao gồm: lưu JSON, tạo thư mục, đặt tên file
"""

import os
import json
from datetime import datetime
import pandas as pd
from typing import Any, Optional

from .formatter import DataFormatter


class FileHandler:
    """Class xử lý lưu trữ file"""
    
    @staticmethod
    def save_to_json(
        data: Any, 
        filename: Optional[str] = None, 
        invoice_type: str = "sold",
        folder: str = "data"
    ) -> str:
        """
        Lưu dữ liệu vào file JSON
        
        Args:
            data: Dữ liệu cần lưu
            filename: Tên file (tự động tạo nếu None)
            invoice_type: Loại hóa đơn (dùng để tạo thư mục)
            folder: Thư mục gốc
            
        Returns:
            Đường dẫn file đã lưu
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            folder_path = f"{folder}/{invoice_type}"
            os.makedirs(folder_path, exist_ok=True)
            filename = f"{folder_path}/invoices_{timestamp}.json"
        else:
            # Tạo thư mục nếu cần
            folder_path = os.path.dirname(filename)
            if folder_path:
                os.makedirs(folder_path, exist_ok=True)
        

 
        # Convert objects to dicts if they have to_dict() method
        if isinstance(data, list) and data and hasattr(data[0], 'to_dict'):
            data = [item.to_dict() for item in data]
        elif hasattr(data, 'to_dict'):
            data = data.to_dict()

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Đã lưu vào: {filename}")
        return filename
    
    @staticmethod
    def load_from_json(filename: str) -> Any:
        """
        Đọc dữ liệu từ file JSON
        
        Args:
            filename: Đường dẫn file
            
        Returns:
            Dữ liệu đã đọc
        """
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @staticmethod
    def ensure_directory(directory: str):
        """
        Đảm bảo thư mục tồn tại
        
        Args:
            directory: Đường dẫn thư mục
        """
        os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def save_to_excel(
        data: list[dict],  # List of dicts từ invoices_with_details
        filename: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
        invoice_type: str = "sold",
        mst: str = "",
        folder: str = "data",
        selected_columns: Optional[list[str]] = None, # Các trường chỉ định (áp dụng sau flatten)
        column_names=None,
        flatten: bool = True
    ) -> str:
        """
        Lưu dữ liệu vào file Excel = convert từ json gốc
        
        Args:
            data: List of dicts (danh sách hóa đơn với details)
            filename: Tên file (tự động nếu None)
            invoice_type: Loại hóa đơn
            folder: Thư mục gốc
            selected_columns: List các trường muốn giữ (nếu None, giữ hết)
            column_names: Dict để rename columns
            
        Returns:
            Đường dẫn file đã lưu
        """
        if not filename:
            start_date = start_date.replace("/","")
            end_date = end_date.replace("/","")
            folder_path = f"{folder}/{invoice_type}"
            os.makedirs(folder_path, exist_ok=True)
            mst_part = f"{mst}" if mst else ""
            filename = f"{folder_path}/{mst_part}_invoices_{invoice_type}_{start_date}_{end_date}.xlsx"
        else:
            folder_path = os.path.dirname(filename)
            if folder_path:
                os.makedirs(folder_path, exist_ok=True)
        
        # Sử dụng DataFormatter pipeline để xử lý dữ liệu
        formatted_data = DataFormatter.transform_for_export(
            invoices=data,
            selected_columns=selected_columns,
            use_vietnamese_names=(column_names is not None),
            flatten=flatten,
        )
        
        # Rename columns nếu được chỉ định (override mapping)
        if column_names:
            formatted_data = DataFormatter.rename_columns(formatted_data, column_names)
        
        # Tạo DataFrame và lưu Excel
        df = pd.DataFrame(formatted_data)
        df.to_excel(filename, index=False, engine='openpyxl')

        print(f"💾 Đã lưu vào Excel: {filename}")
        return filename

    @staticmethod
    def save_to_csv(
        data: list[dict],
        filename: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
        invoice_type: str = "sold",
        mst: str = "",
        folder: str = "data",
        selected_columns: Optional[list[str]] = None,
        column_names=None,
        flatten: bool = True
    ) -> str:
        """
        Lưu dữ liệu vào file CSV

        Args:
            data: List of dicts (danh sách hóa đơn với details)
            filename: Tên file (tự động nếu None)
            invoice_type: Loại hóa đơn
            mst: Mã số thuế
            folder: Thư mục gốc
            selected_columns: List các trường muốn giữ (nếu None, giữ hết)
            column_names: Dict để rename columns

        Returns:
            Đường dẫn file đã lưu
        """
        if not filename:
            start_date = start_date.replace("/", "")
            end_date = end_date.replace("/", "")
            folder_path = f"{folder}/{invoice_type}"
            os.makedirs(folder_path, exist_ok=True)
            mst_part = f"{mst}" if mst else ""
            filename = f"{folder_path}/{mst_part}_invoices_{invoice_type}_{start_date}_{end_date}.csv"
        else:
            folder_path = os.path.dirname(filename)
            if folder_path:
                os.makedirs(folder_path, exist_ok=True)

        formatted_data = DataFormatter.transform_for_export(
            invoices=data,
            selected_columns=selected_columns,
            use_vietnamese_names=(column_names is not None),
            flatten=flatten,
        )

        if column_names:
            formatted_data = DataFormatter.rename_columns(formatted_data, column_names)

        df = pd.DataFrame(formatted_data)
        df.to_csv(filename, index=False, encoding="utf-8-sig")

        print(f"💾 Đã lưu vào CSV: {filename}")
        return filename
