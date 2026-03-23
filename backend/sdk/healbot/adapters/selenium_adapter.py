"""
selenium_adapter.py

Patches selenium.webdriver.remote.webdriver.WebDriver.find_element
at the CLASS level so every Chrome/Firefox/Edge driver instance
anywhere in the test suite gets automatic healing.

No driver wrapping. No test changes. Just works.
"""
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def _to_xpath(by, value):
    """Convert any Selenium locator strategy to an XPath string."""
    mapping = {
        "id":                 "//*[@id='" + value + "']",
        "name":               "//*[@name='" + value + "']",
        "class name":         "//*[contains(@class,'" + value + "')]",
        "tag name":           "//" + value,
        "link text":          "//a[normalize-space()='" + value + "']",
        "partial link text":  "//a[contains(text(),'" + value + "')]",
        "css selector":       value,
        "xpath":              value,
    }
    return mapping.get(by, value)


class SeleniumAdapter:
    """
    Monkey-patches WebDriver.find_element and find_elements at the class
    level. Intercepts NoSuchElementException and calls HealBot before
    re-raising, so broken selectors heal transparently mid-test.
    """

    def __init__(self, hb):
        self._hb = hb
        self._orig_find = None
        self._orig_finds = None

    def patch(self):
        from selenium.webdriver.remote.webdriver import WebDriver

        hb = self._hb
        orig_find = WebDriver.find_element
        orig_finds = WebDriver.find_elements

        self._orig_find = orig_find
        self._orig_finds = orig_finds

        def healed_find_element(driver_self, by, value):
            try:
                return orig_find(driver_self, by, value)
            except NoSuchElementException as original_err:
                test_name = getattr(hb, "_current_test", "")
                print(
                    "\n[HealBot] Selector failed: (%s, '%s') — healing..." % (by, value))
                healed = hb.heal(
                    selector=_to_xpath(by, value),
                    html=driver_self.page_source,
                    test_name=test_name,
                )
                if healed:
                    try:
                        return orig_find(driver_self, By.XPATH, healed)
                    except NoSuchElementException:
                        print("[HealBot] Healed selector also failed: %s" % healed)
                raise original_err

        def healed_find_elements(driver_self, by, value):
            elements = orig_finds(driver_self, by, value)
            if not elements:
                test_name = getattr(hb, "_current_test", "")
                print(
                    "\n[HealBot] find_elements empty: (%s, '%s') — healing..." % (by, value))
                healed = hb.heal(
                    selector=_to_xpath(by, value),
                    html=driver_self.page_source,
                    test_name=test_name,
                )
                if healed:
                    healed_list = orig_finds(driver_self, By.XPATH, healed)
                    if healed_list:
                        return healed_list
            return elements

        WebDriver.find_element = healed_find_element
        WebDriver.find_elements = healed_find_elements
        print("[HealBot] Selenium patched — find_element is now self-healing")

    def unpatch(self):
        from selenium.webdriver.remote.webdriver import WebDriver
        if self._orig_find is not None:
            WebDriver.find_element = self._orig_find
            WebDriver.find_elements = self._orig_finds
            self._orig_find = None
            self._orig_finds = None
            print("[HealBot] Selenium unpatched — find_element restored")
