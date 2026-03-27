import ctypes
import ctypes.wintypes
import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
from threading import Thread
import time
import winreg
import pystray
from PIL import Image, ImageDraw
import os
import sys

AUTOSTART_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "WindowHotkeyTool"

class WindowHotkey:
    def __init__(self, root):
        self.root = root
        self.root.title("窗口快捷打开工具 v2.2")
        self.root.geometry("550x380")
        self.root.resizable(0,0)
        self.running = False
        self.hotkey_list = []
        self.tray_icon = None

        self.create_tray_icon()
        tk.Label(root, text="多窗口快捷绑定工具", font=("微软雅黑", 12, "bold")).place(x=180, y=10)
        tk.Label(root, text="窗口标题关键词", font=("微软雅黑", 10)).place(x=30, y=50)
        tk.Label(root, text="全局快捷键", font=("微软雅黑", 10)).place(x=230, y=50)
        tk.Label(root, text="操作", font=("微软雅黑", 10)).place(x=430, y=50)

        self.list_frame = tk.Frame(root)
        self.list_frame.place(x=20, y=80, width=510, height=180)
        self.rows = []
        self.add_row()

        ttk.Button(root, text="+ 新增一行", command=self.add_row).place(x=30, y=270, width=100)
        ttk.Button(root, text="- 删除最后一行", command=self.del_row).place(x=140, y=270, width=120)

        self.btn_start = ttk.Button(root, text="启动监听", command=self.start)
        self.btn_start.place(x=280, y=270, width=100)
        self.btn_stop = ttk.Button(root, text="停止监听", command=self.stop, state="disabled")
        self.btn_stop.place(x=390, y=270, width=100)

        self.stat = tk.Label(root, text="状态：未运行", fg="red", font=("微软雅黑", 10))
        self.stat.place(x=30, y=310)

        self.autostart_var = tk.BooleanVar(value=self.check_autostart())
        self.autostart_check = ttk.Checkbutton(
            root, text="开机自动启动", variable=self.autostart_var, command=self.toggle_autostart
        )
        self.autostart_check.place(x=30, y=340)

        tk.Label(root, text="关闭窗口将最小化到系统托盘", fg="gray", font=("微软雅黑", 9)).place(x=200, y=340)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color=(0, 120, 215))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
        self.tray_icon = pystray.Icon(
            "WindowHotkey", image, "窗口快捷工具",
            menu=pystray.Menu(
                pystray.MenuItem("打开主界面", self.show_window),
                pystray.MenuItem("退出程序", self.exit_app)
            )
        )

    def minimize_to_tray(self):
        self.root.withdraw()
        if not self.tray_icon.visible:
            Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def exit_app(self):
        self.stop()
        self.tray_icon.stop()
        self.root.destroy()
        os._exit(0)

    def check_autostart(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return value == os.path.abspath(sys.argv[0])
        except:
            return False

    def toggle_autostart(self):
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        if self.autostart_var.get():
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, os.path.abspath(sys.argv[0]))
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except:
                pass
        winreg.CloseKey(key)

    def add_row(self):
        row = len(self.rows)
        y = row * 35
        kw_entry = ttk.Entry(self.list_frame, width=25)
        kw_entry.place(x=0, y=y, height=25)
        hk_entry = ttk.Entry(self.list_frame, width=20, state="readonly")
        hk_entry.place(x=200, y=y, height=25)

        def record_hotkey():
            hk_entry.config(state="normal")
            hk_entry.delete(0, tk.END)
            hk_entry.insert(0, "请按下快捷键...")
            hk_entry.config(state="readonly")
            self.root.update()
            hotkey = keyboard.read_hotkey(suppress=False)
            hk_entry.config(state="normal")
            hk_entry.delete(0, tk.END)
            hk_entry.insert(0, hotkey)
            hk_entry.config(state="readonly")

        record_btn = ttk.Button(self.list_frame, text="录制", command=record_hotkey, width=6)
        record_btn.place(x=380, y=y, height=25)
        self.rows.append({"kw": kw_entry, "hk": hk_entry, "btn": record_btn})

    def del_row(self):
        if len(self.rows) > 1:
            row = self.rows.pop()
            row["kw"].destroy()
            row["hk"].destroy()
            row["btn"].destroy()

    def find_window(self, key):
        res = None
        def cb(hwnd, _):
            nonlocal res
            l = self.user32.GetWindowTextLengthW(hwnd)
            if l == 0:
                return True
            buf = ctypes.create_unicode_buffer(l + 1)
            self.user32.GetWindowTextW(hwnd, buf, l + 1)
            t = buf.value
            if key.lower() in t.lower() and self.user32.IsWindowVisible(hwnd):
                res = hwnd
                return False
            return True
        fp = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        self.user32.EnumWindows(fp(cb), 0)
        return res

    # ✅ 修复：保持最大化窗口不变小
    def activate_window(self, hwnd):
        if not hwnd:
            return
        SW_SHOW = 5
        SW_RESTORE = 9
        is_minimized = self.user32.IsIconic(hwnd)
        if is_minimized:
            self.user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            self.user32.ShowWindow(hwnd, SW_SHOW)
        self.user32.SetForegroundWindow(hwnd)

    def listen_worker(self):
        for row in self.rows:
            kw = row["kw"].get().strip()
            hk = row["hk"].get().strip()
            if not kw or not hk:
                continue
            def callback(k=kw):
                hwnd = self.find_window(k)
                self.activate_window(hwnd)
            try:
                keyboard.add_hotkey(hk, callback)
                self.hotkey_list.append({"hk": hk, "cb": callback})
            except Exception as e:
                pass
        while self.running:
            time.sleep(0.1)
        for item in self.hotkey_list:
            try:
                keyboard.remove_hotkey(item["hk"])
            except:
                pass
        self.hotkey_list.clear()

    def start(self):
        for row in self.rows:
            kw = row["kw"].get().strip()
            hk = row["hk"].get().strip()
            if kw and not hk:
                messagebox.showwarning("提示", f"请为「{kw}」录制快捷键")
                return
            if hk and not kw:
                messagebox.showwarning("提示", f"请为快捷键「{hk}」填写窗口关键词")
                return
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.stat.config(text="状态：运行中（后台监听）", fg="green")
        Thread(target=self.listen_worker, daemon=True).start()

    def stop(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.stat.config(text="状态：已停止", fg="red")

if __name__ == "__main__":
    # ✅ 修复：删除了导致双开的管理员重复启动代码
    root = tk.Tk()
    app = WindowHotkey(root)
    root.mainloop()