"""
Authentication Module
Xử lý đăng nhập và lấy token tự động
Reuse config và session từ các module có sẵn
"""

import os

import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime

from ..core.config import config


class AuthManager:
    """Quản lý authentication với hệ thống hóa đơn điện tử"""
    
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.token_info = None
    
    def login(
        self, 
        username: str, 
        password: str,
        captcha_value: str,
        captcha_key: str
    ) -> Dict[str, Any]:
        """
        Đăng nhập và lấy token
        
        Args:
            username: Mã số thuế hoặc username
            password: Mật khẩu
            captcha_value: Chữ người dùng nhập từ ảnh captcha
            captcha_key: Key lấy từ get_captcha_image()
            
        Returns:
            Dict với token và thông tin
        """
        
        # Sử dụng config có sẵn
        login_url = f"{config.BASE_URL}/security-taxpayer/authenticate"
        
        payload = {
            "username": username,
            "password": password,
            "cvalue": captcha_value,
            "ckey": captcha_key       # key đính kèm theo captcha
        }
        
        # Headers đơn giản, chỉ cần thiết cho login
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": config.DOMAIN,
            "Referer": f"{config.DOMAIN}/login",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }  
        try:
            response = self.session.post(
                login_url,
                json=payload,
                headers=headers,
                timeout=config.DEFAULT_TIMEOUT
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Lấy token từ response
                token = data.get("token")
                
                if token:
                    self.token = token
                    self.token_info = {
                        "token": token,
                        "username": username,
                        "login_time": datetime.now().isoformat(),
                        "raw_response": data
                    }
                    
                    print(f"\n✅ ĐĂNG NHẬP THÀNH CÔNG!")
                    print(f"   Token: {token[:50]}...")
                    
                    # Lưu token vào file
                    self._save_token_to_file()
                    
                    return {
                        "success": True,
                        "token": token,
                        "message": "Đăng nhập thành công",
                        "data": data
                    }
                else:
                    print(f"\n⚠️  Không tìm thấy token trong response")
                    print(f"   Response keys: {list(data.keys())}")
                    
                    return {
                        "success": False,
                        "error": "No token in response",
                        "data": data
                    }
            
            else:
                error_msg = response.text
                print(f"\n❌ ĐĂNG NHẬP THẤT BẠI!")
                print(f"   Status: {response.status_code}")
                print(f"   Error: {error_msg[:200]}")
                
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "message": error_msg
                }
                
        except Exception as e:
            print(f"\n❌ LỖI: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_captcha_image(self) -> Optional[Dict[str, Any]]:
        """
        Lấy ảnh captcha từ API
        
        Returns:
            Dict gồm 'key' và 'image_bytes' hoặc None
        """
        captcha_url = f"{config.BASE_URL}/captcha"
        
        try:
            response = self.session.get(captcha_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                key = data["key"]
                svg_string = data["content"]

                # Lưu thẳng SVG, không cần convert
                svg_bytes = svg_string.encode("utf-8")

                print(f"✅ Đã lấy captcha (key: {key})")

                return {
                    "key": key,
                    "image_bytes": svg_bytes,
                    "extension": "svg"      # để biết lưu đuôi gì
                }
                
        except Exception as e:
            print(f"Lỗi lấy captcha: {e}")
        
        return None


    def save_captcha_image(self, filename: str = "captcha.svg") -> Optional[str]:
        """
        Lưu ảnh captcha, trả về captcha key

        Returns:
            Captcha key nếu thành công, None nếu thất bại
        """
        captcha = self.get_captcha_image()
        
        if captcha:
            with open(filename, "wb") as f:
                f.write(captcha["image_bytes"])
            print(f"✅ Đã lưu captcha: {filename}")

            # Mở file tự động
            try:
                os.startfile(filename)          # Windows
            except AttributeError:
                import subprocess
                subprocess.run(["open", filename])  # macOS
            
            return captcha["key"]
        
        return None
    
    def _save_token_to_file(self, filename: str = "token.json"):
        """
        Lưu token vào file JSON
        
        Args:
            filename: Tên file
        """
        if self.token_info:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.token_info, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Đã lưu token vào: {filename}")
    
    def load_token_from_file(self, filename: str = "token.json") -> Optional[str]:
        """
        Load token từ file
        
        Args:
            filename: Tên file
            
        Returns:
            Token string hoặc None
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            token = data.get("token")
            
            if token:
                self.token = token
                self.token_info = data
                
                login_time = data.get("login_time", "")
                print(f"✅ Đã load token từ file")
                print(f"   Login time: {login_time}")
                print(f"   Token: {token[:50]}...")
                
                return token
        
        except FileNotFoundError:
            print(f"⚠️  File {filename} không tồn tại")
        except Exception as e:
            print(f"⚠️  Lỗi load token: {e}")
        
        return None
    
    def get_token(self) -> Optional[str]:
        """
        Lấy token hiện tại
        
        Returns:
            Token string hoặc None
        """
        return self.token
    
    def update_config_file(self, config_file: str = "src/core/config.py"):
        """
        Cập nhật TOKEN vào file config.py
        
        Args:
            config_file: Đường dẫn file config
        """
        if not self.token:
            print("⚠️  Chưa có token để cập nhật")
            return
        
        try:
            # Đọc file config
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Tìm và thay thế dòng TOKEN
            lines = content.split('\n')
            updated = False
            
            for i, line in enumerate(lines):
                if line.strip().startswith('TOKEN') and '=' in line:
                    # Thay thế token, giữ nguyên format
                    indent = len(line) - len(line.lstrip())
                    lines[i] = ' ' * indent + f'TOKEN: str = "{self.token}"'
                    updated = True
                    break
            
            if updated:
                # Ghi lại file
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write('\n'.join(lines))
                
                print(f"✅ Đã cập nhật TOKEN vào {config_file}")
            else:
                print(f"⚠️  Không tìm thấy dòng TOKEN trong {config_file}")
                print(f"💡 Vui lòng thêm thủ công vào class Config:")
                print(f"    TOKEN: str = \"{self.token}\"")
                
        except Exception as e:
            print(f"⚠️  Lỗi cập nhật config: {e}")
            print(f"💡 Token của bạn:")
            print(f"    {self.token}")