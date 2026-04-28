#!/usr/bin/env python3
"""
CL2000 → Vector ASC Converter
Converts Intrepid/CL2000 logger TXT files to Vector CANalyzer/CANoe .asc format.
"""

import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime


# ─────────────────────────────────────────────
#  Core conversion logic
# ─────────────────────────────────────────────

def parse_ts(ts_str):
    """Parse CL2000 timestamp DDTHHMMSSmmm -> float seconds."""
    m = re.match(r'(\d{1,2})T(\d{2})(\d{2})(\d{2})(\d{3})', ts_str)
    if not m:
        return None
    day, H, M, S, ms = (int(x) for x in m.groups())
    return day * 86400 + H * 3600 + M * 60 + S + ms / 1000.0


def collect_header_info(filepath):
    info = {}
    with open(filepath, 'r', errors='replace') as f:
        for line in f:
            if not line.startswith('#'):
                break
            m = re.match(r'#\s*(.+?):\s*(.+)', line)
            if m:
                info[m.group(1).strip()] = m.group(2).strip().strip('"')
    return info


def convert(input_files, output_file, progress_cb=None, log_cb=None):
    """
    Convert a list of CL2000 TXT files to a single Vector ASC file.

    progress_cb(pct: float)  – called with 0..100
    log_cb(msg: str)         – called with status messages
    """
    def _log(msg):
        if log_cb:
            log_cb(msg)

    # Count total lines for progress
    total_lines = 0
    for fp in input_files:
        with open(fp, 'r', errors='replace') as f:
            for _ in f:
                total_lines += 1

    hdr = collect_header_info(input_files[0])
    bitrate  = hdr.get('Bit-rate', '500000')
    sess_time = hdr.get('Time', datetime.now().strftime('%Y%m%dT%H%M%S'))

    base_ts    = None
    msg_count  = 0
    lines_done = 0

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    with open(output_file, 'w') as out:
        # ASC file header
        out.write(f"date {sess_time}\n")
        out.write("base hex  timestamps absolute\n")
        out.write("no internal events logged\n")
        out.write(f"// Source: CL2000 logger  Bit-rate: {bitrate}\n")
        out.write("Begin Triggerblock\n")

        for filepath in input_files:
            _log(f"Processing: {os.path.basename(filepath)}")
            with open(filepath, 'r', errors='replace') as f:
                for line in f:
                    lines_done += 1
                    if progress_cb and lines_done % 5000 == 0:
                        progress_cb(lines_done / total_lines * 100)

                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('Timestamp'):
                        continue

                    parts = line.split(';')
                    if len(parts) < 4:
                        continue

                    ts_raw, _, can_id_str, data_str = parts[0], parts[1], parts[2], parts[3]

                    ts = parse_ts(ts_raw)
                    if ts is None:
                        continue
                    if base_ts is None:
                        base_ts = ts
                    rel_ts = ts - base_ts

                    try:
                        can_id = int(can_id_str, 16)
                    except ValueError:
                        continue

                    data_hex = data_str.strip()
                    if len(data_hex) % 2 != 0:
                        data_hex = '0' + data_hex
                    dlc = len(data_hex) // 2
                    data_bytes = ' '.join(data_hex[i:i+2] for i in range(0, len(data_hex), 2))

                    id_suffix = 'x' if can_id > 0x7FF else ''
                    id_str    = f"{can_id:X}{id_suffix}"

                    out.write(f"   {rel_ts:.4f} 1  {id_str:<12} Rx   d {dlc} {data_bytes}\n")
                    msg_count += 1

        out.write("End TriggerBlock\n")

    if progress_cb:
        progress_cb(100)
    _log(f"Done — {msg_count:,} messages written to {os.path.basename(output_file)}")
    return msg_count


# ─────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────

