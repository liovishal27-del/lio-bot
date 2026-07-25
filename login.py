from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context()

    page = context.new_page()

    print("Opening Adda247 Login Page...")

    page.goto("https://www.adda247.com/login")

    input("\nLogin complete hone ke baad yaha terminal me ENTER dabao...")

    context.storage_state(path="storage_state.json")

    print("✅ Login Saved Successfully!")

    browser.close()