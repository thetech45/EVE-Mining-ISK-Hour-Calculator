# ================== EVE Mining Dashboard ==================

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import time
import random
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import json
import os
import matplotlib.pyplot as plt
import sys
import subprocess

# ================= FIREWALL AUTO-RULE =================
def add_firewall_rule():
    try:
        exe_path = sys.executable
        subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name=EVE Mining Dashboard",
            f"dir=in", f"action=allow",
            f"program={exe_path}", f"enable=yes"
        ], check=True, shell=True)
    except Exception as e:
        print(f"Firewall rule failed: {e}")

add_firewall_rule()

# ================= CONFIG =================
# Embedded config (no config.json required)
CLIENT_ID = "39293ddfb7a3496cb6055b71c6c2edd2"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
PORT = 8765
SCOPES = "esi-skills.read_skills.v1"

SSO_AUTH = "https://login.eveonline.com/v2/oauth/authorize"

# ================= DATABASE =================
db = sqlite3.connect("mining_history.db", check_same_thread=False)
c = db.cursor()
c.execute("CREATE TABLE IF NOT EXISTS history (ts INTEGER, isk REAL)")
db.commit()

# ================= BOOST DATA =================
BOOSTERS = {
    "None": {"yield": 1.0, "cycle": 1.0},
    "Porpoise": {"yield": 1.15, "cycle": 0.90},
    "Orca": {"yield": 1.30, "cycle": 0.85},
    "Rorqual": {"yield": 1.60, "cycle": 0.75},
}
INDUSTRIAL_CORE_MULT = 1.25
FOREMAN_BURST_MULT = 1.15
COMPRESSION_MULT = 1.05

# ================= TK ROOT =================
root = tk.Tk()
root.title("EVE Mining Command Center")
root.geometry("560x480")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# ================= PERSONAL MINING TAB =================
mining_tab = ttk.Frame(notebook)
notebook.add(mining_tab, text="Personal Mining")
notebook.tab(mining_tab, state="disabled")

booster_var = tk.StringVar(value="None")
industrial_core_var = tk.BooleanVar(value=False)
foreman_burst_var = tk.BooleanVar(value=True)
compression_var = tk.BooleanVar(value=False)
result_var = tk.StringVar(value="ISK/hr: 0")

ttk.Label(mining_tab, text="Booster Ship").pack(pady=5)
ttk.OptionMenu(mining_tab, booster_var, booster_var.get(), *BOOSTERS.keys()).pack()
ttk.Checkbutton(mining_tab, text="Industrial Core (Rorqual only)", variable=industrial_core_var).pack(pady=2)
ttk.Checkbutton(mining_tab, text="Foreman Burst", variable=foreman_burst_var).pack(pady=2)
ttk.Checkbutton(mining_tab, text="Compression", variable=compression_var).pack(pady=2)

# ================= LOGIN TAB =================
login_tab = ttk.Frame(notebook)
notebook.add(login_tab, text="Login")
login_status = tk.StringVar(value="Not logged in")

# ================= AUTH SERVER =================
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Login successful. You may close this window.")
            root.after_idle(lambda: enable_mining_tab())

def start_server():
    httpd = HTTPServer(("127.0.0.1", PORT), CallbackHandler)
    httpd.timeout = 120  # keep server alive for EXE builds
    while True:
        httpd.handle_request()

def start_login():
    state = "mining_dashboard"
    auth_url = (
        f"{SSO_AUTH}?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
        f"&state={state}"
    )
    threading.Thread(target=start_server, daemon=True).start()
    webbrowser.open(auth_url)

def enable_mining_tab():
    login_status.set("Logged in")
    notebook.tab(mining_tab, state="normal")
    notebook.select(mining_tab)

ttk.Button(login_tab, text="Login with EVE Online", command=start_login).pack(pady=20)
ttk.Label(login_tab, textvariable=login_status).pack()

# ================= CALCULATE =================
def calculate():
    base_isk = random.randint(18_000_000, 22_000_000)
    boost = BOOSTERS[booster_var.get()]
    yield_mult = boost["yield"]
    cycle_mult = boost["cycle"]

    if booster_var.get() == "Rorqual" and industrial_core_var.get():
        yield_mult *= INDUSTRIAL_CORE_MULT
    if foreman_burst_var.get():
        yield_mult *= FOREMAN_BURST_MULT
    if compression_var.get():
        yield_mult *= COMPRESSION_MULT

    final_isk = base_isk * yield_mult / cycle_mult
    result_var.set(f"ISK/hr: {int(final_isk):,}")

    c.execute("INSERT INTO history VALUES (?, ?)", (int(time.time()), final_isk))
    db.commit()

# ================= GRAPH =================
def show_graph():
    rows = c.execute("SELECT ts, isk FROM history ORDER BY ts").fetchall()
    if not rows:
        messagebox.showinfo("No Data", "No mining data recorded yet.")
        return
    times = [r[0] for r in rows]
    isk_vals = [r[1] for r in rows]
    plt.figure()
    plt.plot(times, isk_vals)
    plt.title("Mining ISK/hr History")
    plt.xlabel("Time")
    plt.ylabel("ISK/hr")
    plt.show()

# ================= BUTTONS =================
ttk.Button(mining_tab, text="Calculate", command=calculate).pack(pady=10)
ttk.Label(mining_tab, textvariable=result_var, font=("Segoe UI", 12, "bold")).pack(pady=5)
ttk.Button(mining_tab, text="Show Graph", command=show_graph).pack(pady=5)

# ================= START =================
root.mainloop()
