# ── sys.path fix ──
from core.logger import log
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import sys as _sys
import os as _os
_BACKEND_DIR = _os.path.abspath(__file__)
_BACKEND_DIR = _os.path.dirname(_BACKEND_DIR)
if _BACKEND_DIR not in _sys.path:
    _sys.path.insert(0, _BACKEND_DIR)
# ── sys.path fix ──


def get_driver(headless: bool = False, ctx=None) -> webdriver.Chrome:
    """
    Returns a configured Chrome WebDriver.
    Headless mode is auto-enabled when HEALBOT_HEADLESS=1 env var is set
    (e.g. when launched with: python run.py --headless)
    """
    options = Options()
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    # Check env var OR explicit argument
    if headless or _os.environ.get("HEALBOT_HEADLESS") == "1":
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    log("DRIVER", "Chrome driver initialised", ctx=ctx)
    return driver
