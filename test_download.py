import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()

driver = webdriver.Chrome(options=options)

# Yahan Adda247 pe manually login kar lena agar login nahi hai
driver.get("https://www.adda247.com")

input("Login ho jaye to ENTER dabao...")

session = requests.Session()

# Browser ki cookies requests me copy karo
for c in driver.get_cookies():
    session.cookies.set(c["name"], c["value"])

url = "https://www.adda247.com/100632_29897.doc"

r = session.get(url)

print("Status:", r.status_code)
print("Content-Type:", r.headers.get("Content-Type"))
print("Length:", len(r.content))

with open("test.doc", "wb") as f:
    f.write(r.content)

print("Saved as test.doc")

driver.quit()