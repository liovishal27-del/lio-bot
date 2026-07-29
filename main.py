import os
import re
import time
import json
import asyncio
import logging
from curl_cffi import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from pyrogram.errors import FloodWait
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
API_ID = 26754022   
API_HASH = "1a0b65e7a4d48e08687c732bdc0f2cc4" 
BOT_TOKEN = "8959460412:AAEivVObxVzHbNnCquAmTpLZeFz1V3wPaIo"
ADMIN_ID = 8302836831
# =======================================================

EXTRACTED_BY = "@LioBankingM✨"
WATERMARK_TEXT = "Lio Banking Pro"  # Clean Render Text
DOWNLOAD_DIR = "./downloads"
TOKEN_FILE = "saved_tokens.json"
COOKIE_FILE = "saved_cookies.json"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

upload_state = {}

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f: return json.load(f)
        except Exception: return {}
    return {}

def save_tokens(tokens_data):
    with open(TOKEN_FILE, "w") as f: json.dump(tokens_data, f, indent=4)

def load_cookies():
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, "r") as f: return json.load(f)
        except Exception: return {}
    return {}

def save_cookies(cookies_data):
    with open(COOKIE_FILE, "w") as f: json.dump(cookies_data, f, indent=4)

app = Client("my_fresh_bot_v19_ebooks", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_progress_string(current, total, start_time, action_text="Processing"):
    now = time.time()
    diff = now - start_time if (now - start_time) > 0 else 0.1
    percentage = current * 100 / total
    speed = current / diff
    completed_blocks = int(percentage / 10)
    progress_bar_str = "■" * completed_blocks + "□" * (10 - completed_blocks)
    speed_str = f"{round(speed / 1024, 2)} KB/s" if speed < 1024 * 1024 else f"{round(speed / (1024 * 1024), 2)} MB/s"
    return f"⚡ **{action_text}**\n├ `[{progress_bar_str}]` **{round(percentage, 2)}%**\n🚀 **Speed:** {speed_str}"

def tg_upload_progress(current, total, message, start_time, file_name):
    if not hasattr(tg_upload_progress, "last_edit_time"): tg_upload_progress.last_edit_time = 0
    if time.time() - tg_upload_progress.last_edit_time > 3.5 or current == total:
        tg_upload_progress.last_edit_time = time.time()
        progress_text = get_progress_string(current, total, start_time, "Uploading to Telegram")
        try: asyncio.run_coroutine_threadsafe(message.edit_text(f"📦 **File:** `{file_name}`\n\n{progress_text}"), asyncio.get_event_loop())
        except: pass

def get_main_keyboard(user_id):
    buttons = [
        [KeyboardButton("🔍 Extract Links"), KeyboardButton("📥 Upload Edited TXT")],
        [KeyboardButton("🔑 Manage JWT Tokens"), KeyboardButton("🍪 Manage Cookies")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply_text(
        "👋 **Welcome to Lio Banking Pro (v19 Ebooks-Node Engine)!**\n\n"
        "⚡ Use buttons below to manage credentials and files.",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

@app.on_message(filters.regex("🔑 Manage JWT Tokens"))
async def manage_tokens_menu(client, message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID: return
    tokens = load_tokens()
    profile_list = "\n".join([f"• `{name}`" for name in tokens.keys()]) if tokens else "No active profiles found."
    buttons = [
        [InlineKeyboardButton("➕ Add Token Profile", callback_data="add_token")],
        [InlineKeyboardButton("❌ Delete Token Profile", callback_data="delete_token_list")]
    ]
    await message.reply_text(f"📋 **Current Saved JWT Profiles:**\n{profile_list}\n\nSelect an action:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.regex("🍪 Manage Cookies"))
async def manage_cookies_menu(client, message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID: return
    cookies = load_cookies()
    cookie_list = "\n".join([f"• `{name}`" for name in cookies.keys()]) if cookies else "No active cookies found."
    buttons = [
        [InlineKeyboardButton("➕ Add Cookie", callback_data="add_cookie")],
        [InlineKeyboardButton("❌ Delete Cookie", callback_data="delete_cookie_list")]
    ]
    await message.reply_text(f"📋 **Current Saved Cookie Profiles:**\n{cookie_list}\n\nSelect an action:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.command("extract") | filters.regex("🔍 Extract Links"))
async def extract_links_request(client, message: Message):
    user_id = message.from_user.id
    tokens = load_tokens()
    if not tokens:
        await message.reply_text("⚠️ Extraction ke liye pehle **🔑 Manage JWT Tokens** button se valid token save karein!")
        return
    upload_state[user_id] = {"action": "waiting_product_link"}
    await message.reply_text("🔗 **Adda247 Package ID ya URL bhejo (e.g. 100632):**")

@app.on_message(filters.command("upload") | filters.regex("📥 Upload Edited TXT"))
async def upload_txt_request(client, message: Message):
    user_id = message.from_user.id
    upload_state[user_id] = {"action": "waiting_txt_file"}
    await message.reply_text("📝 **Apni edited `.txt` file send karo:**")

@app.on_message(filters.document)
async def handle_document_routing(client, message: Message):
    user_id = message.from_user.id
    state = upload_state.get(user_id)
    file_name = message.document.file_name.lower()
    
    if (state and state.get("action") == "waiting_txt_file") or file_name.endswith(".txt"):
        processing = await message.reply_text("⏳ Downloading TXT file...")
        txt_path = await message.download()
        await processing.delete()
        
        tokens = load_tokens()
        if not tokens:
            await message.reply_text("⚠️ Koi Active Token saved nahi hai.")
            if os.path.exists(txt_path): os.remove(txt_path)
            return

        upload_state[user_id] = {"txt_path": txt_path, "waiting_token_selection": True}
        token_buttons = [[InlineKeyboardButton(f"👤 {name}", callback_data=f"sel_tk:{name}")] for name in tokens.keys()]
        await message.reply_text("📝 **TXT File Received!**\nSelect Account Token Profile:", reply_markup=InlineKeyboardMarkup(token_buttons))

@app.on_message(filters.text & ~filters.command([]))
async def text_input_processor(client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    state = upload_state.get(user_id)

    if not state: return

    if state.get("action") == "waiting_product_link":
        upload_state.pop(user_id, None)
        product_id_match = re.search(r'(?:productId=|product-ebooks/|products/|product/|packageId=)(\d+)', text)
        product_id = product_id_match.group(1) if product_id_match else text
        
        if not product_id.isdigit():
            await message.reply_text("❌ Sahi Ebook ID ya package URL bhejein bhai!")
            return
            
        status = await message.reply_text(f"⚡ **Target Package ID Mapped:** `{product_id}`\nExtracting via New Ebooks Sub-domain Node...")
        
        tokens = load_tokens()
        if not tokens:
            await status.edit_text("❌ Koi token saved nahi mila.")
            return
            
        first_profile = list(tokens.values())[0]
        jwt_token = first_profile.get("jwt")
        login_token = first_profile.get("login")
        
        endpoints = [
            f"https://store.adda247.com/api/v3/content?packageId={product_id}&contentType=EBOOKS&pageNo=1&limit=1000",
            f"https://ebooks.adda247.com/api/v3/content?packageId={product_id}&contentType=EBOOKS&pageNo=1&limit=1000"
        ]
        
        api_headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "cp-origin": "11",
            "login_token": login_token,
            "x-jwt-token": jwt_token
        }
        
        cookies = load_cookies()
        if cookies:
            api_headers["cookie"] = list(cookies.values())[0]

        raw_response_text = ""
        session = requests.Session()
        
        for url in endpoints:
            try:
                response = session.get(url, headers=api_headers, impersonate="chrome120", timeout=20)
                if response.status_code == 200 and len(response.text) > 100:
                    raw_response_text = response.text
                    break
            except Exception: pass

        if not raw_response_text:
            await status.edit_text("❌ Server authentication error. Check Token Profiles or Cookies.")
            return
                
        extracted_items = []
        try:
            data = json.loads(raw_response_text)
            def extract_v3_recursive(node, current_folder="Ebook"):
                if not node: return
                if isinstance(node, list):
                    for sub_node in node: extract_v3_recursive(sub_node, current_folder)
                    return
                if isinstance(node, dict):
                    folder_title = node.get("name") or node.get("title") or node.get("chapterName") or current_folder
                    file_url = node.get("fileUrl") or node.get("downloadUrl") or node.get("url")
                    
                    if file_url and any(x in str(file_url).lower() for x in [".pdf", "pdf", "document"]):
                        extracted_items.append((current_folder, folder_title, file_url))
                        return
                    
                    for key in node.keys():
                        if isinstance(node[key], (dict, list)) and key not in ["headers", "config"]:
                            extract_v3_recursive(node[key], current_folder=folder_title)

            extract_v3_recursive(data)
        except Exception: pass

        if not extracted_items:
            await status.edit_text("⚠️ Content empty or structured block mismatch.")
            return
                
        txt_filename = f"Extracted_{product_id}.txt"
        txt_filepath = os.path.join(DOWNLOAD_DIR, txt_filename)
        with open(txt_filepath, "w", encoding="utf-8") as f:
            for folder, title, url_path in extracted_items:
                f.write(f"[{folder}] {title}.pdf: {url_path}\n")
        
        await status.delete()
        await message.reply_document(document=txt_filepath, caption=f"📝 **Extraction Complete!**\n📊 Total Files Mapped: `{len(extracted_items)}`")
        os.remove(txt_filepath)
        return

    if state.get("action") == "waiting_token_name" and user_id == ADMIN_ID:
        upload_state[user_id]["temp_name"] = text
        upload_state[user_id]["action"] = "waiting_jwt_value"
        await message.reply_text("Ab `x-jwt-token` ki value paste karo:")
        return
    elif state.get("action") == "waiting_jwt_value" and user_id == ADMIN_ID:
        upload_state[user_id]["temp_jwt"] = text
        upload_state[user_id]["action"] = "waiting_login_token"
        await message.reply_text("Ab `login_token` ki value paste karo:")
        return
    elif state.get("action") == "waiting_login_token" and user_id == ADMIN_ID:
        tokens = load_tokens()
        tokens[state["temp_name"]] = {"jwt": state["temp_jwt"], "login": text}
        save_tokens(tokens)
        upload_state.pop(user_id, None)
        await message.reply_text("✅ Token profile saved!", reply_markup=get_main_keyboard(user_id))
        return

    if state.get("action") == "waiting_cookie_name" and user_id == ADMIN_ID:
        upload_state[user_id]["temp_cookie_name"] = text
        upload_state[user_id]["action"] = "waiting_cookie_value"
        await message.reply_text("Ab poori Cookie string ya JSON object paste karo:")
        return
    elif state.get("action") == "waiting_cookie_value" and user_id == ADMIN_ID:
        cookies = load_cookies()
        cookies[state["temp_cookie_name"]] = text
        save_cookies(cookies)
        upload_state.pop(user_id, None)
        await message.reply_text("✅ Cookie profile saved successfully!", reply_markup=get_main_keyboard(user_id))
        return

@app.on_callback_query()
async def query_callback_bridge(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data == "add_token" and user_id == ADMIN_ID:
        await callback_query.answer()
        upload_state[user_id] = {"action": "waiting_token_name"}
        await callback_query.message.reply_text("Profile Name:")
    elif data == "delete_token_list" and user_id == ADMIN_ID:
        await callback_query.answer()
        tokens = load_tokens()
        buttons = [[InlineKeyboardButton(f"❌ {n}", callback_data=f"del_tk:{n}")] for n in tokens.keys()]
        await callback_query.message.edit_text("Delete profile?", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("del_tk:") and user_id == ADMIN_ID:
        await callback_query.answer()
        name = data.split(":")[1]
        tokens = load_tokens()
        if name in tokens: del tokens[name]; save_tokens(tokens)
        await callback_query.message.edit_text(f"🗑️ Deleted Token `{name}`.")
        
    elif data == "add_cookie" and user_id == ADMIN_ID:
        await callback_query.answer()
        upload_state[user_id] = {"action": "waiting_cookie_name"}
        await callback_query.message.reply_text("Cookie Profile Name (e.g., Account_1):")
    elif data == "delete_cookie_list" and user_id == ADMIN_ID:
        await callback_query.answer()
        cookies = load_cookies()
        buttons = [[InlineKeyboardButton(f"❌ {n}", callback_data=f"del_ck:{n}")] for n in cookies.keys()]
        await callback_query.message.edit_text("Select Cookie to delete:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("del_ck:") and user_id == ADMIN_ID:
        await callback_query.answer()
        name = data.split(":")[1]
        cookies = load_cookies()
        if name in cookies: del cookies[name]; save_cookies(cookies)
        await callback_query.message.edit_text(f"🗑️ Deleted Cookie `{name}`.")
        
    elif data.startswith("sel_tk:"):
        await callback_query.answer()
        token_name = data.split(":")[1]
        state = upload_state.get(user_id)
        if not state or not state.get("waiting_token_selection"): return
        
        token_profile = load_tokens().get(token_name)
        await callback_query.message.edit_text(f"⚙️ Using JWT Profile: `{token_name}`\nDownloading...")
        asyncio.create_task(start_pdf_processing(client, callback_query.message, state["txt_path"], token_profile, user_id))

async def start_pdf_processing(client, status_message, txt_path, token_profile, user_id):
    processing = status_message
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    api_headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cp-origin": "11",
        "login_token": token_profile.get("login"),
        "x-jwt-token": token_profile.get("jwt")
    }

    cookies = load_cookies()
    if cookies:
        api_headers["cookie"] = list(cookies.values())[0]

    session = requests.Session()
    for index, line in enumerate(lines, start=1):
        file_path = None
        thumb_path = None  
        try:
            parts = line.split(".pdf:")
            if len(parts) != 2: parts = line.split(":")
            if len(parts) != 2: continue
            
            left, link = parts[0].strip(), parts[1].strip()
            folder_match = re.search(r"\[(.*?)\]", left)
            folder_name = folder_match.group(1) if folder_match else "Unknown"
            
            pdf_name = re.sub(r"\[.*?\]\s*", "", left).strip()
            if not pdf_name.lower().endswith(".pdf"): pdf_name += ".pdf"
            clean_pdf_name = clean_filename(pdf_name)
            file_path = os.path.join(DOWNLOAD_DIR, clean_pdf_name)
            
            await processing.edit_text(f"⏳ **📥 Fetching:** `{clean_pdf_name}`\nFile {index} of {len(lines)}")
            
            response = session.get(link, headers=api_headers, impersonate="chrome120", stream=True, timeout=45)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                start_download_time = time.time()
                last_ui_update = 0
                
                with open(file_path, "wb") as f_out:
                    for chunk in response.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f_out.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0 and (time.time() - last_ui_update > 3.5 or downloaded_size == total_size):
                                last_ui_update = time.time()
                                progress_text = get_progress_string(downloaded_size, total_size, start_download_time, "Downloading")
                                try: await processing.edit_text(f"📦 **File [{index}/{len(lines)}]:** `{clean_pdf_name}`\n\n{progress_text}")
                                except: pass

            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                # 🔥 GRAPHICS SHAPE LAYER OVERLAY ENGINE 🔥
                try:
                    logger.info(f"Mac Engine: Processing {clean_pdf_name}...")
                    doc = fitz.open(file_path)
                    
                    # 1. First, extract clean thumbnail image
                    if len(doc) > 0:
                        page = doc.load_page(0)
                        pix = page.get_pixmap(dpi=100)
                        thumb_name = f"thumb_{clean_pdf_name.replace('.pdf', '')}.jpg"
                        thumb_path = os.path.join(DOWNLOAD_DIR, thumb_name)
                        pix.save(thumb_path)
                    
                    # 2. Shape Layer Draw Engine (Forces overlay on top of all image/text layers)
                    for page in doc:
                        rect = page.rect
                        shape = page.new_shape()
                        
                        font = fitz.Font("helv")
                        text_text = WATERMARK_TEXT
                        font_size = 38
                        
                        # Set diagonal center mapping
                        point = fitz.Point(rect.width / 5, rect.height / 2)
                        matrix = fitz.Matrix(45)  # Perfect 45-degree angle
                        
                        shape.insert_text(
                            point, 
                            text_text, 
                            fontsize=font_size, 
                            fontobj=font, 
                            color=(0.75, 0.75, 0.75), 
                            fill_opacity=0.32,        
                            morph=(point, matrix)      
                        )
                        # overlay=True ensures text stays on top of everything
                        shape.commit(overlay=True) 
                    
                    # 3. Clean close and save chain
                    temp_watermarked_path = file_path + ".temp"
                    doc.save(temp_watermarked_path, incremental=False, encryption=0)
                    doc.close()
                    
                    if os.path.exists(temp_watermarked_path):
                        os.remove(file_path)
                        os.rename(temp_watermarked_path, file_path)
                        logger.info("Watermark layout drawn and finalized successfully.")
                        
                except Exception as process_err:
                    logger.error(f"Shape engine processing issue: {process_err}")
                    if 'doc' in locals() and not doc.is_closed:
                        doc.close()

                caption = f"📝 Title: {clean_pdf_name.replace('.pdf', '')}\n📁 Folder: {folder_name}\n📥 Extracted by: {EXTRACTED_BY}"
                start_upload_time = time.time()
                
                if thumb_path and not os.path.exists(thumb_path):
                    thumb_path = None

                while True:
                    try:
                        await processing.reply_document(
                            document=file_path, 
                            caption=caption,
                            thumb=thumb_path,  
                            progress=tg_upload_progress,
                            progress_args=(processing, start_upload_time, clean_pdf_name)
                        )
                        break
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                        start_upload_time = time.time()
            else: 
                logger.error(f"Download fail for: {clean_pdf_name}")
        except Exception as e: 
            logger.error(f"Error: {e}")
        finally:
            if file_path and os.path.exists(file_path): 
                os.remove(file_path)
            if thumb_path and os.path.exists(thumb_path): 
                os.remove(thumb_path)
            await asyncio.sleep(1.5)

    try: 
        await processing.delete()
    except: 
        pass
        
    await app.send_message(user_id, "✅ Batch upload complete!", reply_markup=get_main_keyboard(user_id))
    if os.path.exists(txt_path): 
        os.remove(txt_path)
    upload_state.pop(user_id, None)

if __name__ == "__main__":
    print("🤖 Bot v19 with Ebooks Node running smoothly.")
    app.run()
