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

def upload_to_public_host(file_path):
    """3 Multi-host fallback system taaki public link kabhi fail na ho"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # Host 1: Litterbox (1 hour temporary direct .mp4 link)
    try:
        print("Trying Host 1: Litterbox...")
        with open(file_path, "rb") as f:
            res = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": f},
                headers=headers,
                timeout=120
            )
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception as e:
        print("Litterbox failed:", e)

    # Host 2: tmpfiles.org (Fast & reliable for GitHub Actions)
    try:
        print("Trying Host 2: tmpfiles.org...")
        with open(file_path, "rb") as f:
            res = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                headers=headers,
                timeout=120
            )
        if res.status_code == 200:
            data = res.json()
            raw_url = data.get("data", {}).get("url", "")
            if raw_url:
                # Convert to direct download link by inserting /dl/
                direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/").replace("http://", "https://")
                return direct_url
    except Exception as e:
        print("tmpfiles failed:", e)

    # Host 3: 0x0.st
    try:
        print("Trying Host 3: 0x0.st...")
        with open(file_path, "rb") as f:
            res = requests.post(
                "https://0x0.st",
                files={"file": f},
                headers={"User-Agent": "curl/8.0.1"},
                timeout=120
            )
        if res.status_code == 200 and res.text.strip().startswith("https://"):
            return res.text.strip()
    except Exception as e:
        print("0x0.st failed:", e)

    raise Exception("Saare public file hosts fail ho gaye!")

def publish_reel_meta_api(video_url, caption):
    """Official Meta Graph API se Reel container banata hai aur publish karta hai"""
    container_url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "location_id": LA_LOCATION_ID,
        "access_token": ACCESS_TOKEN
    }
    res = requests.post(container_url, data=payload).json()
    
    if "error" in res:
        print("Retrying container without location_id...", res)
        payload.pop("location_id", None)
        res = requests.post(container_url, data=payload).json()

    if "id" not in res:
        raise Exception(f"Meta Container Error: {res}")

    creation_id = res["id"]
    print(f"Container Created! ID: {creation_id}. Waiting for Meta to process video...")

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

        # 2. Edit Video (FFmpeg Anti-copyright 1080p 60FPS)
        if chat_id: bot.send_message(chat_id, "🎨 Video edit ho rahi hai (1080p 60FPS)...")
        os.system(f'ffmpeg -i {video_path} -filter_complex "[0:v]setpts=0.97*PTS,eq=saturation=1.05[v];[0:a]atempo=1.03[a]" -map "[v]" -map "[a]" -r 60 -c:v libx264 -b:v 8000k -c:a aac {edited_path} -y')
        
        if not os.path.exists(edited_path):
            raise Exception("Video editing (FFmpeg) fail ho gayi.")

        # 3. Enhance Original Caption
        if chat_id: bot.send_message(chat_id, "✍️ Video ke original caption ko enhance kiya ja raha hai...")
        final_caption = enhance_original_caption(orig_caption)
        
        # 4. Generate Public Link for Meta API
        if chat_id: bot.send_message(chat_id, "🔗 Video ka temporary public link ban raha hai...")
        public_video_url = upload_to_public_host(edited_path)
        print("Public Video URL:", public_video_url)

        # 5. Upload via Official Meta Graph API
        if chat_id: bot.send_message(chat_id, "📤 Official Meta API se Instagram par upload ho raha hai (30 sec lagenge)...")
        media_id = publish_reel_meta_api(public_video_url, final_caption)
        
        # 6. Save & Cleanup
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

