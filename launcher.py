import os
import shutil
import sys
import webbrowser
import threading
import time

import uvicorn

# Explicit imports for PyInstaller to detect the full backend package
import backend.main
import backend.api.routes
import backend.models.database
import backend.fetcher.akshare_fetcher
import backend.analyzer.llm_analyzer
import backend.config_loader
import backend.scheduler
import backend.alert_engine


def ensure_config():
    """Ensure config.yaml exists, copy from example if not."""
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(exe_dir, "config.yaml")

    if not os.path.exists(config_path):
        example_path = None
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            bundled = os.path.join(sys._MEIPASS, "config.example.yaml")
            if os.path.exists(bundled):
                example_path = bundled
        if example_path is None:
            local = os.path.join(exe_dir, "config.example.yaml")
            if os.path.exists(local):
                example_path = local

        if example_path:
            print(f"Creating default config: {config_path}")
            shutil.copy2(example_path, config_path)
        else:
            print(f"Warning: config.example.yaml not found, please create {config_path} manually")
            return False

    return os.path.exists(config_path)


def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")


def main():
    print("=" * 50)
    print("  Futures Position AI Analyzer v2.1")
    print("=" * 50)
    print()

    if not ensure_config():
        print("Default config created. Please edit config.yaml and restart.")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
