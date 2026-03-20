"""
Built-in demo journey for https://www.saucedemo.com

Real selectors (verified):
  username input  → id="user-name"
  password input  → id="password"
  login button    → id="login-button"
  add to cart     → id="add-to-cart-sauce-labs-backpack"
  cart link       → class="shopping_cart_link"
  checkout button → id="checkout"
  first name      → id="first-name"
  last name       → id="last-name"
  postal code     → id="postal-code"
  continue button → id="continue"

Steps marked # BROKEN use wrong IDs to demonstrate healing.
Steps marked # CORRECT are intentionally passing to test the memory/pass path.
"""

JOURNEY_STEPS = [
    {
        "id":          "open_site",
        "description": "Open Sauce Demo",
        "url":         "https://www.saucedemo.com/",
        "action":      "wait",
        # CORRECT — page load gate
        "selector":    "//div[@class='login_logo']",
        "value":       None,
        "intent":      "page load confirmation",
        "critical":    True,
    },
    {
        "id":          "enter_username",
        "description": "Enter username",
        "url":         None,
        "action":      "type",
        "selector":    "//input[@id='broken-username']",  # BROKEN
        "value":       "standard_user",
        "intent":      "username input field",
        "critical":    True,
    },
    {
        "id":          "enter_password",
        "description": "Enter password",
        "url":         None,
        "action":      "type",
        "selector":    "//input[@id='broken-password']",  # BROKEN
        "value":       "secret_sauce",
        "intent":      "password input field",
        "critical":    True,
    },
    {
        "id":          "click_login",
        "description": "Click Login",
        "url":         None,
        "action":      "click",
        "selector":    "//input[@id='broken-login-btn']",  # BROKEN
        "value":       None,
        "intent":      "login submit button",
        "critical":    True,
    },
    {
        "id":          "assert_inventory",
        "description": "Assert inventory page loaded",
        "url":         None,
        "action":      "assert_url",
        "selector":    None,
        "value":       "/inventory",
        "intent":      "url verification",
        "critical":    True,
    },
    {
        "id":          "add_to_cart",
        "description": "Add Backpack to cart",
        "url":         None,
        "action":      "click",
        "selector":    "//button[@id='broken-add-backpack']",  # BROKEN
        "value":       None,
        "intent":      "add to cart button",
        "critical":    False,
    },
    {
        "id":          "open_cart",
        "description": "Open cart",
        "url":         None,
        "action":      "click",
        # CORRECT — tests pass path
        "selector":    "//a[@class='shopping_cart_link']",
        "value":       None,
        "intent":      "shopping cart link",
        "critical":    False,
    },
    {
        "id":          "assert_cart",
        "description": "Assert cart page loaded",
        "url":         None,
        "action":      "assert_url",
        "selector":    None,
        "value":       "/cart",
        "intent":      "url verification",
        "critical":    False,
    },
    {
        "id":          "checkout",
        "description": "Click Checkout",
        "url":         None,
        "action":      "click",
        "selector":    "//button[@id='broken-checkout']",  # BROKEN
        "value":       None,
        "intent":      "checkout button",
        "critical":    False,
    },
    {
        "id":          "fill_first_name",
        "description": "Fill first name",
        "url":         None,
        "action":      "type",
        "selector":    "//input[@id='broken-fname']",  # BROKEN
        "value":       "John",
        "intent":      "first name input field",
        "critical":    False,
    },
    {
        "id":          "fill_last_name",
        "description": "Fill last name",
        "url":         None,
        "action":      "type",
        "selector":    "//input[@id='broken-lname']",  # BROKEN
        "value":       "Doe",
        "intent":      "last name input field",
        "critical":    False,
    },
    {
        "id":          "fill_zip",
        "description": "Fill postal code",
        "url":         None,
        "action":      "type",
        "selector":    "//input[@id='broken-zip']",  # BROKEN
        "value":       "10001",
        "intent":      "postal code zip input field",
        "critical":    False,
    },
    {
        "id":          "continue_checkout",
        "description": "Continue to order summary",
        "url":         None,
        "action":      "click",
        "selector":    "//input[@id='broken-continue']",  # BROKEN
        "value":       None,
        "intent":      "continue button on checkout form",
        "critical":    False,
    },
    {
        "id":          "assert_overview",
        "description": "Assert order overview loaded",
        "url":         None,
        "action":      "assert_url",
        "selector":    None,
        "value":       "/checkout-step-two",
        "intent":      "url verification",
        "critical":    False,
    },
]
