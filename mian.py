# Requirements check
# Ensure the following packages are installed:
# pip install pyrogram tgcrypto requests

import uuid
import re
import time
import requests
import os
import tempfile
from urllib.parse import urlparse, urlunparse
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, PeerIdInvalid

# === Bot Credentials ===
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# === RapidAPI Credentials ===
RAPIDAPI_KEY = "b4b76986admsh4ace8959ebfd8bep1109a9jsn7acb2a172e39"
RAPIDAPI_HOST = "social-media-video-downloader.p.rapidapi.com"

# === Memory Storage ===
video_cache = {}  # short_id: (platform, url)
user_set = set()  # track users for broadcasting

# === Admins ===
ADMINS = [123456789]  # Replace with your Telegram user ID

# === Init Bot ===
app = Client("media_downloader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# === Utilities ===
def clean_url(raw_url):
    parts = urlparse(raw_url)
    return urlunparse(parts._replace(query=""))

def download_social_video(url):
    endpoint = "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "social-download-all-in-one.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    payload = {"url": clean_url(url)}
    response = requests.post(endpoint, json=payload, headers=headers)
    print("API RESPONSE:", response.status_code, response.text)
    return response.json()

def is_valid_url(text):
    return re.match(r"https?://", text)

def extract_video_link(result):
    # TikTok and some APIs: medias array
    if result.get("medias"):
        for media in result["medias"]:
            if (
                media.get("type", "").lower() == "video"
                and media.get("extension", "").lower() == "mp4"
                and isinstance(media.get("url"), str)
            ):
                return media["url"]
    # Try common keys for direct video
    for key in ["video", "videoUrl", "url", "play", "playUrl", "play_url"]:
        val = result.get(key)
        if isinstance(val, str) and (".mp4" in val or "/video" in val):
            return val
    # Try inside 'links' array
    if result.get("links"):
        for link in result["links"]:
            if link.get("type", "").lower() == "video" and (".mp4" in link.get("link", "") or "/video" in link.get("link", "")):
                return link["link"]
            if ".mp4" in link.get("link", ""):
                return link["link"]
    # Try inside 'result' subkey
    if result.get("result"):
        return extract_video_link(result["result"])
    # Fallback: recursively search for any .mp4 or /video string in the response
    def recursive_search(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                found = recursive_search(v)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = recursive_search(item)
                if found:
                    return found
        elif isinstance(obj, str):
            if ".mp4" in obj or "/video" in obj:
                return obj
        return None
    return recursive_search(result)

# === Message Handlers ===
@app.on_message(filters.command("start") & filters.private)
def start_cmd(client, message):
    message.reply(
        '''
👋 Welcome! Send me a TikTok, Instagram, or Facebook video link to download.

👋 مرحبًا! أرسل لي رابط فيديو من تيك توك أو إنستغرام أو فيسبوك لتحميله.

'
🔹 Supported features:
- Download video in multiple qualities (HD/SD, with or without watermark)
- Download audio only (MP3)
- Works for TikTok, Instagram, Facebook, and more
- Fast, simple, and free

'
🔹 ميزات البوت:
- تحميل الفيديو بجودات مختلفة (HD/SD، مع أو بدون علامة مائية)
- تحميل الصوت فقط (MP3)
- يدعم تيك توك، إنستغرام، فيسبوك والمزيد
- سريع وسهل ومجاني

🤖 Bot by: @M7MED1573'''
    )

@app.on_message(filters.command("broadcast") & filters.private)
def broadcast(client, message):
    if message.from_user.id not in ADMINS:
        return message.reply("❌ You are not authorized.")

    if len(message.command) < 2:
        return message.reply("❗ Usage: /broadcast your message")

    text = message.text.split(" ", 1)[1]
    sent, failed = 0, 0

    for user_id in list(user_set):
        try:
            client.send_message(user_id, text)
            sent += 1
            time.sleep(0.5)
        except FloodWait as e:
            time.sleep(e.value)
        except (UserIsBlocked, PeerIdInvalid):
            user_set.discard(user_id)
            failed += 1
        except:
            failed += 1

    message.reply(f"📢 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}")

@app.on_message(filters.private & filters.text)
def detect_and_download(client, message):
    user_set.add(message.from_user.id)

    url = message.text.strip()
    if not is_valid_url(url):
        return message.reply("❌ Please send a valid TikTok, Instagram, or Facebook video link.")

    msg = message.reply("⏳ Getting formats...")

    try:
        result = download_social_video(url)
        print('DEBUG API RESULT:', result)  # Debug print
        # Collect available formats and arrange them
        video_buttons = []
        audio_buttons = []
        if result.get("medias"):
            for media in result["medias"]:
                if media.get("type") == "video":
                    label = "🎬 فيديو"
                    quality = media.get("quality", "").lower()
                    if "hd" in quality:
                        label += " HD"
                    elif "sd" in quality:
                        label += " SD"
                    if "no_watermark" in quality:
                        label += " (بدون علامة مائية)"
                    elif "watermark" in quality:
                        label += " (بعلامة مائية)"
                    video_buttons.append((label, media["url"], "video"))
                elif media.get("type") == "audio":
                    label = "🎵 صوت فقط (MP3)"
                    audio_buttons.append((label, media["url"], "audio"))
        # fallback: just use extracted video
        if not video_buttons and not audio_buttons:
            video_link = extract_video_link(result)
            if video_link:
                video_buttons.append(("🎬 فيديو (تلقائي)", video_link, "video"))
        if not video_buttons and not audio_buttons:
            return msg.edit_text("❌ لا توجد صيغ متاحة للتحميل.")
        # Build inline buttons for formats
        short_id = str(uuid.uuid4())[:8]
        # Store type info for each format
        video_cache[short_id] = (url, result, video_buttons + audio_buttons)
        buttons = []
        # Arrange video buttons in rows of 2
        for i in range(0, len(video_buttons), 2):
            row = [InlineKeyboardButton(video_buttons[j][0], callback_data=f"fmt|{short_id}|{j}") for j in range(i, min(i+2, len(video_buttons)))]
            buttons.append(row)
        # Audio button(s) in a separate row
        for idx, (label, _, _) in enumerate(audio_buttons, start=len(video_buttons)):
            buttons.append([InlineKeyboardButton(label, callback_data=f"fmt|{short_id}|{idx}")])
        msg.edit_text(
            "اختر الصيغة أو الجودة التي تريدها:\nSelect the format/quality you want:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        msg.edit_text(f"❌ Error: {e}")

@app.on_callback_query()
def handle_callback(client, callback_query):
    data = callback_query.data
    if data.startswith("fmt|"):
        _, short_id, idx = data.split("|")
        # Find formats again
        if short_id not in video_cache:
            return callback_query.answer("⚠️ Session expired", show_alert=True)
        url, result, formats = video_cache[short_id]
        idx = int(idx)
        if idx >= len(formats):
            return callback_query.answer("❌ Format not found.", show_alert=True)
        label, media_url, media_type = formats[idx]
        callback_query.answer(f"جاري التحميل: {label}")
        # Download and send
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4' if media_type == 'video' else '.mp3') as tmp_file:
            tmp_path = tmp_file.name
            with requests.get(media_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
        try:
            if media_type == 'audio':
                client.send_audio(callback_query.message.chat.id, audio=tmp_path, caption=label)
            else:
                client.send_video(callback_query.message.chat.id, video=tmp_path, caption=label)
        finally:
            os.remove(tmp_path)
    # ...existing code for dl| ...
    elif data.startswith("dl|"):
        short_id = data.split("|")[1]
        if short_id not in video_cache:
            return callback_query.answer("⚠️ Session expired", show_alert=True)

        url = video_cache[short_id][0]
        callback_query.answer("🔁 Downloading...")

        try:
            result = download_social_video(url)
            video_link = extract_video_link(result)
            print('DEBUG VIDEO LINK TO SEND:', video_link)  # Debug print
            title = result.get("title") or "🎬 Video"

            new_id = str(uuid.uuid4())[:8]
            video_cache[new_id] = (url,)

            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Download Again", callback_data=f"dl|{new_id}")],
                [InlineKeyboardButton("📤 Share", url=url)]
            ])

            if not video_link:
                return callback_query.message.reply("❌ Could not find a downloadable video link.")

            # Download video to temp file, then send
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_path = tmp_file.name
                with requests.get(video_link, stream=True) as r:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
            try:
                client.send_video(callback_query.message.chat.id, video=tmp_path, caption=title, reply_markup=buttons)
            finally:
                os.remove(tmp_path)

        except Exception as e:
            callback_query.message.reply(f"❌ Error: {e}")
    else:
        return callback_query.answer("❌ Invalid action")

# === Start Bot ===
app.run()
