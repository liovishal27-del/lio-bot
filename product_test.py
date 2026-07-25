from playwright.sync_api import sync_playwright

PRODUCT_URL = "https://www.adda247.com/product-ebooks/100632/reasoning-rank-file-ebook?productId=100633"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(storage_state="storage_state.json")

    page = context.new_page()

    page.goto(PRODUCT_URL, wait_until="networkidle")

    print("\nPage Loaded Successfully")
    print("Title:", page.title())
    print("Current URL:", page.url)

    input("\nProduct open ho gaya? Agar haan to ENTER dabao...")

    browser.close()