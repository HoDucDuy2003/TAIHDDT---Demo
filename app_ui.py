"""
app_ui.py - Toàn bộ UI logic
Chứa: TextRedirector, LoginWindow, InvoiceApp, _show_login
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import os
from datetime import datetime, timedelta

from src.core import config,AuthManager
from src.services import InvoiceService
from src.utils import DataFormatter, FileHandler


class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, text):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, text, self.tag)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")
        self.widget.update_idletasks()

    def flush(self):
        pass


# ══════════════════════════════════════════════════════════
# MÀN HÌNH ĐĂNG NHẬP
# ══════════════════════════════════════════════════════════
class LoginWindow:
    def __init__(self, root: tk.Tk, on_success):
        self.root = root
        self.on_success = on_success

        self.root.title("🔐 Đăng nhập – Hệ thống Hóa đơn Điện tử")
        self.root.geometry("460x540")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f4f8")

        self.colors = {
            "bg":        "#f0f4f8",
            "card":      "#ffffff",
            "primary":   "#2563eb",
            "primary_h": "#1d4ed8",
            "danger":    "#dc2626",
            "border":    "#d1d5db",
            "text":      "#1f2937",
            "subtext":   "#6b7280",
            "header_bg": "#1e3a5f",
        }

        sys.path.insert(0, os.path.dirname(__file__))
        self.auth = AuthManager()
        self.captcha_key = None

        self._build_ui()
        self._load_captcha()

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=self.colors["header_bg"], height=64)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="🏦  HỆ THỐNG HÓA ĐƠN ĐIỆN TỬ",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["header_bg"],
            fg="white",
        ).pack(side=tk.LEFT, padx=20, pady=14)

        # Card
        card = tk.Frame(
            self.root,
            bg=self.colors["card"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        card.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        tk.Label(
            card,
            text="Đăng nhập",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"],
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, padx=20)

        # Username
        self._label(card, "👤  Mã số thuế / Username")
        self.username_var = tk.StringVar()
        self._entry(card, self.username_var).pack(fill=tk.X, padx=20, pady=(0, 10))

        # Password
        self._label(card, "🔒  Mật khẩu")
        pw_frame = tk.Frame(card, bg=self.colors["card"])
        pw_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.password_var = tk.StringVar()
        self.pw_entry = tk.Entry(
            pw_frame,
            textvariable=self.password_var,
            show="•",
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["primary"],
            bg="white",
            fg=self.colors["text"],
        )
        self.pw_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, ipadx=6)
        self.show_pw = False
        self.eye_btn = tk.Button(
            pw_frame, text="👁", font=("Segoe UI", 10),
            command=self._toggle_pw,
            relief=tk.FLAT, bg=self.colors["border"],
            activebackground="#e5e7eb", cursor="hand2", padx=8,
        )
        self.eye_btn.pack(side=tk.LEFT, padx=(4, 0))

        # Captcha image row
        self._label(card, "🖼  Mã Captcha")
        captcha_row = tk.Frame(card, bg=self.colors["card"])
        captcha_row.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.captcha_status = tk.StringVar(value="⏳ Đang tải captcha...")
        self.captcha_label = tk.Label(
            captcha_row,
            textvariable=self.captcha_status,
            font=("Segoe UI", 9),
            bg="#f8fafc",
            fg=self.colors["subtext"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            height=2,
            cursor="hand2",
        )
        self.captcha_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, ipadx=8)
        self.captcha_label.bind("<Button-1>", lambda e: self._open_captcha_file())

        tk.Button(
            captcha_row,
            text="🔄",
            font=("Segoe UI", 11),
            command=self._reload_captcha,
            relief=tk.FLAT,
            bg=self.colors["border"],
            activebackground="#e5e7eb",
            cursor="hand2",
            padx=10,
        ).pack(side=tk.LEFT, padx=(6, 0))

        # Captcha input
        self._label(card, "✏️  Nhập mã captcha")
        self.captcha_var = tk.StringVar()
        captcha_entry = self._entry(card, self.captcha_var)
        captcha_entry.pack(fill=tk.X, padx=20, pady=(0, 4))
        captcha_entry.bind("<Return>", lambda e: self._on_login())

        tk.Label(
            card,
            text="💡 Click vào ô captcha để mở ảnh xem mã",
            font=("Segoe UI", 8),
            bg=self.colors["card"],
            fg=self.colors["subtext"],
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # Nút đăng nhập
        self.login_btn = tk.Button(
            card,
            text="🔐  Đăng nhập",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["primary_h"],
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_login,
            pady=10,
        )
        self.login_btn.pack(fill=tk.X, padx=20, pady=(0, 8))

        # Status / lỗi
        self.status_var = tk.StringVar(value="")
        tk.Label(
            card,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg=self.colors["card"],
            fg=self.colors["danger"],
            wraplength=380,
        ).pack(padx=20, pady=(0, 10))

    def _label(self, parent, text):
        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["card"],
            fg=self.colors["subtext"],
        ).pack(anchor="w", padx=20, pady=(6, 2))

    def _entry(self, parent, var):
        return tk.Entry(
            parent,
            textvariable=var,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["primary"],
            bg="white",
            fg=self.colors["text"],
        )

    def _toggle_pw(self):
        self.show_pw = not self.show_pw
        self.pw_entry.config(show="" if self.show_pw else "•")
        self.eye_btn.config(text="🙈" if self.show_pw else "👁")

    def _load_captcha(self):
        self.captcha_status.set("⏳ Đang tải captcha...")
        threading.Thread(target=self._fetch_captcha, daemon=True).start()

    def _fetch_captcha(self):
        self.captcha_key = self.auth.save_captcha_image("captcha.svg")
        if self.captcha_key:
            self.root.after(0, lambda: self.captcha_status.set(
                "✅ Captcha đã tải — click để xem ảnh"
            ))
        else:
            self.root.after(0, lambda: self.captcha_status.set(
                "❌ Tải captcha thất bại — nhấn 🔄 để thử lại"
            ))

    def _reload_captcha(self):
        self.captcha_var.set("")
        self._load_captcha()

    def _open_captcha_file(self):
        try:
            os.startfile("captcha.svg")
        except Exception:
            pass

    def _on_login(self):
        username      = self.username_var.get().strip()
        password      = self.password_var.get().strip()
        captcha_value = self.captcha_var.get().strip()

        if not username:
            self.status_var.set("❌ Vui lòng nhập mã số thuế / username!")
            return
        if not password:
            self.status_var.set("❌ Vui lòng nhập mật khẩu!")
            return
        if not captcha_value:
            self.status_var.set("❌ Vui lòng nhập mã captcha!")
            return
        if not self.captcha_key:
            self.status_var.set("❌ Chưa có captcha key, nhấn 🔄 để tải lại!")
            return

        self.login_btn.config(state="disabled", text="⏳ Đang đăng nhập...")
        self.status_var.set("")

        threading.Thread(
            target=self._do_login,
            args=(username, password, captcha_value),
            daemon=True,
        ).start()

    def _do_login(self, username, password, captcha_value):
        result = self.auth.login(username, password, captcha_value, self.captcha_key)
        if result["success"]:
            config.TOKEN = result["token"]
            self.root.after(0, lambda: self.on_success(result["token"]))
        else:
            msg = result.get("message", result.get("error", "Lỗi không xác định"))
            self.root.after(0, lambda: self._on_login_failed(msg))

    def _on_login_failed(self, msg):
        self.status_var.set(f"❌ {msg[:120]}")
        self.login_btn.config(state="normal", text="🔐  Đăng nhập")
        self._reload_captcha()


# ══════════════════════════════════════════════════════════
# MÀN HÌNH CHÍNH
# ══════════════════════════════════════════════════════════
class InvoiceApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🏦 Hệ thống Hóa đơn Điện tử v2.0")
        self.root.geometry("900x650")
        self.root.resizable(True, True)
        self.root.configure(bg="#f0f4f8")

        self.colors = {
            "bg":        "#f0f4f8",
            "card":      "#ffffff",
            "primary":   "#2563eb",
            "primary_h": "#1d4ed8",
            "success":   "#16a34a",
            "danger":    "#dc2626",
            "border":    "#d1d5db",
            "text":      "#1f2937",
            "subtext":   "#6b7280",
            "header_bg": "#1e3a5f",
        }

        self._build_ui()
        self._redirect_output()
        self._load_defaults()

    def _build_ui(self):
        self._build_header()
        self._build_form_card()
        self._build_run_button()
        self._build_log_area()
        self._build_statusbar()

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.colors["header_bg"], height=64)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🏦  HỆ THỐNG HÓA ĐƠN ĐIỆN TỬ",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["header_bg"],
            fg="white",
        ).pack(side=tk.LEFT, padx=20, pady=14)

        tk.Label(
            header,
            text="v2.0",
            font=("Segoe UI", 10),
            bg=self.colors["header_bg"],
            fg="#93c5fd",
        ).pack(side=tk.LEFT, pady=18)

        tk.Button(
            header,
            text="🚪 Đăng xuất",
            font=("Segoe UI", 9),
            bg="#374151",
            fg="white",
            activebackground="#4b5563",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_logout,
            padx=10,
            pady=6,
        ).pack(side=tk.RIGHT, padx=16, pady=14)

    def _build_form_card(self):
        outer = tk.Frame(self.root, bg=self.colors["bg"])
        outer.pack(fill=tk.X, padx=20, pady=(16, 0))

        card = tk.Frame(
            outer,
            bg=self.colors["card"],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        card.pack(fill=tk.X)

        tk.Label(
            card,
            text="⚙️  Thông số truy vấn",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"],
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 4))

        ttk.Separator(card, orient="horizontal").grid(
            row=1, column=0, columnspan=4, sticky="ew", padx=16
        )

        self._form_label(card, "🔑  Token xác thực", row=2, col=0)
        self.token_var = tk.StringVar()
        token_frame = tk.Frame(card, bg=self.colors["card"])
        token_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=(16, 8), pady=(0, 12))
        card.columnconfigure(0, weight=3)
        card.columnconfigure(1, weight=1)
        card.columnconfigure(2, weight=1)
        card.columnconfigure(3, weight=1)

        self.token_entry = tk.Entry(
            token_frame,
            textvariable=self.token_var,
            font=("Consolas", 9),
            show="•",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["primary"],
            bg="white",
            fg=self.colors["text"],
        )
        self.token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, ipadx=6)

        self.show_token = False
        self.eye_btn = tk.Button(
            token_frame,
            text="👁",
            font=("Segoe UI", 10),
            command=self._toggle_token_visibility,
            relief=tk.FLAT,
            bg=self.colors["border"],
            activebackground="#e5e7eb",
            cursor="hand2",
            padx=8,
        )
        self.eye_btn.pack(side=tk.LEFT, padx=(4, 0))

        tk.Button(
            token_frame,
            text="✕",
            font=("Segoe UI", 10),
            command=lambda: self.token_var.set(""),
            relief=tk.FLAT,
            bg=self.colors["border"],
            activebackground="#e5e7eb",
            cursor="hand2",
            padx=8,
        ).pack(side=tk.LEFT, padx=(4, 0))

        self._form_label(card, "📅  Ngày bắt đầu", row=4, col=0)
        self._form_label(card, "📅  Ngày kết thúc", row=4, col=1)
        self._form_label(card, "📄  Loại hóa đơn",  row=4, col=2)

        self.start_date_var = tk.StringVar()
        self._date_entry(card, self.start_date_var, row=5, col=0)

        self.end_date_var = tk.StringVar()
        self._date_entry(card, self.end_date_var, row=5, col=1)

        self.invoice_type_var = tk.StringVar(value="purchase")
        type_frame = tk.Frame(card, bg=self.colors["card"])
        type_frame.grid(row=5, column=2, sticky="ew", padx=(8, 16), pady=(0, 16))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.TCombobox",
            fieldbackground="white",
            background="white",
            selectbackground=self.colors["primary"],
            selectforeground="white",
        )

        self.type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.invoice_type_var,
            values=["purchase", "sold"],
            state="readonly",
            style="Custom.TCombobox",
            font=("Segoe UI", 10),
        )
        self.type_combo.pack(fill=tk.X, ipady=5)
        self.type_combo["values"] = ["purchase  —  Mua vào", "sold  —  Bán ra"]
        self.type_combo.set("purchase  —  Mua vào")

    def _form_label(self, parent, text, row, col):
        padx = (16, 8) if col == 0 else (8, 8)
        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["card"],
            fg=self.colors["subtext"],
        ).grid(row=row, column=col, sticky="w", padx=padx, pady=(8, 2))

    def _date_entry(self, parent, var, row, col):
        padx = (16, 8) if col == 0 else (8, 8)
        frame = tk.Frame(parent, bg=self.colors["card"])
        frame.grid(row=row, column=col, sticky="ew", padx=padx, pady=(0, 16))

        tk.Entry(
            frame,
            textvariable=var,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["primary"],
            bg="white",
            fg=self.colors["text"],
            width=14,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, ipadx=6)

    def _build_run_button(self):
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"])
        btn_frame.pack(fill=tk.X, padx=20, pady=(10, 0))

        self.run_btn = tk.Button(
            btn_frame,
            text="▶   Chạy – Tải hóa đơn",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["primary_h"],
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_run,
            padx=24,
            pady=10,
        )
        self.run_btn.pack(side=tk.LEFT)

        tk.Button(
            btn_frame,
            text="🗑  Xóa log",
            font=("Segoe UI", 10),
            bg="#e5e7eb",
            fg=self.colors["text"],
            activebackground="#d1d5db",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._clear_log,
            padx=14,
            pady=10,
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _build_log_area(self):
        log_frame = tk.Frame(self.root, bg=self.colors["bg"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 4))

        tk.Label(
            log_frame,
            text="📋  Log kết quả",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["subtext"],
        ).pack(anchor="w")

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            state="disabled",
            wrap=tk.WORD,
        )
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.log_box.tag_config("stdout",  foreground="#e2e8f0")
        self.log_box.tag_config("stderr",  foreground="#f87171")
        self.log_box.tag_config("success", foreground="#4ade80")
        self.log_box.tag_config("info",    foreground="#60a5fa")
        self.log_box.tag_config("warn",    foreground="#fbbf24")

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Sẵn sàng")
        bar = tk.Frame(self.root, bg="#e5e7eb", height=24)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Label(
            bar,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg="#e5e7eb",
            fg=self.colors["subtext"],
        ).pack(side=tk.LEFT, padx=12)

    def _redirect_output(self):
        sys.stdout = TextRedirector(self.log_box, "stdout")
        sys.stderr = TextRedirector(self.log_box, "stderr")

    def _toggle_token_visibility(self):
        self.show_token = not self.show_token
        self.token_entry.config(show="" if self.show_token else "•")
        self.eye_btn.config(text="🙈" if self.show_token else "👁")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")

    def _load_defaults(self):
        today = datetime.now()
        self.end_date_var.set(today.strftime("%d/%m/%Y"))
        self.start_date_var.set((today - timedelta(days=30)).strftime("%d/%m/%Y"))

        try:
            if config.TOKEN and config.TOKEN != "DÁN_TOKEN_MỚI_VÀO_ĐÂY":
                self.token_var.set(config.TOKEN)
                self._log("ℹ️  Đã tải token từ đăng nhập\n", "info")
        except Exception:
            pass

    def _log(self, msg: str, tag: str = "stdout"):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, msg, tag)
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def _set_status(self, text: str):
        self.status_var.set(text)
        self.root.update_idletasks()

    def _get_invoice_type(self) -> str:
        return "purchase" if "purchase" in self.type_combo.get() else "sold"

    def _validate(self) -> bool:
        token = self.token_var.get().strip()
        start = self.start_date_var.get().strip()
        end   = self.end_date_var.get().strip()

        if not token:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Token xác thực!")
            return False

        fmt = "%d/%m/%Y"
        try:
            start_dt = datetime.strptime(start, fmt)
        except ValueError:
            messagebox.showerror("Sai định dạng", f"Ngày bắt đầu không hợp lệ: '{start}'")
            return False
        try:
            end_dt = datetime.strptime(end, fmt)
        except ValueError:
            messagebox.showerror("Sai định dạng", f"Ngày kết thúc không hợp lệ: '{end}'")
            return False

        if start_dt > end_dt:
            messagebox.showerror("Lỗi ngày", "Ngày bắt đầu phải trước ngày kết thúc!")
            return False

        return True

    def _on_logout(self):
        if messagebox.askyesno("Đăng xuất", "Bạn có muốn đăng xuất không?"):
            config.TOKEN = ""
            self.root.withdraw()
            show_login(self.root)

    def _on_run(self):
        if not self._validate():
            return
        self.run_btn.config(state="disabled", text="⏳  Đang chạy...")
        self._set_status("🔄 Đang tải hóa đơn...")
        threading.Thread(target=self._run_task, daemon=True).start()

    def _run_task(self):
        try:
            token        = self.token_var.get().strip()
            start_date   = self.start_date_var.get().strip()
            end_date     = self.end_date_var.get().strip()
            invoice_type = self._get_invoice_type()

            self._log("\n" + "=" * 70 + "\n", "info")
            self._log("🚀 Bắt đầu lấy hóa đơn\n", "info")
            self._log(f"   📅 Từ: {start_date}  →  {end_date}\n", "info")
            self._log(f"   📄 Loại: {'Mua vào' if invoice_type == 'purchase' else 'Bán ra'}\n", "info")
            self._log(f"   🔑 Token: {token[:40]}...\n", "info")
            self._log("=" * 70 + "\n\n", "info")

            service      = InvoiceService()
            file_handler = FileHandler()

            result = service.get_all_invoices_with_details(
                invoice_type=invoice_type,
                start_date=start_date,
                end_date=end_date,
                size=50,
                return_models=True,
            )

            if result.get("success"):
                invoices = result["all_invoices_with_details"]
                summary  = result.get("summary", {})

                self._log("\n📊 TỔNG KẾT:\n", "success")
                self._log(f"   • Tổng hóa đơn   : {summary.get('total_invoices', len(invoices))}\n", "success")
                self._log(f"   • Số trang đã lấy : {summary.get('pages_fetched', '-')}\n", "success")
                if "details_success" in summary:
                    self._log(f"   • Chi tiết OK    : {summary['details_success']}\n", "success")
                    self._log(f"   • Chi tiết lỗi   : {summary['details_failed']}\n", "warn")

                self._log(f"\n💾 Đang lưu {len(invoices)} hóa đơn...\n", "info")
                json_file  = file_handler.save_to_json(invoices, invoice_type=invoice_type)
                excel_file = file_handler.save_to_excel(
                    [inv.to_dict() for inv in invoices],
                    invoice_type=invoice_type,
                    start_date=start_date,
                    end_date=end_date,
                    selected_columns=DataFormatter.DEFAULT_EXPORT_COLUMNS,
                    column_names=DataFormatter.VIETNAMESE_COLUMN_NAMES,
                )

                self._log("\n✅ HOÀN THÀNH!\n", "success")
                self._log(f"   📁 JSON : {json_file}\n", "success")
                self._log(f"   📁 EXCEL: {excel_file}\n", "success")
                self._set_status(f"✅ Hoàn thành — {len(invoices)} hóa đơn | {os.path.basename(excel_file)}")

            else:
                err = result.get("error", "Unknown")
                self._log(f"\n❌ Lỗi: {err}\n", "stderr")
                self._log(f"   {result.get('message', '')[:300]}\n", "stderr")
                self._set_status(f"❌ Lỗi: {err}")

        except Exception as exc:
            import traceback
            self._log(f"\n❌ Exception: {exc}\n", "stderr")
            self._log(traceback.format_exc(), "stderr")
            self._set_status(f"❌ Lỗi: {exc}")

        finally:
            self.root.after(0, lambda: self.run_btn.config(
                state="normal", text="▶   Chạy – Tải hóa đơn"
            ))


# ══════════════════════════════════════════════════════════
# ĐIỀU PHỐI LOGIN → MAIN
# ══════════════════════════════════════════════════════════
def show_login(root: tk.Tk):
    """Hiện màn hình login, callback chuyển sang màn hình chính"""
    for widget in root.winfo_children():
        widget.destroy()

    def on_success(token: str):
        for widget in root.winfo_children():
            widget.destroy()
        root.deiconify()
        InvoiceApp(root)

    LoginWindow(root, on_success=on_success)