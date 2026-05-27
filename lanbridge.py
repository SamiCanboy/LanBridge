#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════╗
║  LanBridge v3.1  —  LAN P2P Köprüsü      ║
║  macOS ↔ Windows  |  Bulutsuz, Ücretsiz  ║
║  Metin + Dosya + Görsel  (pano → pano)   ║
╚═══════════════════════════════════════════╝
"""
from __future__ import annotations
import os, sys, json, socket, struct, threading, time, platform, math
import tempfile, hashlib, subprocess
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, Optional, List

# Tek instance kontrolü
_INSTANCE_LOCK_PORT = 55102
_instance_socket = None

def _ensure_single_instance():
    """Aynı anda sadece bir LanBridge çalışsın. Varsa mevcut olanı öne getir."""
    global _instance_socket
    try:
        _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _instance_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        _instance_socket.bind(("127.0.0.1", _INSTANCE_LOCK_PORT))
        _instance_socket.listen(1)
        return True
    except OSError:
        # Mevcut instance'a "öne gel" sinyali gönder
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", _INSTANCE_LOCK_PORT))
            s.sendall(b"SHOW")
            s.close()
        except: pass
        return False
# ══════════════════════════════════════════════════════════════════════════════
#  DETACH — terminalden ayrıl
# ══════════════════════════════════════════════════════════════════════════════
def _detach_from_terminal():
    if os.environ.get("LANBRIDGE_DETACHED") == "1": return
    env = os.environ.copy(); env["LANBRIDGE_DETACHED"] = "1"
    try:
        if platform.system() == "Windows":
            py = sys.executable
            if py.lower().endswith("python.exe"):
                pyw = py[:-10] + "pythonw.exe"
                if os.path.exists(pyw): py = pyw
            subprocess.Popen([py, os.path.abspath(__file__)], env=env,
                             creationflags=0x00000008 | 0x00000200,
                             close_fds=True, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen([sys.executable, os.path.abspath(__file__)], env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True,
                             close_fds=True)
        sys.exit(0)
    except Exception as e:
        print(f"[detach] {e}", file=sys.stderr)

if __name__ == "__main__":
    # Tek instance kontrolü — detach'ten önce
    if os.environ.get("LANBRIDGE_DETACHED") == "1":
        if not _ensure_single_instance():
            sys.exit(0)  # Zaten çalışıyor, sessizce çık
    
    if "--debug" not in sys.argv and "--no-detach" not in sys.argv:
        _detach_from_terminal()

# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    print("HATA: Tkinter bulunamadı."); sys.exit(1)

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

try:
    import pyperclip
    CLIP_TEXT_AVAILABLE = True
except Exception:
    CLIP_TEXT_AVAILABLE = False

try:
    from PIL import ImageGrab, Image, ImageDraw
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import pystray
    PYSTRAY_AVAILABLE = True
except Exception:
    PYSTRAY_AVAILABLE = False

CLIP_FILES_AVAILABLE = False
if platform.system() == "Darwin":
    try:
        from AppKit import NSPasteboard, NSImage
        CLIP_FILES_AVAILABLE = True
    except Exception: pass
elif platform.system() == "Windows":
    try:
        import win32clipboard
        CLIP_FILES_AVAILABLE = True
    except Exception: pass

# ══════════════════════════════════════════════════════════════════════════════
#  SABİTLER
# ══════════════════════════════════════════════════════════════════════════════
APP_NAME      = "LanBridge"
VERSION       = "3.1"
DISC_PORT     = 55100
TCP_PORT      = 55101
DISC_INTERVAL = 3
CLIP_INTERVAL = 0.7
PEER_TTL      = 10
CHUNK_SIZE    = 65536
FILE_TIMEOUT  = 3600
TYPE_FILE     = 0x01
TYPE_CLIP     = 0x02
SIZE_WARN_MB  = 50
SIZE_WARN_B   = SIZE_WARN_MB * 1024 * 1024
IMAGE_EXTS    = {".png",".jpg",".jpeg",".gif",".bmp",".webp",".tiff"}

DOWNLOADS = Path.home() / "LanBridge_Alinanlar"
DOWNLOADS.mkdir(parents=True, exist_ok=True)
TMPDIR    = Path(tempfile.gettempdir()) / "LanBridge_Tmp"
TMPDIR.mkdir(parents=True, exist_ok=True)

C = {
    "bg":"#0b0c10","panel":"#13141a","card":"#1a1d27","card2":"#171922",
    "border":"#252836","accent":"#00d2ff","accent2":"#3a7bd5",
    "success":"#00e676","warn":"#ffab40","danger":"#ff5252","purple":"#b388ff",
    "text":"#e8eaf6","text2":"#b0bec5","muted":"#546e7a","dim":"#37474f",
    "header_bg":"#0d1117",
}
MONO = ("Courier New" if platform.system()=="Windows" else "Menlo", 9)
UI   = ("Segoe UI"    if platform.system()=="Windows" else "SF Pro Display", 10)

# ══════════════════════════════════════════════════════════════════════════════
#  YARDIMCILAR
# ══════════════════════════════════════════════════════════════════════════════
def get_local_ip():
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80))
        ip=s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def human_size(n):
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

def human_speed(bps):
    if bps < 1: return "—"
    for u in ("B/s","KB/s","MB/s","GB/s"):
        if bps < 1024: return f"{bps:.1f} {u}"
        bps /= 1024
    return f"{bps:.1f} TB/s"

def open_folder(path):
    if   platform.system()=="Darwin":  os.system(f'open "{path}"')
    elif platform.system()=="Windows": os.startfile(path)
    else:                              os.system(f'xdg-open "{path}"')
SETTINGS_FILE = Path.home() / ".lanbridge_settings.json"

def load_setting(key, default=False):
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text()).get(key, default)
    except: pass
    return default

def save_setting(key, value):
    try:
        data = {}
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text())
        data[key] = value
        SETTINGS_FILE.write_text(json.dumps(data))
    except: pass
LOCAL_IP = get_local_ip()
HOSTNAME = socket.gethostname()
OS_NAME  = f"{platform.system()} {platform.release()}"

# ══════════════════════════════════════════════════════════════════════════════
#  SİSTEM TEPSİSİ / MENÜ ÇUBUĞU İKONU
# ══════════════════════════════════════════════════════════════════════════════
def make_tray_icon_image():
    """64x64 transparan arkaplanlı altıgen ikon — pystray için."""
    if not PIL_AVAILABLE: return None
    size = 128
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    d = ImageDraw.Draw(img)
    cx, cy = size//2, size//2
    r_out = int(size*0.42)
    r_in  = int(size*0.22)
    pts_out, pts_in = [], []
    for i in range(6):
        a = (math.pi/3)*i - math.pi/2
        pts_out.append((cx + r_out*math.cos(a), cy + r_out*math.sin(a)))
        pts_in.append ((cx + r_in *math.cos(a), cy + r_in *math.sin(a)))
    # Yarı şeffaf dolgu
    d.polygon(pts_out, fill=(0,210,255,90))
    # Kalın kenarlık
    w = max(5, size//18)
    for i in range(6):
        d.line([pts_out[i], pts_out[(i+1)%6]], fill=(0,210,255,255), width=w)
    # İç altıgen — dolu
    d.polygon(pts_in, fill=(0,210,255,235))
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  PROTOKOL
# ══════════════════════════════════════════════════════════════════════════════
def proto_send_header(sock, t, h):
    b = json.dumps(h, ensure_ascii=False).encode("utf-8")
    sock.sendall(struct.pack(">BQ", t, len(b)) + b)

def proto_recv_header(sock):
    raw = _recv_exact(sock, 9); t,l = struct.unpack(">BQ", raw)
    return t, json.loads(_recv_exact(sock, l).decode("utf-8"))

def _recv_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c: raise ConnectionError("Bağlantı kesildi")
        buf.extend(c)
    return bytes(buf)

# ══════════════════════════════════════════════════════════════════════════════
#  PANODAN DOSYA/GÖRSEL OKUMA
# ══════════════════════════════════════════════════════════════════════════════
def get_clipboard_files():
    if not CLIP_FILES_AVAILABLE: return []
    try:
        if platform.system() == "Darwin":
            pb = NSPasteboard.generalPasteboard()
            items = pb.propertyListForType_("NSFilenamesPboardType")
            if items: return [str(p) for p in items if os.path.exists(str(p))]
        elif platform.system() == "Windows":
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                    files = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                    return [f for f in files if os.path.exists(f)]
            finally: win32clipboard.CloseClipboard()
    except: pass
    return []

def get_clipboard_image():
    if not PIL_AVAILABLE: return None
    try:
        img = ImageGrab.grabclipboard()
        if img is None or isinstance(img, list): return None
        if isinstance(img, Image.Image): return img
    except: pass
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  PANOYA GÖRSEL YAZMA  (alınan görseli panoya koy)
# ══════════════════════════════════════════════════════════════════════════════
def copy_image_to_clipboard(path: str) -> bool:
    """Alınan görseli işletim sistemi panosuna yaz. Başarılıysa True."""
    if not PIL_AVAILABLE: return False
    try:
        if platform.system() == "Darwin":
            # macOS — NSPasteboard
            if not CLIP_FILES_AVAILABLE: return False
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            img = NSImage.alloc().initWithContentsOfFile_(path)
            if img is None: return False
            return bool(pb.writeObjects_([img]))

        elif platform.system() == "Windows":
            # Windows — CF_DIB
            if not CLIP_FILES_AVAILABLE: return False
            img = Image.open(path)
            output = BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]   # BMP header çıkar
            output.close()
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            finally:
                win32clipboard.CloseClipboard()
            return True
    except Exception as e:
        print(f"[copy-img] {e}")
    return False

# ══════════════════════════════════════════════════════════════════════════════
#  İSTATİSTİK
# ══════════════════════════════════════════════════════════════════════════════
class Stats:
    def __init__(self):
        self.start         = time.time()
        self.bytes_sent    = 0
        self.bytes_recv    = 0
        self.tx_count      = 0
        self.rx_count      = 0
        self.last_speed    = 0.0      # bytes/sec

    def uptime_str(self):
        d = int(time.time() - self.start)
        h, rem = divmod(d, 3600); m, s = divmod(rem, 60)
        if h: return f"{h}sa {m:02d}dk"
        if m: return f"{m}dk {s:02d}sn"
        return f"{s} sn"

# ══════════════════════════════════════════════════════════════════════════════
#  SERVİSLER  (önceki versiyondan değişmedi)
# ══════════════════════════════════════════════════════════════════════════════
class DiscoveryService:
    def __init__(self, on_found, on_lost):
        self.on_found, self.on_lost = on_found, on_lost
        self.running = False; self._peers={}; self._lock=threading.Lock()
    def start(self):
        self.running = True
        for t,n in [(self._bcast,"d-tx"),(self._listen,"d-rx"),(self._gc,"d-gc")]:
            threading.Thread(target=t, daemon=True, name=n).start()
    def stop(self): self.running = False
    def peers(self): return dict(self._peers)
    def _bcast(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        pl = json.dumps({"app":"LanBridge","version":VERSION,"hostname":HOSTNAME,
                         "ip":LOCAL_IP,"tcp_port":TCP_PORT,"os":OS_NAME}).encode()
        while self.running:
            try: s.sendto(pl, ("<broadcast>", DISC_PORT))
            except: pass
            time.sleep(DISC_INTERVAL)
        s.close()
    def _listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError: pass
        s.bind(("", DISC_PORT)); s.settimeout(1.0)
        while self.running:
            try:
                d, addr = s.recvfrom(2048)
                info = json.loads(d.decode())
                if info.get("app") != "LanBridge": continue
                pip = info.get("ip", addr[0])
                if pip == LOCAL_IP: continue
                with self._lock:
                    is_new = pip not in self._peers
                    self._peers[pip] = {"hostname":info.get("hostname",pip),
                                        "tcp_port":info.get("tcp_port",TCP_PORT),
                                        "os":info.get("os","?"),
                                        "last_seen":time.time(),
                                        "since":self._peers.get(pip,{}).get("since",time.time())}
                if is_new: self.on_found(pip, self._peers[pip])
            except socket.timeout: continue
            except: pass
        s.close()
    def _gc(self):
        while self.running:
            now = time.time(); dead = []
            with self._lock:
                for ip,p in list(self._peers.items()):
                    if now - p["last_seen"] > PEER_TTL: dead.append(ip)
                for ip in dead: del self._peers[ip]
            for ip in dead: self.on_lost(ip)
            time.sleep(DISC_INTERVAL)


class ClipboardMonitor:
    def __init__(self, on_text, on_pending):
        self.on_text = on_text; self.on_pending = on_pending
        self.running = False
        self._last_text = ""; self._last_files = ""; self._last_imgh = ""
        self._syncing = False
        self.enabled_text = True; self.enabled_files = True; self.enabled_images = True
        self._block_image_hash = ""   # gelen görsel için döngü engelleme

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True, name="clipboard").start()
    def stop(self): self.running = False

    def set_from_remote_text(self, text):
        if not CLIP_TEXT_AVAILABLE: return
        self._syncing = True
        try: pyperclip.copy(text); self._last_text = text
        except: pass
        finally: self._syncing = False

    def mark_remote_image(self, image_path):
        """Yeni gelen görselin hash'ini bilinen olarak işaretle ki tekrar gönderilmesin."""
        if not PIL_AVAILABLE: return
        try:
            img = Image.open(image_path)
            h = hashlib.md5(img.tobytes()[:8192]).hexdigest()
            self._last_imgh = h
        except: pass

    def _loop(self):
        while self.running:
            if CLIP_TEXT_AVAILABLE and self.enabled_text:
                try:
                    cur = pyperclip.paste()
                    if cur and cur != self._last_text and not self._syncing:
                        self._last_text = cur; self.on_text(cur)
                except: pass
            if self.enabled_files:
                try:
                    files = get_clipboard_files()
                    if files:
                        key = "|".join(files)
                        if key != self._last_files:
                            self._last_files = key
                            total = sum(os.path.getsize(f) for f in files
                                        if os.path.exists(f) and os.path.isfile(f))
                            self.on_pending("files", files, total)
                    elif self._last_files: self._last_files = ""
                except: pass
            if self.enabled_images and PIL_AVAILABLE:
                try:
                    img = get_clipboard_image()
                    if img is not None:
                        h = hashlib.md5(img.tobytes()[:8192]).hexdigest()
                        if h != self._last_imgh:
                            self._last_imgh = h
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            fpath = TMPDIR / f"clipboard_image_{ts}.png"
                            img.save(fpath, "PNG")
                            sz = fpath.stat().st_size
                            self.on_pending("image", [str(fpath)], sz)
                except: pass
            time.sleep(CLIP_INTERVAL)


