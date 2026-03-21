from core.logger import log
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import sys
import os

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def get_driver(headless: bool = False, ctx=None) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    if headless or os.environ.get("HEALBOT_HEADLESS") == "1":
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    log("DRIVER", "Chrome driver initialised", ctx=ctx)
    return driver
