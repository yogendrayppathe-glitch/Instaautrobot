import os
import time
import random
import requests
import telebot
import google.generativeai as genai

# --- Credentials ---
TELEGRAM_TOKEN = "8985439812:AAG8MOcfiB7Lplr_IjcSu0bet42LJk2oJLw"
GEMINI_API_KEY = "AQ.Ab8RN6J3t8huhvllFs2EgfsrMUJ_a0MLKNYEMZJazJZ6mcV9Yw"

# Meta Official API Credentials
ACCESS_TOKEN = "EAATdbGETDAMBS364SZCinyzVc9lPTr4kj3ZBTg9ljo7flqGjhRd9StEWu4FraikuiVpgGLwiUHuhLhAoZBru0FXZAX9TJfwCG9dcccRSSrSYKq0c1gPkBZAwjCL6o0XNTRiD64o1ZBCuX5FUoTZA7oonTKMP4eeRGuKgkcQkJU1xWZBZBtdwxTFh3UEKB36Ngp4LX87rEQFnsagWXlPPFAERhVJ8jqOw3tHmp"
IG_USER_ID = "17841440705100139"

# Los Angeles Facebook Place ID for Meta API
LA_LOCATION_ID = "110970792260960"

# Setup
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

HISTORY_FILE = "processed_links.txt"

def get_processed_links():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return f.read().splitlines()

def save_processed_link(link):
    with open(HISTORY_FILE, "a") as f:
        f.write(link + "\n")

def get_new_link_from_telegram():
    try:
        updates = bot.get_updates(limit=10)
        processed = get_processed_links()
        
        for update in updates:
            if update.message and update.message.text:
                text = update.message.text.strip()
                if "instagram.com/reel/" in text or "instagram.com/p/" in text:
                    if text not in processed:
                        return text, update.message.chat.id
        return None, None
    except Exception as e:
        print("Telegram fetch error:", e)
        return None, None

def enhance_original_caption(orig_caption):
    hashtag_sets = [
        "#LosAngeles #ExplorePage #ViralReels #TrendingUSA #CaliforniaVibes #FYP",
        "#USA #LA #DailyVibes #ReelsInstagram #ViralVideos #AmericanLife #TrendingNow",
        "#Hollywood #WestCoast #InstaGood #ReelItFeelIt #USATrending #ViralContent",
        "#SoCal #NewYork #MiamiVibes #ExploreMore #TrendingReels #USAViral"
    ]
    chosen_tags = random.choice(hashtag_sets)

    clean_orig = orig_caption.split("#")[0].strip() if orig_caption else "Wait for the end!"
    if not clean_orig:
        clean_orig = orig_caption.strip() if orig_caption else "Unbelievable moment!"

    try:
        prompt = (
            f"Here is an Instagram Reel caption: '{orig_caption}'\n"
            f"Rewrite and enhance this exact caption to make it catchy, Gen-Z style for a USA audience. "
            f"Keep the core meaning of the original caption, add 5-6 relevant hashtags based on the video topic plus {chosen_tags}. "
            f"Give ONLY the final caption text, nothing else."
        )
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print("Gemini API skipped, using smart enhanced fallback:", e)

    hooks = ["Wait for it... 👀", "This is crazy! 🔥", "No way this happened 💀", "Vibes on point ✨", "Thoughts on this? 👇"]
    return f"{clean_orig}\n.\n{random.choice(hooks)}\n.\n{chosen_tags}"

