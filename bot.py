import os
import telebot
from instagrapi import Client
import google.generativeai as genai

# --- Tere asli aur fixed credentials ---
TELEGRAM_TOKEN = "8985439812:AAG8MOcfiB7Lplr_IjcSu0bet42LJk2oJLw"
INSTA_USERNAME = "fan_p_age123"
INSTA_PASSWORD = "yp@365637"
GEMINI_API_KEY = "AQ.Ab8RN6J3t8huhvllFs2EgfsrMUJ_a0MLKNYEMZJazJZ6mcV9Yw"

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
                text = update.message.text
                if "instagram.com/reel/" in text or "instagram.com/p/" in text:
                    if text not in processed:
                        return text, update.message.chat.id
        return None, None
    except Exception as e:
        print("Telegram fetch error:", e)
        return None, None

def generate_us_caption():
    try:
        prompt = "Write a viral, Gen-Z style Instagram Reel caption targeted for a USA audience. Include popular US hashtags like #LosAngeles #TrendingUSA. No emojis at the start, keep it clean and catchy."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("AI Caption Error:", e)
        return "Viral moments everyday! 🔥 #LosAngeles #USA #Trending"

def process_and_upload():
    link, chat_id = get_new_link_from_telegram()
    
    if not link:
        print("Koi nayi link nahi mili Telegram par. Queue khali hai.")
        return

    try:
        if chat_id: bot.send_message(chat_id, f"🚀 Nayi link mil gayi! Process shuru kar raha hu...\nLink: {link}")
        
        # 1. Download Video
        video_path = "downloaded_video.mp4"
        if chat_id: bot.send_message(chat_id, "⬇️ HD Video download ho rahi hai...")
        os.system(f"yt-dlp -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o {video_path} {link}")
        
        if not os.path.exists(video_path):
            raise Exception("Download fail ho gaya! Link check karein.")

        # 2. Edit Video 
        edited_path = "final_us_video.mp4"
        if chat_id: bot.send_message(chat_id, "🎨 Video edit ho rahi hai (1080p 60FPS, Anti-copyright)...")
        os.system(f'ffmpeg -i {video_path} -filter_complex "[0:v]setpts=0.97*PTS,eq=saturation=1.05[v];[0:a]atempo=1.03[a]" -map "[v]" -map "[a]" -r 60 -c:v libx264 -b:v 8000k -c:a aac {edited_path} -y')
        
        if not os.path.exists(edited_path):
            raise Exception("Video editing (FFmpeg) fail ho gayi.")

        # 3. AI Caption
        if chat_id: bot.send_message(chat_id, "🤖 AI se US Gen-Z caption likhwa raha hu...")
        caption = generate_us_caption()
        
        # 4. Upload to Instagram (Clean Session)
        if chat_id: bot.send_message(chat_id, "📤 Instagram par Los Angeles location ke sath upload kar raha hu...")
        
        cl = Client()
        
        if os.path.exists("session.json"):
            cl.load_settings("session.json", override_app_version=True)
            
        cl.login(INSTA_USERNAME, INSTA_PASSWORD)
        cl.dump_settings("session.json")
        
        # Upload
                loc = cl.location_search(34.0522, -118.2437)[0]
        (edited_path, caption, location=loc)
        
        # 5. Cleanup
        save_processed_link(link)
        os.remove(video_path)
        os.remove(edited_path)
        
        if chat_id: bot.send_message(chat_id, "✅ SUCCESS! Reel upload ho chuki hai!")
        print("Upload Successful!")

    except Exception as e:
        print(f"Error aa gaya: {e}")
        if chat_id: bot.send_message(chat_id, f"❌ Error: {e}")

if __name__ == "__main__":
    process_and_upload()
