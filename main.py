#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import glob
import shutil
import socket
import threading
import urllib.request

BLUE = "\033[34m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloaded_packages")
LOCAL_DIR = os.path.join(BASE_DIR, "local_packages")
UPDATE_DIR = os.path.join(BASE_DIR, "update")
REQ_FILE = os.path.join(BASE_DIR, "requirements.txt")

APP_URL = "https://raw.githubusercontent.com/Virensahtiofficial/omx/refs/heads/main/app.py"
MAIN_URL = "https://raw.githubusercontent.com/Virensahtiofficial/omx/refs/heads/main/main.py"
REQ_URL = "https://raw.githubusercontent.com/Virensahtiofficial/omx/refs/heads/main/requirements.txt"

LOG_PATH = os.path.join(BASE_DIR, "launcher_update.log")

def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except:
        pass

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def get_terminal_size():
    try:
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except:
        return 80, 24

def center_text(text, width):
    return " " * max(0, (width // 2) - (len(text) // 2)) + text

def move_cursor(row: int, col: int = 1):
    print(f"\033[{row};{col}H", end="", flush=True)

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def animated_loading(stop_event, term_width, loading_y, term_height, msg="Loading"):
    dots = 0
    while not stop_event.is_set():
        text = f"{BLUE}{msg}{'.' * (dots % 4)}{RESET}"
        move_cursor(loading_y, 1)
        print(center_text(text, term_width), end="", flush=True)
        time.sleep(0.4)
        dots += 1
    move_cursor(term_height, 1)

def download_url_to_file(url, dest, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OMX-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                log(f"download failed {url} status {resp.status}")
                return False
            data = resp.read()
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
        log(f"downloaded {url} -> {dest}")
        return True
    except Exception as e:
        log(f"download error {url} {e}")
        return False

def safe_copy(src, dst):
    try:
        tmp = dst + ".tmp"
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
        return True
    except Exception as e:
        log(f"safe_copy error {src} -> {dst} {e}")
        return False

def update_files():
    os.makedirs(UPDATE_DIR, exist_ok=True)
    clear_screen()
    term_width, term_height = get_terminal_size()
    title_y = term_height // 2
    loading_y = title_y + 1
    move_cursor(title_y, 1)
    print(center_text(f"{CYAN}{BOLD}Checking for updates...{RESET}", term_width), end="", flush=True)
    stop_event = threading.Event()
    loader_thread = threading.Thread(target=animated_loading, args=(stop_event, term_width, loading_y, term_height, "Updating"))
    loader_thread.start()
    req_path = os.path.join(UPDATE_DIR, "requirements.txt")
    app_path = os.path.join(UPDATE_DIR, "app.py")
    main_path = os.path.join(UPDATE_DIR, "main.py")
    try:
        req_ok = False
        if check_internet():
            req_ok = download_url_to_file(REQ_URL, req_path)
            if not req_ok:
                log("requirements download failed")
        else:
            log("no internet for requirements download")
        if not req_ok and os.path.exists(REQ_FILE):
            log("using existing requirements.txt")
            req_ok = True
        if req_ok:
            if os.path.exists(req_path):
                safe_copy(req_path, REQ_FILE)
            log("requirements ready")
            app_ok = False
            main_ok = False
            if check_internet():
                app_ok = download_url_to_file(APP_URL, app_path)
                main_ok = download_url_to_file(MAIN_URL, main_path)
            if app_ok:
                safe_copy(app_path, os.path.join(BASE_DIR, "app.py"))
            if main_ok:
                safe_copy(main_path, os.path.join(BASE_DIR, "main.py"))
            log(f"update results app_ok={app_ok} main_ok={main_ok}")
        else:
            log("no requirements available, skipping update of code and packages")
    finally:
        stop_event.set()
        loader_thread.join()
        time.sleep(0.3)
        clear_screen()

def read_requirements():
    if not os.path.exists(REQ_FILE):
        return []
    try:
        with open(REQ_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
        pkgs = []
        for l in lines:
            if l.startswith("-r ") or l.startswith("--requirement"):
                continue
            pkgs.append(l)
        return pkgs
    except Exception as e:
        log(f"read_requirements error {e}")
        return []

def download_packages(packages):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    if not packages:
        return True
    if not check_internet():
        log("no internet, skipping package download")
        return False
    for pkg in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "download", pkg, "-d", DOWNLOAD_DIR, "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log(f"downloaded package {pkg}")
        except subprocess.CalledProcessError as e:
            log(f"pip download failed {pkg} {e}")
            return False
    return True

def install_from_download():
    os.makedirs(LOCAL_DIR, exist_ok=True)
    files = glob.glob(os.path.join(DOWNLOAD_DIR, "*"))
    if not files:
        log("no downloaded files to install")
        return False
    for file in files:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", file, "--target", LOCAL_DIR, "--break-system-packages", "--upgrade", "--no-deps", "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log(f"installed {file} to {LOCAL_DIR}")
        except subprocess.CalledProcessError as e:
            log(f"pip install failed {file} {e}")
            return False
    return True

def start_intro_and_install():
    clear_screen()
    term_width, term_height = get_terminal_size()
    title = f"{CYAN}{BOLD}OMX Mail Client Launcher{RESET}"
    title_y = term_height // 2
    loading_y = title_y + 1
    move_cursor(title_y, 1)
    print(center_text(title, term_width), end="", flush=True)
    stop_event = threading.Event()
    loader_thread = threading.Thread(target=animated_loading, args=(stop_event, term_width, loading_y, term_height))
    loader_thread.start()
    try:
        pkgs = read_requirements()
        if pkgs:
            download_ok = download_packages(pkgs)
            if download_ok:
                install_ok = install_from_download()
                if install_ok:
                    if LOCAL_DIR not in sys.path:
                        sys.path.insert(0, LOCAL_DIR)
                    log("local packages installed and added to sys.path")
                else:
                    log("install_from_download failed, will attempt to continue")
            else:
                log("download_packages failed or skipped, attempting to use existing local packages if present")
                if os.path.exists(LOCAL_DIR) and os.listdir(LOCAL_DIR):
                    if LOCAL_DIR not in sys.path:
                        sys.path.insert(0, LOCAL_DIR)
                    log("using existing local packages")
                else:
                    log("no local packages available")
        else:
            log("no requirements specified, skipping package install")
    finally:
        stop_event.set()
        loader_thread.join()
        time.sleep(0.2)
        clear_screen()

if __name__ == "__main__":
    if LOCAL_DIR not in sys.path:
        sys.path.insert(0, LOCAL_DIR)
    try:
        update_files()
        start_intro_and_install()
        try:
            import app
        except Exception as e:
            log(f"import app failed {e}")
            raise
        try:
            if hasattr(app, "load_config"):
                app.load_config()
            if hasattr(app, "CONFIG") and hasattr(app, "DEFAULT_SERVER"):
                app.SERVER_URL = app.CONFIG.get("server_url", app.DEFAULT_SERVER)
            elif hasattr(app, "CONFIG"):
                app.SERVER_URL = app.CONFIG.get("server_url", "http://omx.dedyn.io:30174")
        except Exception as e:
            log(f"app config load failed {e}")
        try:
            if hasattr(app, "main_menu"):
                app.main_menu()
            elif hasattr(app, "main"):
                app.main()
            else:
                log("no entry point found in app")
        except Exception as e:
            log(f"app runtime error {e}")
            raise
    except ModuleNotFoundError as e:
        print(f"\n{RED}Error: Required package missing. {e}{RESET}")
        log(f"ModuleNotFoundError {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        try:
            if 'app' in globals() and hasattr(app, "printc") and hasattr(app, "C"):
                app.printc("Interrupted. Bye.", app.C.YELLOW)
            else:
                print("\nInterrupted. Bye.")
        except:
            print("\nInterrupted. Bye.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        log(f"fatal error {e}")
        sys.exit(1)