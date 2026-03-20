"""
Dynamic intent resolution — three-tier priority:

  1. Step-level explicit `intent` field  (always wins — set in journey JSON)
  2. Client custom map                   (POST /intent-map to register)
  3. Built-in keyword rules              (fallback)

Client intent map schema (POST /intent-map):
  {
    "client_id": "acme",
    "mappings": [
      { "keywords": ["frm_usr", "account_field"], "intent": "username input field" },
      { "keywords": ["frm_pwd"],                  "intent": "password input field"  }
    ]
  }
"""

import re
import threading
from typing import Optional

_lock = threading.Lock()
_custom_maps: dict = {}   # client_id → list[{keywords, intent}]

_BUILTIN = [
    (["user-name", "user_name", "username", "email",
     "uname", "account"], "username input field"),
    (["password", "pass", "pwd", "secret"],
     "password input field"),
    (["login-button", "login_button", "login",
     "signin", "sign-in"],     "login submit button"),
    (["logout", "signout", "sign-out"],
     "logout button"),
    (["add-to-cart", "add_to_cart", "addtocart",
      "add-backpack", "add-bike", "add-jacket",
      "add-onesie", "add-bolt", "add-red"],                            "add to cart button"),
    (["checkout"],
     "checkout button"),
    (["continue"],
     "continue button on checkout form"),
    (["first-name", "first_name", "firstname", "fname"],
     "first name input field"),
    (["last-name", "last_name", "lastname", "lname"],
     "last name input field"),
    (["postal-code", "postal_code", "postcode", "zipcode",
     "zip"],       "postal code zip input field"),
    (["shopping_cart_link", "shopping-cart", "cart"],
     "shopping cart link"),
    (["search", "query", "find"],
     "search input field"),
    (["submit"],
     "submit button"),
]


def register_intent_map(client_id: str, mappings: list):
    with _lock:
        _custom_maps[client_id] = mappings


def get_all_intent_maps() -> dict:
    with _lock:
        return dict(_custom_maps)


def infer_intent_from_selector(selector: str, client_id: Optional[str] = None) -> str:
    clean = re.sub(r"[/\[\]@'\"=*()]", " ", selector.lower())

    # Client custom map first
    if client_id:
        with _lock:
            custom = _custom_maps.get(client_id, [])
        for rule in custom:
            if any(kw.lower() in clean for kw in rule.get("keywords", [])):
                return rule["intent"]

    # Built-in rules
    for keywords, intent in _BUILTIN:
        if any(kw in clean for kw in keywords):
            return intent

    return "interactive web element"
