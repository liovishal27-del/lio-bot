from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(storage_state="storage_state.json")
    page = context.new_page()

    def log_response(response):
        url = response.url
        if "ebooks.adda247.com" in url:
            print("\n", "=" * 80)
            print(response.request.method, url)

    page.on("response", log_response)

    page.goto(
        "https://www.adda247.com/product-ebooks/100632/reasoning-rank-file-ebook?productId=100633",
        wait_until="networkidle"
    )

    print("\nBrowser open hai.")
    print("Ab kisi bhi ebook par click karo.")
    input("\nClick karne ke baad yahan ENTER dabao...")

    browser.close()