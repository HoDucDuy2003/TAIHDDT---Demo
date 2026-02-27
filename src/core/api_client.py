"""
API Client Module - Updated with Retry Mechanism
Xử lý tất cả HTTP requests đến API hóa đơn điện tử
"""

import requests
import time
from typing import Dict, Any, Optional
from .config import config


class APIClient:
    """Client để giao tiếp với API hóa đơn điện tử"""
    
    def __init__(self, token: Optional[str] = None, max_retries: int = 3):
        """
        Khởi tạo API client
        
        Args:
            token: Token xác thực
            max_retries: Số lần thử lại tối đa khi gặp lỗi
        """
        self.token = token or config.get_token()
        self.base_url = config.BASE_URL
        self.domain = config.DOMAIN
        self.timeout = config.DEFAULT_TIMEOUT
        self.max_retries = max_retries
    
    def _get_headers(self, invoice_type: str) -> Dict[str, str]:
        """
        Tạo headers cho request
        
        Args:
            invoice_type: "sold" hoặc "purchase"
            
        Returns:
            Dict chứa headers
        """
        referer_path = config.REFERER_PATHS.get(
            invoice_type, 
            config.REFERER_PATHS["sold"]
        )
        
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": self.domain,
            "Referer": f"{self.domain}/{referer_path}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        invoice_type: str = "sold",
        timeout: Optional[int] = None,
        retry_on_500: bool = True
    ) -> Dict[str, Any]:
        """
        Thực hiện GET request với retry mechanism
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            invoice_type: Loại hóa đơn
            timeout: Timeout (giây)
            retry_on_500: Có retry khi gặp lỗi 500 không
            
        Returns:
            Dict với keys: success, data/error, status_code
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(invoice_type)
        timeout = timeout or self.timeout
        
        last_error = None
        
        # Retry loop
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff: 2s, 4s, 8s...
                    wait_time = 2 ** attempt
                    print(f"   ⏳ Đợi {wait_time}s trước khi thử lại...")
                    time.sleep(wait_time)
                    print(f"   🔄 Thử lại lần {attempt + 1}/{self.max_retries}...")
                
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout
                )
                
                # Nếu thành công hoặc lỗi không phải 500, return ngay
                if response.status_code != 500:
                    return self._handle_response(response)
                
                # Nếu là lỗi 500 và không retry, return luôn
                if not retry_on_500:
                    return self._handle_response(response)
                
                # Lỗi 500 và còn lần retry
                last_error = {
                    "status_code": 500,
                    "response_text": response.text[:500]
                }
                
                if attempt < self.max_retries - 1:
                    print(f"   ⚠️  Lỗi 500 từ server, đang thử lại...")
                
            except requests.exceptions.Timeout:
                last_error = {
                    "error": "Timeout",
                    "message": f"Server không phản hồi trong {timeout} giây"
                }
                
                if attempt < self.max_retries - 1:
                    print(f"   ⚠️  Timeout, đang thử lại...")
                
            except requests.exceptions.ConnectionError:
                last_error = {
                    "error": "Connection Error",
                    "message": "Không thể kết nối đến server"
                }
                
                if attempt < self.max_retries - 1:
                    print(f"   ⚠️  Lỗi kết nối, đang thử lại...")
                
            except Exception as e:
                last_error = {
                    "error": str(e),
                    "message": f"Lỗi không xác định: {str(e)}"
                }
                break  # Không retry với unknown errors
        
        # Đã hết số lần retry
        print(f"   ❌ Đã thử {self.max_retries} lần nhưng vẫn thất bại")
        
        return {
            "success": False,
            **last_error
        }
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Xử lý response từ API
        
        Args:
            response: Response object
            
        Returns:
            Dict chuẩn hóa kết quả
        """
        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "status_code": 200,
                    "url": response.url
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": "Invalid JSON",
                    "message": f"Không thể parse JSON: {str(e)}",
                    "status_code": 200,
                    "response_text": response.text[:500]
                }
        
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Unauthorized",
                "message": "Token không hợp lệ hoặc đã hết hạn. Vui lòng cập nhật TOKEN mới.",
                "status_code": 401
            }
        
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "Not Found",
                "message": "Endpoint không tồn tại hoặc không có dữ liệu",
                "status_code": 404,
                "response_text": response.text[:300]
            }
        
        elif response.status_code == 500:
            return {
                "success": False,
                "error": "Server Error",
                "message": "Lỗi từ server (500). Server của Tổng Cục Thuế đang gặp sự cố.",
                "status_code": 500,
                "response_text": response.text[:500],
                "suggestion": "Thử lại sau vài phút hoặc thay đổi khoảng thời gian query"
            }
        
        elif response.status_code == 503:
            return {
                "success": False,
                "error": "Service Unavailable",
                "message": "Server đang bảo trì hoặc quá tải",
                "status_code": 503
            }
        
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "message": f"Lỗi HTTP {response.status_code}",
                "status_code": response.status_code,
                "response_text": response.text[:500]
            }