def publish_reel_meta_direct(file_path, caption):
    """
    Bina kisi third-party link ke, seedha Meta ke Official Resumable Upload Server 
    (rupload.facebook.com) par local MP4 file bhejta hai!
    """
    # Step 1: Initialize Resumable Upload Container
    init_url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "upload_type": "resumable",
        "caption": caption,
        "location_id": LA_LOCATION_ID,
        "access_token": ACCESS_TOKEN
    }
    res = requests.post(init_url, data=payload).json()

    if "error" in res:
        print("Retrying container without location_id...", res)
        payload.pop("location_id", None)
        res = requests.post(init_url, data=payload).json()

    if "id" not in res or "uri" not in res:
        raise Exception(f"Meta Init Error: {res}")

    creation_id = res["id"]
    upload_uri = res["uri"]
    print(f"Container Initialized! ID: {creation_id}")

    # Step 2: Upload Local Video File Directly to Meta Server
    file_size = os.path.getsize(file_path)
    headers = {
        "Authorization": f"OAuth {ACCESS_TOKEN}",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Type": "application/octet-stream"
    }

    print(f"Uploading {file_size} bytes directly to Meta server...")
    with open(file_path, "rb") as f:
        upload_res = requests.post(upload_uri, headers=headers, data=f, timeout=300).json()

    if not upload_res.get("success"):
        raise Exception(f"Meta Direct File Upload Failed: {upload_res}")

    print("Video binary uploaded! Waiting for Meta to process...")

    # Step 3: Wait for FINISHED status
    status_url = f"https://graph.facebook.com/v20.0/{creation_id}"
    for attempt in range(25):
        time.sleep(10)
        status_res = requests.get(status_url, params={"fields": "status_code,status", "access_token": ACCESS_TOKEN}).json()
        status = status_res.get("status_code")
        print(f"Check {attempt+1}: Video Status = {status}")
        
        if status == "FINISHED":
            break
        elif status == "ERROR":
            raise Exception(f"Meta Video Processing Failed: {status_res}")
    else:
        raise Exception("Timeout waiting for Meta to process video.")

    # Step 4: Publish the Reel
    publish_url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    pub_res = requests.post(publish_url, data={
        "creation_id": creation_id,
        "access_token": ACCESS_TOKEN
    }).json()

    if "id" not in pub_res:
        raise Exception(f"Meta Publish Error: {pub_res}")

    return pub_res["id"]

def process_and_upload():
    link, chat_id = get_new_link_from_telegram()
    
    if not link:
        print("Koi nayi link nahi mili Telegram par. Queue khali hai.")
        return

    video_path = "downloaded_video.mp4"
    desc_file = "downloaded_video.description"
    edited_path = "final_us_video.mp4"

    try:
        if chat_id: bot.send_message(chat_id, f"🚀 Nayi link mil gayi! Process shuru...\nLink: {link}")
        
        # 1. Download Video + Original Caption
        if chat_id: bot.send_message(chat_id, "⬇️ HD Video aur uska Asli Caption download ho raha hai...")
        os.system(f"yt-dlp --write-description -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o '{video_path}' '{link}'")
        
        if not os.path.exists(video_path):
            raise Exception("Download fail ho gaya! Link check karein.")

        orig_caption = ""
        if os.path.exists(desc_file):
            with open(desc_file, "r", encoding="utf-8", errors="ignore") as f:
                orig_caption = f.read().strip()

        # 2. Edit Video (Strict Meta Official Reel Specs: H.264, yuv420p, 30FPS, 9:16, 4.5Mbps, AAC 48kHz)
        if chat_id: bot.send_message(chat_id, "🎨 Video Meta Official specs ke hisaab se edit ho rahi hai...")
        ffmpeg_cmd = (
            f'ffmpeg -i {video_path} -filter_complex '
            f'"[0:v]setpts=0.98*PTS,eq=saturation=1.04,scale=1080:1920:force_original_aspect_ratio=decrease,'
            f'pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v];'
            f'[0:a]atempo=1.02[a]" '
            f'-map "[v]" -map "[a]" -r 30 -c:v libx264 -profile:v high -level:v 4.1 -b:v 4500k -maxrate 5000k -bufsize 10000k '
            f'-c:a aac -b:a 128k -ar 48000 -movflags +faststart {edited_path} -y'
        )
        os.system(ffmpeg_cmd)
        
        if not os.path.exists(edited_path):
            raise Exception("Video editing (FFmpeg) fail ho gayi.")

        # 3. Enhance Original Caption
        if chat_id: bot.send_message(chat_id, "✍️ Video ke original caption ko enhance kiya ja raha hai...")
        final_caption = enhance_original_caption(orig_caption)

        # 4. Direct Upload via Official Meta Resumable API (No third-party host needed!)
        if chat_id: bot.send_message(chat_id, "📤 Seedha Meta Server par video upload ho rahi hai (30 sec lagenge)...")
        media_id = publish_reel_meta_direct(edited_path, final_caption)
        
        # 5. Save & Cleanup
        save_processed_link(link)
        if chat_id: bot.send_message(chat_id, f"✅ SUCCESS! Official API se Reel upload ho gayi!\nPost ID: {media_id}\n\nCaption:\n{final_caption}")
        print("Upload Successful! Media ID:", media_id)

    except Exception as e:
        print(f"Error aa gaya: {e}")
        if chat_id: bot.send_message(chat_id, f"❌ Error: {e}")
    
    finally:
        for f_path in [video_path, desc_file, edited_path]:
            if os.path.exists(f_path):
                os.remove(f_path)

if __name__ == "__main__":
    process_and_upload()
                