class TCPServer:
    def __init__(self, on_file, on_clip):
        self.on_file, self.on_clip = on_file, on_clip
        self.running = False
    def start(self):
        self.running = True
        threading.Thread(target=self._listen, daemon=True, name="tcp-srv").start()
    def stop(self): self.running = False
    def _listen(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", TCP_PORT)); srv.listen(10); srv.settimeout(1.0)
        while self.running:
            try:
                conn, addr = srv.accept()
                threading.Thread(target=self._handle, args=(conn,addr), daemon=True).start()
            except socket.timeout: continue
            except: break
        srv.close()
    def _handle(self, conn, addr):
        try:
            conn.settimeout(FILE_TIMEOUT)
            t, hdr = proto_recv_header(conn)
            if t == TYPE_FILE:
                fn = Path(hdr["filename"]).name; sz = hdr["filesize"]
                dest = DOWNLOADS / fn
                if dest.exists():
                    i=1
                    while dest.exists():
                        dest = DOWNLOADS / f"{Path(fn).stem}_{i}{Path(fn).suffix}"; i+=1
                rx=0; t0=time.time()
                with open(dest,"wb") as f:
                    while rx < sz:
                        c = _recv_exact(conn, min(CHUNK_SIZE, sz-rx))
                        f.write(c); rx += len(c)
                dur = max(time.time()-t0, 0.001)
                self.on_file(addr[0], fn, sz, str(dest), sz/dur)
            elif t == TYPE_CLIP:
                self.on_clip(addr[0], hdr.get("text",""))
        except Exception as e: print(f"[TCP] {addr}: {e}")
        finally: conn.close()


class FileSender:
    @staticmethod
    def send(ip, port, path, progress_cb=None):
        p = Path(path); sz = p.stat().st_size
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(15); s.connect((ip,port)); s.settimeout(FILE_TIMEOUT)
        proto_send_header(s, TYPE_FILE, {"filename":p.name,"filesize":sz})
        sent=0; t0=time.time()
        with open(p,"rb") as f:
            while True:
                ch = f.read(CHUNK_SIZE)
                if not ch: break
                s.sendall(ch); sent += len(ch)
                if progress_cb: progress_cb(sent, sz)
        s.close()
        dur = max(time.time()-t0, 0.001)
        return sz/dur

class ClipSender:
    @staticmethod
    def send(ip, port, text):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5); s.connect((ip,port))
            proto_send_header(s, TYPE_CLIP, {"text":text}); s.close()
        except Exception as e: print(f"[Clip] {ip}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  SPLASH
# ══════════════════════════════════════════════════════════════════════════════
class SplashScreen:
    DURATION = 2400
    def __init__(self, root):
        self.root = root
        self.win = tk.Toplevel(root); self.win.overrideredirect(True)
        self.win.configure(bg=C["bg"]); self.win.attributes("-topmost", True)
        W,H = 500,320
        sw,sh = root.winfo_screenwidth(), root.winfo_screenheight()
        self.win.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        c = tk.Canvas(self.win, width=W, height=H, bg=C["bg"], highlightthickness=0)
        c.pack(fill="both", expand=True); self.c = c; self._W,self._H = W,H
        for x in range(0,W+1,40): c.create_line(x,0,x,H, fill="#0f1118")
        for y in range(0,H+1,40): c.create_line(0,y,W,y, fill="#0f1118")
        for x,y in [(0,0),(W,0),(0,H),(W,H)]:
            dx,dy = (1 if x==0 else -1),(1 if y==0 else -1)
            c.create_line(x,y, x+dx*30,y, fill=C["accent"], width=2)
            c.create_line(x,y, x,y+dy*30, fill=C["accent"], width=2)
        # Hex + logo
        c.create_text(W//2-160, 120, text="⬡", font=(UI[0],52,"bold"), fill=C["accent"])
        c.create_text(W//2+15,  120, text="LANBRIDGE",
                      font=("Courier New" if platform.system()=="Windows" else "Menlo",36,"bold"),
                      fill=C["text"])
        c.create_line(W//2-140,165, W//2+140,165, fill=C["border"], width=1)
        c.create_text(W//2,185, text=f"v{VERSION}  •  LAN P2P Köprüsü", font=MONO, fill=C["muted"])
        c.create_text(W//2,205, text=f"{HOSTNAME}  ({LOCAL_IP})", font=MONO, fill=C["dim"])
        bx1,by1,bx2,by2 = W//2-140,H-55,W//2+140,H-40
        c.create_rectangle(bx1,by1,bx2,by2, fill=C["card"], outline=C["border"])
        self._bx1,self._by1,self._bx2,self._by2 = bx1+2,by1+2,bx2-2,by2-2
        self._bar = c.create_rectangle(self._bx1,self._by1,self._bx1,self._by2,
                                       fill=C["accent"], outline="")
        self._msg = c.create_text(W//2, H-24, text="Başlatılıyor...", font=MONO, fill=C["muted"])
        self._x = 0; self._anim()
    def _anim(self):
        if not self.win.winfo_exists(): return
        self._x = min(self._x+5, self._bx2-self._bx1)
        self.c.coords(self._bar, self._bx1,self._by1, self._bx1+self._x,self._by2)
        pct = self._x / (self._bx2-self._bx1)
        msgs = ["Başlatılıyor...","Ağ dinleniyor...","Hazırlanıyor..."]
        self.c.itemconfigure(self._msg, text=msgs[min(int(pct/0.34),2)])
        if self._x < self._bx2-self._bx1: self.win.after(16, self._anim)
    def destroy(self):
        if self.win.winfo_exists(): self.win.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  ANA UYGULAMA
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
#  macOS Tray Handler (global — sınıf bir kez register edilsin)
# ══════════════════════════════════════════════════════════════════════════════
_MACOS_TRAY_APP_REF = [None]  # mutable container — app instance burada tutulur

if platform.system() == "Darwin":
    try:
        from Foundation import NSObject
        import objc
    except Exception:
        pass
else:
    _MacOSTrayHandler = None
class LanBridgeApp:
    def __init__(self):
        LanBridgeApp._current_instance = None
        self._peers={}; self._sel_peer=None; self._pulse_phase=0.0
        self._pending = None
        self.stats = Stats()
        self._tray_icon = None
        self._tray_notified = False
        self._really_quit = False

        self._dnd = False
        if DND_AVAILABLE:
            try: self.root = TkinterDnD.Tk(); self._dnd = True
            except Exception: self.root = tk.Tk()
        else: self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        self.root.withdraw()
        self.root.title(f"{APP_NAME}  —  {HOSTNAME}")
        self.root.configure(bg=C["bg"])
        self.root.geometry("980x720")
        self.root.minsize(880, 640)

        self._splash = SplashScreen(self.root)

        self.discovery    = DiscoveryService(self._on_peer_found, self._on_peer_lost)
        self.clip_monitor = ClipboardMonitor(self._on_clip_text, self._on_clip_pending)
        self.tcp_server   = TCPServer(self._on_file_rx, self._on_clip_rx)

        self._build_gui()
        self.root.after(SplashScreen.DURATION, self._show_main)

    def _show_main(self):
        self._splash.destroy()
        self.root.deiconify(); self.root.lift()
        self.discovery.start(); self.clip_monitor.start(); self.tcp_server.start()
        self._log("info", f"{APP_NAME} v{VERSION} başlatıldı  —  {OS_NAME}")
        feats = []
        if CLIP_TEXT_AVAILABLE:  feats.append("Metin")
        if CLIP_FILES_AVAILABLE: feats.append("Dosya")
        if PIL_AVAILABLE:        feats.append("Görsel")
        self._log("info", f"Pano desteği: {', '.join(feats) if feats else 'YOK'}")
        if not CLIP_FILES_AVAILABLE:
            mod = "pyobjc-framework-Cocoa" if platform.system()=="Darwin" else "pywin32"
            self._log("warn", f"Pano dosyaları için: pip3 install {mod}")
        if not PIL_AVAILABLE:
            self._log("warn", "Pano görselleri için: pip3 install Pillow")
        self._log("folder", f"Alınanlar: {DOWNLOADS}")
        self._log("search", "Ağda LanBridge cihazları aranıyor...")
        self._setup_tray()
        # Instance lock listener — başka instance açılırsa pencereyi göster
        threading.Thread(target=self._instance_listener, daemon=True, name="instance-lock").start()
        self._pulse_tick(); self._tick_periodic()

    def _hide_to_tray(self):
        """Pencereyi kapat ama app'i tepside tut."""
        # macOS'ta tray kapalıysa direkt çık
        if sys.platform == 'darwin' and not load_setting("macos_tray_enabled", False):
            self._do_quit()
            return
        self.root.withdraw()
        

    # ══════════════════════════════════════════════════════════════════════════
    #  GUI
    # ══════════════════════════════════════════════════════════════════════════
    def _build_gui(self):
        r = self.root

        # ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        # ┃ HEADER  —  büyük logo solda, PC bilgi kartı sağda                 ┃
        # ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        hdr = tk.Frame(r, bg=C["header_bg"], height=100)
        hdr.pack(fill="x"); hdr.pack_propagate(False)

        # Logo bloğu (sol)
        logo_box = tk.Frame(hdr, bg=C["header_bg"])
        logo_box.pack(side="left", padx=24, pady=16, fill="y")
        tk.Label(logo_box, text="⬡", font=(UI[0],30,"bold"),
                 bg=C["header_bg"], fg=C["accent"]).pack(side="left", padx=(0,12))
        text_block = tk.Frame(logo_box, bg=C["header_bg"])
        text_block.pack(side="left", fill="y", expand=True)
        tk.Label(text_block, text="LANBRIDGE",
                 font=("Courier New" if platform.system()=="Windows" else "Menlo",20,"bold"),
                 bg=C["header_bg"], fg=C["text"]).pack(anchor="w", pady=(4,2))
        tk.Label(text_block, text=f"v{VERSION}   •   LAN P2P Köprüsü",
                 font=(UI[0],9), bg=C["header_bg"], fg=C["muted"]).pack(anchor="w")

        # PC bilgi kartı (sağ) — geniş + ferah
        info_card = tk.Frame(hdr, bg=C["card"], padx=18, pady=10,
                             highlightthickness=1, highlightbackground=C["border"])
        info_card.pack(side="right", padx=24, pady=16, ipadx=4)

        # Satır 1: nokta + hostname (TAM görünür)
        top_row = tk.Frame(info_card, bg=C["card"])
        top_row.pack(anchor="e", fill="x")
        self._sc = tk.Canvas(top_row, width=12, height=12,
                             bg=C["card"], highlightthickness=0)
        self._sc.pack(side="left", padx=(0,8))
        tk.Label(top_row, text=HOSTNAME, font=(UI[0],11,"bold"),
                 bg=C["card"], fg=C["text"]).pack(side="left")

        # Satır 2: IP : port  (tek label, kesilmez)
        tk.Label(info_card,
                 text=f"{LOCAL_IP} : {TCP_PORT}",
                 font=MONO, bg=C["card"], fg=C["accent"]
                 ).pack(anchor="e", pady=(4,0))

        # Satır 3: OS
        tk.Label(info_card, text=OS_NAME, font=(UI[0],8),
                 bg=C["card"], fg=C["dim"]).pack(anchor="e", pady=(2,0))

        tk.Frame(r, bg=C["border"], height=1).pack(fill="x")

        # ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        # ┃ BODY                                                              ┃
        # ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        body = tk.Frame(r, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=12)
        body.columnconfigure(0, weight=0, minsize=270)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # ━━ Sol sidebar (cihazlar + pano kontrol) ━━━━━━━━━━━━━━━━━━━━━━━━━━━
        sidebar = tk.Frame(body, bg=C["bg"])
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0,12))

        dev_outer, self._dev_frame = self._card(sidebar, "🖥  AKTİF CİHAZLAR", subtitle="LAN ağında bulunanlar")
        dev_outer.pack(fill="both")
        self._peer_canvas = tk.Canvas(self._dev_frame, bg=C["card"],
                                      highlightthickness=0, height=210)
        self._peer_canvas.pack(fill="both", expand=False, padx=8, pady=(0,8))
        self._peer_canvas.bind("<Button-1>", self._on_canvas_click)
        self._lbl_no_peer = tk.Label(self._dev_frame, text="  ⏳  Cihaz bekleniyor...",
                                     bg=C["card"], fg=C["muted"],
                                     font=(UI[0],9,"italic"), pady=8)
        self._lbl_no_peer.pack(fill="x", padx=8, pady=(0,8))

        # Pano kontrol
        clip_outer, clip_card = self._card(sidebar, "📋  PANO EŞİTLEME")
        clip_outer.pack(fill="both", expand=True, pady=(10,0))
        self._clip_text_v   = tk.BooleanVar(value=CLIP_TEXT_AVAILABLE)
        self._clip_files_v  = tk.BooleanVar(value=CLIP_FILES_AVAILABLE)
        self._clip_image_v  = tk.BooleanVar(value=PIL_AVAILABLE)
        for txt,var,ok in [
            (" Metin (otomatik)",          self._clip_text_v,  CLIP_TEXT_AVAILABLE),
            (" Dosya (onayla)",            self._clip_files_v, CLIP_FILES_AVAILABLE),
            (" Görsel (onayla)",           self._clip_image_v, PIL_AVAILABLE),
        ]:
            tk.Checkbutton(clip_card, text=txt, variable=var,
                bg=C["card"], fg=C["text"], selectcolor=C["card"],
                activebackground=C["card"], activeforeground=C["accent"],
                font=(UI[0],9), cursor="hand2",
                state="normal" if ok else "disabled"
            ).pack(anchor="w", padx=10, pady=1)
        def _sync_flags(*_):
            self.clip_monitor.enabled_text   = self._clip_text_v.get()
            self.clip_monitor.enabled_files  = self._clip_files_v.get()
            self.clip_monitor.enabled_images = self._clip_image_v.get()
        for v in (self._clip_text_v, self._clip_files_v, self._clip_image_v):
            v.trace_add("write", _sync_flags)
        self._clip_preview = tk.Label(clip_card, text="Pano izleniyor...",
            bg=C["panel"], fg=C["muted"], font=(UI[0],9),
            wraplength=210, justify="left", anchor="nw",
            padx=8, pady=8, relief="flat")
        self._clip_preview.pack(fill="both", expand=False, padx=8, pady=(6,4))
        self._clip_badge = tk.Label(clip_card, text="", bg=C["card"],
                                    fg=C["success"], font=(UI[0],8,"italic"))
        if sys.platform == 'darwin':
            tk.Frame(clip_card, bg=C["border"], height=1).pack(fill="x", padx=8, pady=(6,4))
            self._macos_tray_v = tk.BooleanVar(value=load_setting("macos_tray_enabled", False))
            def _toggle_macos_tray():
                save_setting("macos_tray_enabled", self._macos_tray_v.get())
                messagebox.showinfo(
                    "Yeniden Başlatma Gerekli",
                    "Değişikliğin uygulanması için uygulamayı yeniden başlatın."
                )
            tk.Checkbutton(
                clip_card, text=" macOS menü çubuğunda göster",
                variable=self._macos_tray_v, command=_toggle_macos_tray,
                bg=C["card"], fg=C["text"], selectcolor=C["card"],
                activebackground=C["card"], activeforeground=C["accent"],
                font=(UI[0],9), cursor="hand2"
            ).pack(anchor="w", padx=10, pady=(2,6))
        self._clip_badge.pack(anchor="w", padx=10, pady=(0,6))

        # ━━ Ana panel ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        main = tk.Frame(body, bg=C["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(3, weight=1)
        main.columnconfigure(0, weight=1)

        # 1) ONLINE banner
        status_card = tk.Frame(main, bg=C["card"],
                               highlightthickness=1, highlightbackground=C["border"])
        status_card.grid(row=0, column=0, sticky="ew", pady=(0,10))

        s_inner = tk.Frame(status_card, bg=C["card"])
        s_inner.pack(fill="x", padx=14, pady=10)
        s_inner.columnconfigure(1, weight=1)

        # Sol: nabız + ONLINE etiketi
        live_box = tk.Frame(s_inner, bg=C["card"])
        live_box.grid(row=0, column=0, sticky="w")
        self._live_canvas = tk.Canvas(live_box, width=14, height=14,
                                      bg=C["card"], highlightthickness=0)
        self._live_canvas.pack(side="left", padx=(0,8))
        self._lbl_online = tk.Label(live_box, text="OFFLINE", font=(UI[0],13,"bold"),
                                    bg=C["card"], fg=C["danger"])
        self._lbl_online.pack(side="left")
        self._lbl_online_sub = tk.Label(live_box, text="  cihaz aranıyor",
                                        font=(UI[0],9), bg=C["card"], fg=C["muted"])
        self._lbl_online_sub.pack(side="left")

        # Sağ: stat tile'lar
        stat_box = tk.Frame(s_inner, bg=C["card"])
        stat_box.grid(row=0, column=1, sticky="e")
        self._stat_labels = {}
        for label, key in [("UPTIME","uptime"),("GÖNDERİLEN","sent"),
                           ("ALINAN","recv"),("HIZ","speed"),("TRANSFER","tx")]:
            tile = tk.Frame(stat_box, bg=C["panel"], padx=10, pady=6)
            tile.pack(side="left", padx=4)
            tk.Label(tile, text=label, font=(UI[0],7,"bold"),
                     bg=C["panel"], fg=C["muted"]).pack(anchor="w")
            val = tk.Label(tile, text="—", font=MONO,
                           bg=C["panel"], fg=C["text"])
            val.pack(anchor="w")
            self._stat_labels[key] = val

        # 2) Pending area
        self._pending_outer = tk.Frame(main, bg=C["bg"])
        self._pending_outer.grid(row=1, column=0, sticky="ew")

        # 3) Dosya gönder kartı
        file_outer, file_card = self._card(main, "📁  DOSYA GÖNDER")
        file_outer.grid(row=2, column=0, sticky="ew", pady=(0,10))

        dz_fg = C["accent"] if self._dnd else C["muted"]
        dz_text = ("⬇   Dosyaları buraya sürükle & bırak" if self._dnd
                   else "⬇   Dosyaları seçmek için aşağıdaki düğmeyi kullan")
        self._drop_canvas = tk.Canvas(file_card, height=66, bg=C["card"],
                                      highlightthickness=0, cursor="hand2")
        self._drop_canvas.pack(fill="x", padx=8, pady=(0,6))
        self._dz_text = dz_text; self._dz_fg = dz_fg
        self._drop_canvas.bind("<Configure>",
            lambda e: self._draw_drop_zone(self._dz_text, self._dz_fg))
        if self._dnd:
            self._drop_canvas.drop_target_register(DND_FILES)
            self._drop_canvas.dnd_bind("<<Drop>>", self._on_drop)
            self._drop_canvas.bind("<Enter>",
                lambda e: self._draw_drop_zone(self._dz_text, C["text"]))
            self._drop_canvas.bind("<Leave>",
                lambda e: self._draw_drop_zone(self._dz_text, self._dz_fg))

        btn_row = tk.Frame(file_card, bg=C["card"])
        btn_row.pack(fill="x", padx=8, pady=(0,6))
        self._btn(btn_row, "📂  Dosya Seç & Gönder", self._select_and_send,
                  accent=True).pack(side="left", padx=(0,8))
        self._btn(btn_row, "📥  Alınanlar Klasörü",
                  lambda: open_folder(str(DOWNLOADS))).pack(side="left")

        prog_frame = tk.Frame(file_card, bg=C["card"])
        prog_frame.pack(fill="x", padx=8, pady=(4,6))
        self._prog_bg = tk.Canvas(prog_frame, height=8, bg=C["panel"], highlightthickness=0)
        self._prog_bg.pack(fill="x")
        self._lbl_prog = tk.Label(prog_frame, text="", bg=C["card"],
                                  fg=C["muted"], font=(UI[0],8))
        self._lbl_prog.pack(anchor="w")

        # 4) Log
        log_outer, log_card = self._card(main, "📜  AKTİVİTE GÜNLÜĞÜ")
        log_outer.grid(row=3, column=0, sticky="nsew")
        log_inner = tk.Frame(log_card, bg=C["panel"])
        log_inner.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self._log_box = tk.Text(log_inner, bg=C["panel"], fg=C["text"],
                                font=MONO, relief="flat", state="disabled",
                                wrap="word", cursor="arrow", padx=6, pady=4,
                                insertbackground=C["accent"])
        sb = tk.Scrollbar(log_inner, orient="vertical",
                          command=self._log_box.yview,
                          bg=C["card"], troughcolor=C["panel"],
                          activebackground=C["border"])
        self._log_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self._log_box.pack(fill="both", expand=True)
        for tag,col in [("ts",C["dim"]),("info",C["accent2"]),("ok",C["success"]),
                        ("warn",C["warn"]),("err",C["danger"]),("clip",C["purple"]),
                        ("folder",C["muted"]),("search",C["dim"])]:
            self._log_box.tag_config(tag, foreground=col)

        # Thread-güvenli pencere açma için virtual event
        self.root.bind("<<TrayShow>>", lambda e: self._show_window())
        self.root.bind("<<TrayQuit>>", lambda e: self._do_quit())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════════════════════════
    #  BEKLEYEN AKTARIM KARTI
    # ══════════════════════════════════════════════════════════════════════════
    def _show_pending_card(self, kind, items, total):
        for w in self._pending_outer.winfo_children(): w.destroy()
        big = total >= SIZE_WARN_B
        accent_col = C["warn"] if big else C["accent"]
        title_text = ("⚠ BÜYÜK DOSYA — ONAY GEREKLİ" if big
                      else "📌  PANODA YENİ ÖĞE — GÖNDERMEK İSTER MİSİN?")
        wrap = tk.Frame(self._pending_outer, bg=C["bg"])
        wrap.pack(fill="x", pady=(0,10))
        tk.Frame(wrap, bg=accent_col, width=3).pack(side="left", fill="y")
        inner = tk.Frame(wrap, bg=C["card"])
        inner.pack(side="left", fill="both", expand=True)
        tr = tk.Frame(inner, bg=C["card"]); tr.pack(fill="x", padx=12, pady=(8,4))
        tk.Label(tr, text=title_text, font=(UI[0],9,"bold"),
                 bg=C["card"], fg=accent_col).pack(side="left")
        x_btn = tk.Label(tr, text="✕", font=(UI[0],11,"bold"),
                         bg=C["card"], fg=C["muted"], cursor="hand2")
        x_btn.pack(side="right")
        x_btn.bind("<Button-1>", lambda e: self._dismiss_pending())
        x_btn.bind("<Enter>", lambda e: x_btn.configure(fg=C["danger"]))
        x_btn.bind("<Leave>", lambda e: x_btn.configure(fg=C["muted"]))
        ico = "🖼" if kind=="image" else "📄" if len(items)==1 else "📦"
        name_txt = (Path(items[0]).name if len(items)==1 else f"{len(items)} dosya")
        sz_text = f"Boyut: {human_size(total)}"
        if big: sz_text += f"   ⚠  {SIZE_WARN_MB} MB üstü"
        ir = tk.Frame(inner, bg=C["card"]); ir.pack(fill="x", padx=12, pady=(0,2))
        tk.Label(ir, text=ico, font=(UI[0],22), bg=C["card"], fg=accent_col).pack(side="left", padx=(0,10))
        tc = tk.Frame(ir, bg=C["card"]); tc.pack(side="left", fill="x", expand=True)
        tk.Label(tc, text=name_txt, font=(UI[0],11,"bold"),
                 bg=C["card"], fg=C["text"], anchor="w").pack(fill="x")
        tk.Label(tc, text=sz_text, font=MONO,
                 bg=C["card"], fg=(C["warn"] if big else C["muted"]),
                 anchor="w").pack(fill="x")
        if len(items) > 1:
            for f in items[:3]:
                tk.Label(tc, text=f"   • {Path(f).name}", font=MONO,
                         bg=C["card"], fg=C["muted"], anchor="w").pack(fill="x")
            if len(items) > 3:
                tk.Label(tc, text=f"   ... ve {len(items)-3} dosya daha",
                         font=MONO, bg=C["card"], fg=C["dim"], anchor="w").pack(fill="x")
        br = tk.Frame(inner, bg=C["card"]); br.pack(fill="x", padx=12, pady=(8,10))
        self._btn(br, "✓  Gönder", lambda: self._confirm_send_pending(items),
                  accent=True).pack(side="left", padx=(0,8))
        self._btn(br, "✕  Atla", self._dismiss_pending).pack(side="left")
        self._pending = {"kind":kind, "items":items, "size":total}

    def _dismiss_pending(self):
        for w in self._pending_outer.winfo_children(): w.destroy()
        self._pending = None

    def _confirm_send_pending(self, items):
        if not self.discovery.peers():
            messagebox.showwarning("Cihaz Yok", "Gönderilecek cihaz yok.")
            return
        for f in items:
            threading.Thread(target=self._send_file, args=(f,), daemon=True).start()
        self._dismiss_pending()

    # ══════════════════════════════════════════════════════════════════════════
    #  UI YARDIMCILAR
    # ══════════════════════════════════════════════════════════════════════════
    def _card(self, parent, title, subtitle=None):
        """outer/inner yapısı: outer'ı pack veya grid ile yerleştir,
        children'ı outer.body'ye ekle. Geriye uyumlu: return (outer, inner)."""
        outer = tk.Frame(parent, bg=C["bg"])
        tk.Frame(outer, bg=C["border"], height=1).pack(fill="x")
        tb = tk.Frame(outer, bg=C["panel"]); tb.pack(fill="x")
        tk.Label(tb, text=title, font=(UI[0],8,"bold"),
                 bg=C["panel"], fg=C["muted"], padx=10, pady=5).pack(side="left")
        if subtitle:
            tk.Label(tb, text=subtitle, font=(UI[0],8),
                     bg=C["panel"], fg=C["dim"], pady=5).pack(side="left")
        inner = tk.Frame(outer, bg=C["card"]); inner.pack(fill="both", expand=True)
        tk.Frame(outer, bg=C["border"], height=1).pack(fill="x")
        outer.body = inner
        return outer, inner

    def _btn(self, parent, text, cmd, accent=False):
        bg = C["accent"] if accent else C["card"]
        fg = C["bg"]     if accent else C["text"]
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=bg, fg=fg, activebackground=C["accent2"], activeforeground="white",
                        font=(UI[0],9,"bold" if accent else "normal"),
                        relief="flat", padx=12, pady=6, cursor="hand2",
                        bd=0, highlightthickness=1,
                        highlightbackground=C["accent"] if accent else C["border"])
        btn.bind("<Enter>", lambda e,b=btn: b.configure(bg=C["accent2"], fg="white"))
        btn.bind("<Leave>", lambda e,b=btn,_bg=bg,_fg=fg: b.configure(bg=_bg, fg=_fg))
        return btn

    def _draw_drop_zone(self, text, fg):
        c = self._drop_canvas; c.delete("all")
        W = c.winfo_width() or 500; H = 66
        for i in range(0,W,12):
            c.create_line(i,0, min(i+7,W),0, fill=C["border"])
            c.create_line(i,H-1, min(i+7,W),H-1, fill=C["border"])
        for j in range(0,H,12):
            c.create_line(0,j, 0,min(j+7,H), fill=C["border"])
            c.create_line(W-1,j, W-1,min(j+7,H), fill=C["border"])
        c.create_text(W//2, H//2, text=text, font=(UI[0],11), fill=fg)

    def _draw_peer_cards(self):
        c = self._peer_canvas; c.delete("all")
        live = self.discovery.peers()
        if not live:
            self._lbl_no_peer.pack(fill="x", padx=8, pady=(0,8))
            c.configure(height=80)
            W = c.winfo_width() or 240
            c.create_text(W//2, 40, text="⏳  Cihaz bekleniyor...",
                          font=(UI[0],9,"italic"), fill=C["muted"])
            return
        self._lbl_no_peer.pack_forget()
        card_h = 64; gap = 6
        c.configure(height=min(len(live)*(card_h+gap)+4, 220))
        W = max(self._peer_canvas.winfo_width(), 220)
        ips = list(live.keys()); self._peer_card_ips = ips
        now = time.time()
        for i,(ip,info) in enumerate(live.items()):
            y1 = i*(card_h+gap)+4; y2 = y1+card_h
            sel = (ip == self._sel_peer)
            fill   = C["accent"] if sel else C["panel"]
            outln  = C["accent"] if sel else C["border"]
            txt    = C["bg"]     if sel else C["text"]
            dim    = C["bg"]     if sel else C["muted"]
            dim2   = C["bg"]     if sel else C["dim"]
            c.create_rectangle(4,y1, W-4,y2, fill=fill, outline=outln, width=1 if not sel else 2)
            # Yeşil noktalar (canlılık)
            c.create_oval(14,y1+12, 22,y1+20, fill=C["success"], outline="")
            # Hostname
            c.create_text(30,y1+15, text=info["hostname"], font=(UI[0],10,"bold"),
                          fill=txt, anchor="w")
            # IP : port
            c.create_text(30,y1+33, text=f"{ip} : {info['tcp_port']}", font=MONO,
                          fill=dim, anchor="w")
            # OS + Bağlı süresi
            since = int(now - info.get("since", now))
            if since < 60: ttl = f"{since}sn"
            elif since < 3600: ttl = f"{since//60}dk"
            else: ttl = f"{since//3600}sa{(since%3600)//60:02d}dk"
            c.create_text(30,y1+49, text=f"⏱ {ttl}  •  {info.get('os','?')}",
                          font=(UI[0],8), fill=dim2, anchor="w")

    def _on_canvas_click(self, event):
        if not hasattr(self, "_peer_card_ips"): return
        idx = (event.y - 4) // 70
        if 0 <= idx < len(self._peer_card_ips):
            self._sel_peer = self._peer_card_ips[idx]
            self._draw_peer_cards()

    def _pulse_tick(self):
        if not self.root.winfo_exists(): return
        self._pulse_phase += 0.12
        # Sağ üst (header) küçük dot
        cx,cy = 6,6
        live = bool(self.discovery.peers())
        col = C["success"] if live else C["danger"]
        self._sc.delete("all")
        if live:
            halo = 4 + 3*abs(math.sin(self._pulse_phase*0.7))
            self._sc.create_oval(cx-halo//2,cy-halo//2,cx+halo//2,cy+halo//2,
                                 fill="", outline=col, width=1)
        r = 3 + 1.5*math.sin(self._pulse_phase)
        self._sc.create_oval(cx-r//2,cy-r//2, cx+r//2,cy+r//2, fill=col, outline="")
        # Büyük ONLINE rozet
        bx,by = 7,7
        self._live_canvas.delete("all")
        if live:
            halo = 5 + 5*abs(math.sin(self._pulse_phase*0.7))
            self._live_canvas.create_oval(bx-halo//2,by-halo//2,bx+halo//2,by+halo//2,
                                          fill="", outline=col, width=1)
            self._live_canvas.create_oval(bx-3,by-3, bx+3,by+3, fill=col, outline="")
        else:
            self._live_canvas.create_oval(bx-3,by-3, bx+3,by+3, fill="", outline=col, width=1)
        self.root.after(60, self._pulse_tick)

    def _tick_periodic(self):
        """Saniye başı: peer kartları + istatistikler güncelle."""
        if not self.root.winfo_exists(): return
        self._draw_peer_cards()
        # ONLINE etiketi
        n = len(self.discovery.peers())
        if n > 0:
            self._lbl_online.configure(text="ONLINE", fg=C["success"])
            self._lbl_online_sub.configure(
                text=f"  {n} cihaz bağlı" if n==1 else f"  {n} cihaz bağlı",
                fg=C["text2"])
        else:
            self._lbl_online.configure(text="OFFLINE", fg=C["danger"])
            self._lbl_online_sub.configure(text="  cihaz aranıyor", fg=C["muted"])
        # Stats
        self._stat_labels["uptime"].configure(text=self.stats.uptime_str())
        self._stat_labels["sent"].configure(text=human_size(self.stats.bytes_sent))
        self._stat_labels["recv"].configure(text=human_size(self.stats.bytes_recv))
        self._stat_labels["speed"].configure(
            text=human_speed(self.stats.last_speed) if self.stats.last_speed else "—")
        self._stat_labels["tx"].configure(
            text=f"{self.stats.tx_count}↑ {self.stats.rx_count}↓")
        self.root.after(1000, self._tick_periodic)

    def _set_progress(self, pct, label=""):
        self._lbl_prog.configure(text=label)
        self.root.after(0, lambda: self._redraw_progress(pct))

    def _redraw_progress(self, pct):
        c = self._prog_bg; W = c.winfo_width() or 300; H = 8
        c.delete("all")
        c.create_rectangle(0,0,W,H, fill=C["panel"], outline="")
        if pct > 0:
            fw = int((pct/100)*W)
            c.create_rectangle(0,0,fw,H, fill=C["accent2"], outline="")
            c.create_rectangle(max(0,fw-30),0,fw,H, fill=C["accent"], outline="")

    # ══════════════════════════════════════════════════════════════════════════
    #  CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════
    def _on_peer_found(self, ip, info):
        self._peers[ip] = info
        self.root.after(0, self._draw_peer_cards)
        self.root.after(0, lambda: self._log("ok",
            f"Cihaz bulundu ▶  {info['hostname']}  ({ip})"))

    def _on_peer_lost(self, ip):
        name = self._peers.get(ip,{}).get("hostname", ip)
        self._peers.pop(ip, None)
        if self._sel_peer == ip: self._sel_peer = None
        self.root.after(0, self._draw_peer_cards)
        self.root.after(0, lambda: self._log("warn",
            f"Cihaz ayrıldı ◀  {name}  ({ip})"))

    def _on_clip_text(self, text):
        if not self._clip_text_v.get(): return
        peers = self.discovery.peers()
        if not peers: return
        prev = text[:60].replace("\n","↵") + ("…" if len(text)>60 else "")
        self.root.after(0, lambda: self._clip_preview.configure(text=prev, fg=C["text"]))
        self.root.after(0, lambda: self._clip_badge.configure(
            text=f"→ {len(peers)} cihaza gönderildi", fg=C["accent"]))
        self.root.after(3000, lambda: self._clip_badge.configure(text=""))
        for ip,info in peers.items():
            threading.Thread(target=ClipSender.send,
                             args=(ip,info["tcp_port"],text), daemon=True).start()
        self.root.after(0, lambda: self._log("clip",
            f"Metin → {len(peers)} cihaz  ({len(text)} kr)"))

    def _on_clip_pending(self, kind, items, total):
        peers = self.discovery.peers()
        if not peers: return

        # Hedef cihaz adı
        if self._sel_peer and self._sel_peer in peers:
            target_name = peers[self._sel_peer]["hostname"]
        else:
            target_name = list(peers.values())[0]["hostname"]

        # ─── ≤ 50 MB → ANINDA gönder, onay yok ─────────────────────────────
        if total <= SIZE_WARN_B:
            if kind == "files":
                n = len(items)
                self.root.after(0, lambda: self._clip_preview.configure(
                    text=f"📄 {n} dosya → {target_name}  ({human_size(total)})",
                    fg=C["success"]))
                self.root.after(0, lambda: self._log("clip",
                    f"Pano'da {n} dosya — otomatik gönderiliyor  ({human_size(total)})"))
            else:
                self.root.after(0, lambda: self._clip_preview.configure(
                    text=f"🖼 Görsel → {target_name}  ({human_size(total)})",
                    fg=C["success"]))
                self.root.after(0, lambda: self._log("clip",
                    f"Pano'da görsel — otomatik gönderiliyor  ({human_size(total)})"))
            for f in items:
                threading.Thread(target=self._send_file, args=(f,), daemon=True).start()
            return

        # ─── > 50 MB → onay kartı göster ──────────────────────────────────
        self.root.after(0, lambda: self._show_pending_card(kind, items, total))
        if kind == "files":
            n = len(items)
            self.root.after(0, lambda: self._clip_preview.configure(
                text=f"📄 {n} dosya — onay bekliyor  ({human_size(total)})",
                fg=C["warn"]))
            self.root.after(0, lambda: self._log("clip",
                f"Pano'da {n} dosya — onay bekliyor ⚠  ({human_size(total)})"))
        else:
            self.root.after(0, lambda: self._clip_preview.configure(
                text=f"🖼 Görsel — onay bekliyor  ({human_size(total)})",
                fg=C["warn"]))
            self.root.after(0, lambda: self._log("clip",
                f"Pano'da görsel — onay bekliyor ⚠  ({human_size(total)})"))

    def _on_clip_rx(self, from_ip, text):
        if not self._clip_text_v.get(): return
        self.clip_monitor.set_from_remote_text(text)
        name = self._peers.get(from_ip,{}).get("hostname", from_ip)
        prev = text[:60].replace("\n","↵") + ("…" if len(text)>60 else "")
        self.root.after(0, lambda: self._clip_preview.configure(text=prev, fg=C["warn"]))
        self.root.after(0, lambda: self._clip_badge.configure(
            text=f"← {name}'den senkronize edildi", fg=C["success"]))
        self.root.after(3000, lambda: self._clip_badge.configure(text=""))
        self.root.after(0, lambda: self._log("clip", f"Metin ← {name}  ({len(text)} kr)"))

    def _on_file_rx(self, from_ip, filename, filesize, dest, speed_bps):
        """Dosya alındı. Görsel ise panoya da kopyala."""
        self.stats.bytes_recv += filesize
        self.stats.rx_count   += 1
        self.stats.last_speed  = speed_bps
        name = self._peers.get(from_ip,{}).get("hostname", from_ip)
        self.root.after(0, lambda: self._log("ok",
            f"Dosya alındı ← {name}: {filename}  ({human_size(filesize)} @ {human_speed(speed_bps)})"))

        # ── Görselse panoya da kopyala ────────────────────────────────────
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTS:
            def _do_copy():
                # Döngüyü engelle: önce monitor'e bu hash'i bildir
                self.clip_monitor.mark_remote_image(dest)
                if copy_image_to_clipboard(dest):
                    self._log("clip",
                              f"🖼 Görsel panoya kopyalandı — anında Cmd/Ctrl+V")
                    self._clip_preview.configure(
                        text=f"🖼 {Path(filename).name}\n(panoya yapıştırılmaya hazır)",
                        fg=C["success"])
                    self._clip_badge.configure(
                        text=f"← {name}'den görsel panoda", fg=C["success"])
                    self.root.after(5000, lambda: self._clip_badge.configure(text=""))
            self.root.after(0, _do_copy)

        self.root.after(0, lambda: messagebox.showinfo(
            "✅ Dosya Alındı",
            f"Kimden : {name}\nDosya  : {filename}\n"
            f"Boyut  : {human_size(filesize)}\n"
            f"Hız    : {human_speed(speed_bps)}\n\nKonum  : {dest}" +
            ("\n\n🖼 Görsel panoya kopyalandı." if ext in IMAGE_EXTS else "")))

    def _on_drop(self, event):
        for f in self.root.tk.splitlist(event.data):
            threading.Thread(target=self._send_file, args=(f,), daemon=True).start()

    def _select_and_send(self):
        if not self.discovery.peers():
            messagebox.showwarning("Cihaz Yok", "Ağda LanBridge cihazı yok.")
            return
        files = filedialog.askopenfilenames(title="Gönderilecek dosyaları seçin")
        for f in files:
            threading.Thread(target=self._send_file, args=(f,), daemon=True).start()

    def _send_file(self, filepath):
        peers = self.discovery.peers()
        if not peers:
            self.root.after(0, lambda: messagebox.showwarning("Cihaz Yok", "Bağlı cihaz yok."))
            return
        if self._sel_peer and self._sel_peer in peers:
            tip, tinfo = self._sel_peer, peers[self._sel_peer]
        else:
            tip, tinfo = list(peers.items())[0]
        p = Path(filepath); sz = p.stat().st_size
        self.root.after(0, lambda: self._log("info",
            f"Gönderiliyor → {tinfo['hostname']}: {p.name}  ({human_size(sz)})"))
        def _prog(s,t):
            pct = (s/t*100) if t else 100
            self.root.after(0, lambda: self._set_progress(pct,
                f"{human_size(s)} / {human_size(t)}  ({pct:.1f}%)"))
        try:
            speed = FileSender.send(tip, tinfo["tcp_port"], filepath, _prog)
            self.stats.bytes_sent += sz
            self.stats.tx_count   += 1
            self.stats.last_speed  = speed
            self.root.after(0, lambda: self._log("ok",
                f"Tamamlandı ✓ → {tinfo['hostname']}: {p.name}  @ {human_speed(speed)}"))
            self.root.after(2500, lambda: self._set_progress(0, ""))
        except Exception as e:
            self.root.after(0, lambda: self._log("err", f"Gönderim hatası: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Hata", str(e)))

    def _log(self, level, msg):
        icons = {"info":"·","ok":"✓","warn":"⚠","err":"✗",
                 "clip":"◈","folder":"⊞","search":"○"}
        ts = datetime.now().strftime("%H:%M:%S")
        ic = icons.get(level,"·")
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"[{ts}] ", "ts")
        self._log_box.insert("end", f"{ic} {msg}\n", level)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    #  SİSTEM TEPSİSİ
    # ══════════════════════════════════════════════════════════════════════════
    def _setup_tray(self):
        """pystray ile sistem tepsisi/menü çubuğu ikonu kur."""
        if sys.platform == 'darwin' and not load_setting("macos_tray_enabled", False):
            self._log("info", "macOS sistem tepsisi devre dışı (Ayarlar'dan açabilirsin)")
            return
        
        if not (PYSTRAY_AVAILABLE and PIL_AVAILABLE):
            self._log("warn", "Sistem tepsisi desteği için: pip install pystray")
            return
        try:
            img = make_tray_icon_image()
            if img is None: return
            
            if sys.platform == 'darwin':
                self._setup_macos_tray(img)
            else:
                menu = pystray.Menu(
                    pystray.MenuItem("LanBridge'i Aç", self._tray_show, default=True),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Alınanlar Klasörü",
                                     lambda: open_folder(str(DOWNLOADS))),
                    pystray.MenuItem(lambda item: f"Cihaz sayısı: {len(self.discovery.peers())}",
                                     None, enabled=False),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Çıkış", self._tray_quit),
                )
                self._tray_icon = pystray.Icon(
                    name="LanBridge",
                    icon=img,
                    title=f"LanBridge — {HOSTNAME}",
                    menu=menu,
                )
                self._tray_icon.run_detached()
            self._log("ok", "Sistem tepsisi ikonu hazır")
        except Exception as e:
            self._log("warn", f"Tepsi ikonu kurulamadı: {e}")
            self._tray_icon = None

    def _setup_macos_tray(self, img):
        """macOS NSStatusBar — action'lar sinyal dosyası üzerinden ana thread'e iletilir."""
        from Cocoa import (NSStatusBar, NSMenu, NSMenuItem, NSImage,
                           NSApplication, NSApp)
        import tempfile as _tf, os as _os
        
        # NSApp'ı initialize et (Tk ile beraber çalışacak)
        try: NSApplication.sharedApplication()
        except Exception: pass
        
        tmp_path = _os.path.join(_tf.gettempdir(), "lanbridge_tray.png")
        img.save(tmp_path)
        
        # Sinyal dosyaları — AppleScript ile yazılacak, Python ana thread polling yapacak
        self._tray_signal_dir = Path(_tf.gettempdir()) / "lanbridge_signals"
        self._tray_signal_dir.mkdir(exist_ok=True)
        
        status_bar = NSStatusBar.systemStatusBar()
        self._tray_item = status_bar.statusItemWithLength_(-1)
        
        ns_img = NSImage.alloc().initByReferencingFile_(tmp_path)
        ns_img.setSize_((18, 18))
        self._tray_item.setImage_(ns_img)
        
        ns_menu = NSMenu.new()
        
        # NSMenuItem action'ları → shell komut çalıştır (Python callback YOK)
        # Shell komut sinyal dosyası oluşturur, Python tarafı bunu okur
        sig_show = str(self._tray_signal_dir / "show")
        sig_folder = str(self._tray_signal_dir / "folder")
        sig_quit = str(self._tray_signal_dir / "quit")
        
        # NSMenuItem target=nil + action=nil → menü item TIKLANABILIR ama callback yok
        # Bunun yerine view-based item kullan
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("LanBridge'i Aç", None, "")
        ns_menu.addItem_(open_item)
        
        ns_menu.addItem_(NSMenuItem.separatorItem())
        
        folder_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Alınanlar Klasörü", None, "")
        ns_menu.addItem_(folder_item)
        
        ns_menu.addItem_(NSMenuItem.separatorItem())
        
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Çıkış", None, "")
        ns_menu.addItem_(quit_item)
        
        self._tray_item.setMenu_(ns_menu)
        self._ns_tray_image_path = tmp_path
        self._tray_icon = True
        
        # Menü item referanslarını sakla — sonra delegate atayacağız
        self._tray_menu_items = {
            'show': open_item,
            'folder': folder_item,
            'quit': quit_item,
        }
        
        # PyObjC delegate'i Python callback olmadan kuralım
        self._install_macos_menu_delegate()
    
    def _install_macos_menu_delegate(self):
        """NSMenu delegate — highlight event ile state takip et."""
        from Cocoa import NSObject
        import objc
        
        # Sınıf zaten register edilmişse tekrar etme
        if not hasattr(LanBridgeApp, '_MenuDelegate'):
            class _MenuDelegate(NSObject):
                def menu_willHighlightItem_(self, menu, item):
                    pass
                def menuDidClose_(self, menu):
                    # Hangi item seçildi?
                    try:
                        sel = menu.highlightedItem()
                        if sel is None: return
                        title = str(sel.title())
                        app = LanBridgeApp._current_instance
                        if app is None: return
                        if title == "LanBridge'i Aç":
                            app.root.after(0, app._show_window)
                        elif title == "Alınanlar Klasörü":
                            app.root.after(0, lambda: open_folder(str(DOWNLOADS)))
                        elif title == "Çıkış":
                            app.root.after(0, app._do_quit)
                    except Exception: pass
            LanBridgeApp._MenuDelegate = _MenuDelegate
        
        LanBridgeApp._current_instance = self
        self._menu_delegate = LanBridgeApp._MenuDelegate.alloc().init()
        self._tray_item.menu().setDelegate_(self._menu_delegate)
    def _tray_show(self, icon=None, item=None):
        """Tepsiden 'Aç' tıklandı — virtual event ile thread-güvenli iletim."""
        try:
            # event_generate thread-safe; tkinter ana thread'i işler
            self.root.event_generate("<<TrayShow>>", when="tail")
        except Exception:
            try: self.root.after(0, self._show_window)
            except Exception: pass
    
    def _show_window(self):
        """Pencereyi göster — ana thread'de çalışır."""
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception as e:
            try: self._log("err", f"Pencere açılamadı: {e}")
            except Exception: pass
            return

        # macOS: uygulamayı öne getir (focus_force yerine osascript)
        if platform.system() == "Darwin":
            try:
                os.system(
                    f"osascript -e 'tell application \"System Events\" "
                    f"to set frontmost of (first process whose unix id is {os.getpid()}) "
                    f"to true' >/dev/null 2>&1 &"
                )
            except Exception: pass
        else:
            # Windows/Linux: kısa topmost flash
            try:
                self.root.attributes("-topmost", True)
                self.root.after(200, lambda: self.root.attributes("-topmost", False))
            except Exception: pass

    def _tray_quit(self, icon=None, item=None):
        """Tepsiden 'Çıkış' tıklandı — gerçekten kapat (thread-güvenli)."""
        try:
            self.root.event_generate("<<TrayQuit>>", when="tail")
        except Exception:
            try: self.root.after(0, self._do_quit)
            except Exception: pass

    def _do_quit(self):
        """Gerçek kapatma — ana thread'de."""
        self._really_quit = True
        
        # macOS: NSStatusBar'ı önce temizle (crash önleme)
        if sys.platform == 'darwin' and hasattr(self, '_tray_item') and self._tray_item is not None:
            try:
                from Cocoa import NSStatusBar
                NSStatusBar.systemStatusBar().removeStatusItem_(self._tray_item)
                self._tray_item = None
            except Exception: pass
        
        # Windows: pystray icon stop
        if self._tray_icon and sys.platform != 'darwin':
            try: self._tray_icon.stop()
            except Exception: pass
        
        # Servisleri durdur
        try: self.discovery.stop()
        except Exception: pass
        try: self.clip_monitor.stop()
        except Exception: pass
        try: self.tcp_server.stop()
        except Exception: pass
        
        # Instance lock'u serbest bırak
        global _instance_socket
        if _instance_socket:
            try: _instance_socket.close()
            except Exception: pass
            _instance_socket = None
        
        try: self.root.destroy()
        except Exception: pass

    def _instance_listener(self):
        """Başka bir LanBridge instance'ı açılmaya çalışırsa SHOW sinyali al."""
        global _instance_socket
        if _instance_socket is None: return
        _instance_socket.settimeout(1.0)
        while not self._really_quit:
            try:
                conn, _ = _instance_socket.accept()
                data = conn.recv(16)
                conn.close()
                if data == b"SHOW":
                    self.root.after(0, self._show_window)
            except socket.timeout: continue
            except: break
    def _on_close(self):
        """X düğmesi: tepsi varsa gizle, yoksa gerçekten çık."""
        if self._tray_icon is not None and not self._really_quit:
            self.root.withdraw()
            if not self._tray_notified and sys.platform != 'darwin':
                try:
                    self._tray_icon.notify(
                        "LanBridge arka planda çalışıyor.\n"
                        "Tepsi ikonuna sağ tıklayıp 'Çıkış' ile kapatabilirsin.",
                        "LanBridge"
                    )
                except Exception: pass
                self._tray_notified = True
        else:
            self.discovery.stop(); self.clip_monitor.stop(); self.tcp_server.stop()
            if self._tray_icon and sys.platform != 'darwin':
                try: self._tray_icon.stop()
                except Exception: pass
            self.root.destroy()

    def run(self):
        self.root.mainloop()

# ══════════════════════════════════════════════════════════════════════════════
def _run():
    app = LanBridgeApp()
    app.run()

if __name__ == "__main__":
    log_path = Path.home() / "lanbridge_error.log"
    try:
        _run()
    except Exception:
        import traceback
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.now()} ===\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Platform: {platform.system()} {platform.release()}\n")
            f.write(traceback.format_exc())
            f.write("\n")
        # Debug modunda terminale de bas
        if "--debug" in sys.argv or "--no-detach" in sys.argv:
            traceback.print_exc()
        raise
