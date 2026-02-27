"""
Login Script - Đăng nhập và lấy token tự động
"""

import sys
import os
from getpass import getpass

sys.path.insert(0, os.path.dirname(__file__))

from src.core import AuthManager


def main():
    print("=" * 80)
    print("🔐 ĐĂNG NHẬP HỆ THỐNG HÓA ĐƠN ĐIỆN TỬ")
    print("=" * 80)

    auth = AuthManager()

    while True:
        # Luôn tải captcha trước — key và ảnh phải đi cùng nhau
        print("\n📥 Đang tải captcha...")
        captcha_key = auth.save_captcha_image("captcha.svg")

        if not captcha_key:
            print("❌ Không tải được captcha, thử lại...")
            continue

        print("✅ File captcha.svg đã mở, hãy xem mã captcha")

        print("\n" + "=" * 80)
        print("📝 NHẬP THÔNG TIN ĐĂNG NHẬP")
        print("=" * 80)

        username = input("Mã số thuế / Username: ").strip()
        password = getpass("Mật khẩu (ẩn): ").strip()
        captcha_value = input("Mã captcha (nhìn file captcha.svg): ").strip()

        if not username or not password or not captcha_value:
            print("❌ Vui lòng nhập đầy đủ thông tin!")
            continue

        print("\n" + "=" * 80)

        # Đăng nhập với đúng key đi kèm ảnh vừa tải
        result = auth.login(username, password, captcha_value, captcha_key)

        print("=" * 80)

        if result["success"]:
            token = result["token"]

            print("\n🎉 ĐĂNG NHẬP THÀNH CÔNG!")
            print(f"   Token: {token[:60]}...")
            print(f"   Độ dài: {len(token)} ký tự")

            print("\nBạn có muốn cập nhật TOKEN vào file config.py không? (y/n)")
            if input("👉 ").strip().lower() == 'y':
                auth.update_config_file()
                print("\n✅ HOÀN TẤT! Bạn có thể chạy main.py ngay bây giờ!")
            else:
                print("\n💾 Token đã được lưu vào token.json")

            print("\n" + "=" * 80)
            print("📋 TOKEN:")
            print("=" * 80)
            print(token)
            print("=" * 80)
            break  # Thoát vòng lặp khi đăng nhập thành công

        else:
            print(f"\n❌ ĐĂNG NHẬP THẤT BẠI: {result.get('error', 'Unknown')}")
            if 'message' in result:
                print(f"   Chi tiết: {result['message'][:200]}")

            print("\nBạn có muốn thử lại không? (y/n)")
            if input("👉 ").strip().lower() != 'y':
                break
            # Vòng lặp tiếp → tải captcha MỚI tự động


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Đã hủy!")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()