from playwright.sync_api import sync_playwright

URL = "https://www.adda247.com/product-ebooks/100632/reasoning-rank-file-ebook?productId=100633"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(storage_state="storage_state.json")

    page = context.new_page()

    def log_request(req):
        if "ebooks.adda247.com" in req.url:
            print("\nREQUEST")
            print(req.method)
            print(req.url)

    def log_response(res):
        if "ebooks.adda247.com" in res.url:
            print("\nRESPONSE")
            print(res.status)
            print(res.url)

    page.on("request", log_request)
    page.on("response", log_response)

    page.goto(URL)

    print("\nPage open ho gaya.")
    print("Ab browser me:")
    print("1. Topic Wise (English) kholo")
    print("2. Kisi ebook par click karo")
    print("3. Agar naya page khule to khulne do")
    print("4. Jab sab ho jaye tab terminal me ENTER dabao")

    input()

    browser.close()