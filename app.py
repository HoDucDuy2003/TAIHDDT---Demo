"""
app.py - Entry point
Chạy file này để khởi động ứng dụng
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app_ui import show_login


def main():
    root = tk.Tk()

    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass

    show_login(root)
    root.mainloop()


if __name__ == "__main__":
    main()