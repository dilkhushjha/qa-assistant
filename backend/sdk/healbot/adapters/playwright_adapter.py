"""
playwright_adapter.py

Patches sync Playwright's Page.locator to return a HealingLocator proxy.
When a locator action times out, the proxy heals the selector and retries.

Only activates if playwright is installed. Safe to import even if it is not.
"""


class HealingLocator:
    """
    Proxy around a Playwright Locator.
    Intercepts action methods and heals on TimeoutError.
    """

    def __init__(self, page, selector, locator, hb):
        self._page = page
        self._selector = selector
        self._locator = locator
        self._hb = hb

    def _try(self, method_name, *args, **kwargs):
        try:
            return getattr(self._locator, method_name)(*args, **kwargs)
        except Exception as err:
            if "Timeout" not in type(err).__name__:
                raise
            print("\n[HealBot] Playwright locator.%s timed out: '%s' — healing..."
                  % (method_name, self._selector))
            try:
                healed = self._hb.heal(self._selector, self._page.content())
            except Exception:
                raise err
            if healed:
                try:
                    new_loc = self._page._hb_orig_locator(healed)
                    return getattr(new_loc, method_name)(*args, **kwargs)
                except Exception:
                    pass
            raise err

    # ── Common locator actions ────────────────────────────────────────────────
    def click(self, **kw): return self._try("click", **kw)
    def fill(self, value, **kw): return self._try("fill", value, **kw)
    def type(self, text, **kw): return self._try("type", text, **kw)
    def press(self, key, **kw): return self._try("press", key, **kw)
    def check(self, **kw): return self._try("check", **kw)
    def uncheck(self, **kw): return self._try("uncheck", **kw)
    def inner_text(self, **kw): return self._try("inner_text", **kw)
    def text_content(self, **kw): return self._try("text_content", **kw)
    def input_value(self, **kw): return self._try("input_value", **kw)
    def is_visible(self, **kw): return self._try("is_visible", **kw)
    def is_enabled(self, **kw): return self._try("is_enabled", **kw)
    def wait_for(self, **kw): return self._try("wait_for", **kw)

    def scroll_into_view_if_needed(self, **kw):
        return self._try("scroll_into_view_if_needed", **kw)

    def __getattr__(self, name):
        """Pass through any locator method not explicitly overridden."""
        return getattr(self._locator, name)

    def __repr__(self):
        return "HealingLocator(selector=%r)" % self._selector


class PlaywrightAdapter:
    """Patches sync Playwright Page.locator."""

    def __init__(self, hb):
        self._hb = hb
        self._orig = None

    def patch(self):
        try:
            from playwright.sync_api import Page
        except ImportError:
            print("[HealBot] Playwright not installed — skipping patch")
            return

        hb = self._hb
        orig = Page.locator
        self._orig = orig

        def healed_locator(page_self, selector, **kwargs):
            # Store original locator method on page instance for use in HealingLocator
            page_self._hb_orig_locator = lambda s: orig(page_self, s)
            raw = orig(page_self, selector, **kwargs)
            return HealingLocator(page_self, selector, raw, hb)

        Page.locator = healed_locator
        print("[HealBot] Playwright patched — Page.locator is now self-healing")

    def unpatch(self):
        if self._orig is not None:
            try:
                from playwright.sync_api import Page
                Page.locator = self._orig
                self._orig = None
                print("[HealBot] Playwright unpatched — Page.locator restored")
            except ImportError:
                pass
