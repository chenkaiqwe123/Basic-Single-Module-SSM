#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple GUI to select a screen region, run OCR, and press the detected key.
Optimized with optional MSS screenshot and basic image preprocessing.
"""

import cv2
import numpy as np
import pyautogui
import pytesseract
import threading
import time
import sys
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image
from queue import SimpleQueue
from datetime import datetime

try:
    from mss import mss
    USE_MSS = True
except Exception:
    USE_MSS = False

# ---------- configurable ----------
SCAN_INTERVAL = 0.5
LEGAL_CHARS = set("123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
TESS_PATH_WIN = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
TESS_CONFIG = (
    "--oem 3 --psm 8 "
    "-c tessedit_char_whitelist=123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
)
# ---------------------------------

roi_coords: tuple[int, int, int, int] | None = None
running = False
msg_q = SimpleQueue()

_sct = mss() if USE_MSS else None


def grab_screen(region: tuple[int, int, int, int]) -> np.ndarray:
    """Capture a region of the screen and return BGR image."""
    if USE_MSS:
        x, y, w, h = region
        monitor = {"left": x, "top": y, "width": w, "height": h}
        img = np.array(_sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(
        np.array(pyautogui.screenshot(region=region)),
        cv2.COLOR_RGB2BGR,
    )


def detect_char(frame_bgr: np.ndarray) -> str | None:
    """Return first legal character detected in the image."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = pytesseract.image_to_string(Image.fromarray(binary), config=TESS_CONFIG)
    for ch in text.upper():
        if ch in LEGAL_CHARS:
            return ch
    return None


def detection_loop():
    global running, roi_coords
    while running:
        x, y, w, h = roi_coords
        frame = grab_screen((x, y, w, h))
        ch = detect_char(frame)
        if ch:
            key = ch.lower() if ch.isalpha() else ch
            pyautogui.press(key)
            msg_q.put(f"{datetime.now():%H:%M:%S}  检测到 → {ch}  , 已按键 {key}")
        time.sleep(SCAN_INTERVAL)


def select_roi() -> tuple[int, int, int, int]:
    w, h = pyautogui.size()
    full_bgr = grab_screen((0, 0, w, h))
    cv2.namedWindow("框选区域（回车确认，ESC 取消）", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        "框选区域（回车确认，ESC 取消）", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
    )
    roi = cv2.selectROI(
        "框选区域（回车确认，ESC 取消）", full_bgr, showCrosshair=True, fromCenter=False
    )
    cv2.destroyAllWindows()
    x, y, w, h = map(int, roi)
    if w == 0 or h == 0:
        sys.exit("❌ 未选择有效区域，程序退出。")
    return x, y, w, h


# ---------------- GUI ----------------

def on_start():
    global roi_coords, running
    root.withdraw()
    roi_coords = select_roi()
    running = True
    threading.Thread(target=detection_loop, daemon=True).start()
    btn_start.pack_forget()
    btn_stop.pack(pady=8)
    root.deiconify()
    append_msg(f"{datetime.now():%H:%M:%S}  ✅ 开始检测  ROI={roi_coords}")


def on_stop():
    global running
    running = False
    append_msg(f"{datetime.now():%H:%M:%S}  🟥 检测停止")
    time.sleep(0.3)
    root.destroy()


def append_msg(msg: str):
    info_box.configure(state="normal")
    info_box.insert(tk.END, msg + "\n")
    info_box.see(tk.END)
    info_box.configure(state="disabled")


def poll_queue():
    while not msg_q.empty():
        append_msg(msg_q.get())
    root.after(100, poll_queue)


def ensure_tesseract():
    if sys.platform.startswith("win"):
        pytesseract.pytesseract.tesseract_cmd = TESS_PATH_WIN


if __name__ == "__main__":
    ensure_tesseract()

    root = tk.Tk()
    root.title("OCR → 自动按键")
    root.geometry("360x300")
    root.resizable(False, False)

    tk.Label(
        root,
        text="流程：开始 → 框选区域 → 实时OCR → 自动按键\n(识别 1-9 及 A-Z)",
        justify="center",
    ).pack(pady=8)

    btn_start = tk.Button(root, text="开始", width=12, command=on_start)
    btn_start.pack(pady=4)

    btn_stop = tk.Button(root, text="停止", width=12, command=on_stop)
    btn_stop.pack_forget()

    info_box = scrolledtext.ScrolledText(root, height=8, state="disabled")
    info_box.pack(fill="both", padx=10, pady=10, expand=True)

    root.after(100, poll_queue)
    root.mainloop()
