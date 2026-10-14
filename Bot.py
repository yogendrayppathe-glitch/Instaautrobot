import os
import telebot
from instagrapi import Client
import google.generativeai as genai

# --- API KEYS (Yahan apne asli details daalein) ---
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN" # Jaise pehle tha 89854...
INSTA_USERNAME = "fan_p_age123"
INSTA_PASSWORD = "YOUR_INSTA_PASSWORD" 
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

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

def get_new_link():
    try:
        # Telegram se pichle 20 messages layega
        updates = bot.get_updates(limit=20)
        processed = get_processed_links()
        
        for update in updates:
            if update.message and update.message.text:
                text = update.message.text
                if "instagram.com" in text:
                    # Agar link ke sath koi aur text bhi ho, toh sirf link nikalega
                    words = text.split()
                    for word in words:
                        if "instagram.com" in word:
                            if word not in processed:
                                return word, update.message.chat.id
        return None, None
    except Exception as e:
        print(f"Telegram fetch error: {e}")
        return None, None

def main():
    link, chat_id = get_new_link()
    
    if not link:
        print("Koi nayi Instagram link nahi mili. Queue khali hai.")
        return

    try:
        if chat_id: bot.send_message(chat_id, f"🚀 Nayi link mil gayi! Process shuru ho raha hai...\nLink: {link}")
        
        # 1. Download Video
        if chat_id: bot.send_message(chat_id, "⬇️ Video download ho rahi hai...")
        os.system(f"yt-dlp -o 'downloaded_video.mp4' {link}")
        
        if not os.path.exists("downloaded_video.mp4"):
            raise Exception("Download fail ho gaya! Link check karein.")

        # 2. Edit Video (1.03x speed, color shift, 60fps 1080p, No Text)
        if chat_id: bot.send_message(chat_id, "🎨 Video edit ho rahi hai (1080p 60FPS, Anti-copyright)...")
        os.system('ffmpeg -i downloaded_video.mp4 -filter_complex "[0:v]setpts=0.97*PTS,eq=saturation=1.05[v];[0:a]atempo=1.03[a]" -map "[v]" -map "[a]" -r 60 -c:v libx264 -b:v 8000k -c:a aac final_us_video.mp4 -y')
        
        if not os.path.exists("final_us_video.mp4"):
            raise Exception("Video editing (FFmpeg) fail ho gayi.")

        # 3. AI Caption USA Targeted
        if chat_id: bot.send_message(chat_id, "🤖 AI se US Gen-Z caption likhwa raha hu...")
        try:
            prompt = "Write a viral, Gen-Z style Instagram Reel caption targeted for a USA audience. Include popular US hashtags like #LosAngeles #TrendingUSA. Keep it clean and catchy. No emojis at the very beginning."
            caption = model.generate_content(prompt).text
        except:
            caption = "Viral moments everyday! 🔥 #LosAngeles #USA #Trending #FYP"

        # 4. Upload to Instagram (Blocking - wait karega jab tak pura na ho)
        if chat_id: bot.send_message(chat_id, "📤 Instagram par Los Angeles location ke sath upload ho raha hai... (Isme 1-2 minute lag sakte hain)")
        cl = Client()
        cl.login(INSTA_USERNAME, INSTA_PASSWORD)
        loc = cl.location_search("Los Angeles, California")[0]
        
        cl.clip_upload("final_us_video.mp4", caption, location=loc)
        
        # 5. Save to Memory & Cleanup
        save_processed_link(link)
        os.remove("downloaded_video.mp4")
        os.remove("final_us_video.mp4")
        
        if chat_id: bot.send_message(chat_id, "✅ SUCCESS! Reel USA Location ke sath upload ho chuki hai! Ab main agle alarm tak so raha hu.")
        print("Upload Successful!")
        
    except Exception as e:
        error_msg = f"❌ ERROR aa gaya:\n{str(e)}"
        print(error_msg)
        if chat_id: bot.send_message(chat_id, error_msg)

if __name__ == "__main__":
    main()