BG        = "#0d0f14"
PANEL     = "#14171f"
BORDER    = "#1e2330"
ACCENT    = "#00c8ff"
ACCENT2   = "#005f78"
TEXT      = "#d4dbe8"
TEXT_DIM  = "#5a6070"
SUCCESS   = "#00e5a0"
ERROR_CLR = "#ff4c6a"
MONO      = ("Courier New", 9)
FONT_UI   = ("Segoe UI", 10) if os.name == "nt" else ("SF Pro Display", 10)
FONT_TITLE = ("Segoe UI Semibold", 13) if os.name == "nt" else ("SF Pro Display", 13)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CL2000 → Vector ASC")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(680, 540)

        self._files = []          # list of selected input paths
        self._output_path = tk.StringVar()
        self._running = False

        self._build_ui()
        self._center()

    # ── layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── title bar ──
        top = tk.Frame(self, bg=BG, pady=18)
        top.pack(fill="x", padx=24)

        tk.Label(top, text="CL2000", font=("Courier New", 22, "bold"),
                 fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(top, text=" → Vector ASC Converter", font=FONT_TITLE,
                 fg=TEXT, bg=BG).pack(side="left", pady=4)

        # ── input files section ──
        self._section(self, "INPUT FILES")

        input_frame = tk.Frame(self, bg=PANEL, bd=0, relief="flat",
                               highlightbackground=BORDER, highlightthickness=1)
        input_frame.pack(fill="both", expand=True, padx=24, pady=(0, 4))

        # listbox + scrollbar
        list_frame = tk.Frame(input_frame, bg=PANEL)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self._listbox = tk.Listbox(
            list_frame, bg=PANEL, fg=TEXT, selectbackground=ACCENT2,
            selectforeground=ACCENT, font=MONO, bd=0, highlightthickness=0,
            activestyle="none", relief="flat"
        )
        sb = tk.Scrollbar(list_frame, orient="vertical",
                          command=self._listbox.yview,
                          troughcolor=PANEL, bg=BORDER)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)

        # file buttons
        btn_row = tk.Frame(input_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        self._btn(btn_row, "＋  Add Files",    self._add_files,   ACCENT).pack(side="left", padx=(0, 6))
        self._btn(btn_row, "✕  Remove Selected", self._remove_selected, "#444").pack(side="left", padx=(0, 6))
        self._btn(btn_row, "↑  Move Up",       self._move_up,     "#444").pack(side="left", padx=(0, 6))
        self._btn(btn_row, "↓  Move Down",     self._move_down,   "#444").pack(side="left")

        # ── output file ──
        self._section(self, "OUTPUT FILE")

        out_frame = tk.Frame(self, bg=PANEL, highlightbackground=BORDER,
                             highlightthickness=1)
        out_frame.pack(fill="x", padx=24, pady=(0, 4))

        inner = tk.Frame(out_frame, bg=PANEL)
        inner.pack(fill="x", padx=8, pady=8)

        self._out_entry = tk.Entry(
            inner, textvariable=self._output_path,
            bg="#0a0c11", fg=TEXT, insertbackground=ACCENT,
            font=MONO, bd=0, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT, relief="flat"
        )
        self._out_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        self._btn(inner, "Browse…", self._browse_output, ACCENT2).pack(side="left")

        # ── progress ──
        prog_frame = tk.Frame(self, bg=BG)
        prog_frame.pack(fill="x", padx=24, pady=(8, 0))

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("CAN.Horizontal.TProgressbar",
                        troughcolor=PANEL, background=ACCENT,
                        bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT)

        self._progress = ttk.Progressbar(prog_frame, style="CAN.Horizontal.TProgressbar",
                                         orient="horizontal", mode="determinate")
        self._progress.pack(fill="x")

        # ── log console ──
        self._section(self, "LOG")

        log_frame = tk.Frame(self, bg=PANEL, highlightbackground=BORDER,
                             highlightthickness=1)
        log_frame.pack(fill="x", padx=24, pady=(0, 4))

        self._log_text = tk.Text(
            log_frame, height=5, bg="#080a0e", fg=TEXT_DIM,
            font=MONO, bd=0, highlightthickness=0, state="disabled",
            relief="flat", wrap="word"
        )
        self._log_text.pack(fill="x", padx=8, pady=8)
        self._log_text.tag_config("ok",  foreground=SUCCESS)
        self._log_text.tag_config("err", foreground=ERROR_CLR)
        self._log_text.tag_config("inf", foreground=ACCENT)

        # ── convert button ──
        btn_bottom = tk.Frame(self, bg=BG)
        btn_bottom.pack(fill="x", padx=24, pady=12)

        self._convert_btn = self._btn(
            btn_bottom, "  CONVERT  ", self._start_conversion,
            ACCENT, fg="#000", font=("Courier New", 11, "bold"), padx=24, pady=10
        )
        self._convert_btn.pack(side="right")

    def _section(self, parent, text):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=24, pady=(10, 4))
        tk.Label(f, text=text, font=("Courier New", 8, "bold"),
                 fg=ACCENT, bg=BG).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                               expand=True, padx=(8, 0), pady=6)

    def _btn(self, parent, text, cmd, bg, fg=TEXT,
             font=FONT_UI, padx=12, pady=5):
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg=fg, activebackground=ACCENT, activeforeground="#000",
            font=font, bd=0, padx=padx, pady=pady,
            cursor="hand2", relief="flat"
        )
        b.bind("<Enter>", lambda e: b.config(bg=ACCENT if bg == ACCENT else "#2a2e3a"))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    # ── file management ──────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select CL2000 TXT log files",
            filetypes=[("Text log files", "*.TXT *.txt"), ("All files", "*.*")]
        )
        for p in paths:
            if p not in self._files:
                self._files.append(p)
                self._listbox.insert("end", os.path.basename(p))
        # Auto-suggest output path next to first file
        if self._files and not self._output_path.get():
            d = os.path.dirname(self._files[0])
            self._output_path.set(os.path.join(d, "converted.asc"))

    def _remove_selected(self):
        sel = list(self._listbox.curselection())
        for i in reversed(sel):
            self._listbox.delete(i)
            self._files.pop(i)

    def _move_up(self):
        sel = self._listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self._files[i-1], self._files[i] = self._files[i], self._files[i-1]
        self._refresh_list(i - 1)

    def _move_down(self):
        sel = self._listbox.curselection()
        if not sel or sel[0] >= len(self._files) - 1:
            return
        i = sel[0]
        self._files[i], self._files[i+1] = self._files[i+1], self._files[i]
        self._refresh_list(i + 1)

    def _refresh_list(self, select=None):
        self._listbox.delete(0, "end")
        for f in self._files:
            self._listbox.insert("end", os.path.basename(f))
        if select is not None:
            self._listbox.selection_set(select)

    def _browse_output(self):
        p = filedialog.asksaveasfilename(
            title="Save ASC file as…",
            defaultextension=".asc",
            filetypes=[("ASC log files", "*.asc"), ("All files", "*.*")]
        )
        if p:
            self._output_path.set(p)

    # ── conversion ───────────────────────────────────────────────────────────

    def _log(self, msg, tag="inf"):
        def _do():
            self._log_text.config(state="normal")
            self._log_text.insert("end", msg + "\n", tag)
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        self.after(0, _do)

    def _set_progress(self, pct):
        self.after(0, lambda: self._progress.config(value=pct))

    def _start_conversion(self):
        if self._running:
            return
        if not self._files:
            messagebox.showwarning("No input files", "Please add at least one CL2000 TXT file.")
            return
        out = self._output_path.get().strip()
        if not out:
            messagebox.showwarning("No output file", "Please specify an output .asc file path.")
            return

        self._running = True
        self._convert_btn.config(state="disabled", text="  CONVERTING…  ")
        self._progress.config(value=0)

        def worker():
            try:
                convert(
                    self._files, out,
                    progress_cb=self._set_progress,
                    log_cb=lambda m: self._log(m, "inf")
                )
                self._log(f"✔  Saved: {out}", "ok")
            except Exception as e:
                self._log(f"✘  Error: {e}", "err")
            finally:
                self._running = False
                self.after(0, lambda: self._convert_btn.config(
                    state="normal", text="  CONVERT  "))

        threading.Thread(target=worker, daemon=True).start()

    # ── utils ────────────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        w, h = 720, 600
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
