# pip install pyrogram tgcrypto requests yt-dlp

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
from yt_dlp import YoutubeDL

# === Bot Credentials ===
API_ID = 28129546
API_HASH = "f0985e4f023d1406fe8ee76717651e85"
BOT_TOKEN = "7796238248:AAFqSY_MfrY5k4miqjFdYxF7D1DXHM98bOc"

# === RapidAPI Credentials ===
RAPIDAPI_KEY = "b4b76986admsh4ace8959ebfd8bep1109a9jsn7acb2a172e39"
RAPIDAPI_HOST = "social-media-video-downloader.p.rapidapi.com"

video_cache = {}
user_set = set()
ADMINS = [123456789]  # Replace with your Telegram user ID

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
    return response.json()

def is_valid_url(text):
    return re.match(r"https?://", text)

def is_youtube_url(url):
    return re.search(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/", url) is not None

def extract_video_link(result):
    if result.get("medias"):
        for media in result["medias"]:
            if media.get("type", "").lower() == "video" and isinstance(media.get("url"), str):
                return media["url"]
    for key in ["video", "videoUrl", "url", "play", "playUrl", "play_url"]:
        val = result.get(key)
        if isinstance(val, str) and (".mp4" in val or "/video" in val):
            return val
    if result.get("links"):
        for link in result["links"]:
            if ".mp4" in link.get("link", ""):
                return link["link"]
    if result.get("result"):
        return extract_video_link(result["result"])
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

def download_youtube_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'merge_output_format': 'mp4'
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        return file_path, info.get("title", "YouTube Video")

# === Commands ===
@app.on_message(filters.command("start") & filters.private)
def start_cmd(client, message):
    message.reply(
        '''
👋 Welcome! Send me a TikTok, Instagram, Facebook, or YouTube video link to download.

'
🔹 Supported platforms:
- TikTok, Instagram, Facebook, YouTube
- Download with/without watermark
- MP4 & MP3 support
- Multiple quality formats

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

# === Main Handler ===
@app.on_message(filters.private & filters.text)
def detect_and_download(client, message):
    user_set.add(message.from_user.id)
    url = message.text.strip()

    if not is_valid_url(url):
        return message.reply("❌ Send a valid video link.")

    msg = message.reply("⏳ Checking platform...")

    if is_youtube_url(url):
        msg.edit_text("⏳ Downloading YouTube video...")
        try:
            file_path, title = download_youtube_video(url)
            client.send_video(message.chat.id, video=file_path, caption=title)
            os.remove(file_path)
        except Exception as e:
            msg.edit_text(f"❌ YouTube download failed:\n{e}")
        return

    try:
        result = download_social_video(url)
        video_buttons, audio_buttons = [], []

        if result.get("medias"):
            for media in result["medias"]:
                if media.get("type") == "video":
                    label = "🎬 Video"
                    q = media.get("quality", "").lower()
                    if "hd" in q: label += " HD"
                    if "sd" in q: label += " SD"
                    if "no_watermark" in q: label += " (No Watermark)"
                    video_buttons.append((label, media["url"], "video"))
                elif media.get("type") == "audio":
                    audio_buttons.append(("🎵 Audio (MP3)", media["url"], "audio"))

        if not video_buttons and not audio_buttons:
            fallback = extract_video_link(result)
            if fallback:
                video_buttons.append(("🎬 Video (Auto)", fallback, "video"))

        if not video_buttons and not audio_buttons:
            return msg.edit_text("❌ No downloadable formats found.")

        short_id = str(uuid.uuid4())[:8]
        video_cache[short_id] = (url, result, video_buttons + audio_buttons)

        buttons = []
        for i in range(0, len(video_buttons), 2):
            row = [InlineKeyboardButton(video_buttons[j][0], callback_data=f"fmt|{short_id}|{j}") for j in range(i, min(i + 2, len(video_buttons)))]
            buttons.append(row)
        for idx, (label, _, _) in enumerate(audio_buttons, start=len(video_buttons)):
            buttons.append([InlineKeyboardButton(label, callback_data=f"fmt|{short_id}|{idx}")])

        msg.edit_text("🎥 Choose format/quality:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        msg.edit_text(f"❌ Error: {e}")

# === Callback Handler ===
@app.on_callback_query()
def handle_callback(client, cb):
    data = cb.data
    if data.startswith("fmt|"):
        _, short_id, idx = data.split("|")
        if short_id not in video_cache:
            return cb.answer("⚠️ Session expired", show_alert=True)
        url, result, formats = video_cache[short_id]
        idx = int(idx)
        if idx >= len(formats):
            return cb.answer("❌ Format not found.", show_alert=True)
        label, media_url, media_type = formats[idx]
        cb.answer(f"📥 Downloading: {label}")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4' if media_type == 'video' else '.mp3') as tmp_file:
            tmp_path = tmp_file.name
            with requests.get(media_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
        try:
            if media_type == 'audio':
                client.send_audio(cb.message.chat.id, audio=tmp_path, caption=label)
            else:
                client.send_video(cb.message.chat.id, video=tmp_path, caption=label)
        finally:
            os.remove(tmp_path)
    else:
        cb.answer("❌ Unknown action")

# === Run Bot ===
app.run()
