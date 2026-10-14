import os
import time
import telebot
import yt_dlp
from moviepy.editor import VideoFileClip, CompositeVideoClip, vfx
import google.generativeai as genai
from instagrapi import Client

# Aapki Saari Details (Sab fix hai)
TELEGRAM_TOKEN = '8985439812:AAG8MOcfiB7Lplr_IjcSu0bet42LJk2oJLw'
ALLOWED_CHAT_ID = 6649646092
GEMINI_API_KEY = 'AQ.Ab8RN6J3t8huhvllFs2EgfsrMUJ_a0MLKNYEMZJazJZ6mcV9Yw'
IG_USERNAME = 'fan_p_age123'
IG_PASSWORD = 'yp@365637'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

def send_alert(chat_id, error_msg):
    try:
        bot.send_message(chat_id, f"🚨 **ERROR!**\n`{error_msg}`")
    except:
        pass

def generate_us_caption(original_title):
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"Original reel title is: '{original_title}'. Write a very short, engaging Instagram Reel caption for a US Gen-Z audience based on this topic. Don't write on the video, just the caption text. Add 4-5 USA-targeted trending hashtags (like #usa, #losangeles, #viral)."
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return f"{original_title} 🔥👀 #usa #losangeles #viral"

def download_video(url, chat_id):
    temp_file = "raw_video.mp4"
    if os.path.exists(temp_file): os.remove(temp_file)
    try:
        ydl_opts = {'format': 'best', 'outtmpl': temp_file, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info to get original title
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Trending Video')
        return temp_file, title
    except Exception as e:
        send_alert(chat_id, f"Download Fail: {str(e)}")
        return None, None

def edit_video(video_path, chat_id):
    try:
        clip = VideoFileClip(video_path)
        # Anti-Copyright (Speed & Color) - Purana system active
        clip = clip.fx(vfx.speedx, 1.03).fx(vfx.colorx, 1.05)
        
        # Clean 1080p Canvas without any text overlay
        W, H = 1080, 1920
        scaled_clip = clip.resize(width=int(W * 0.95)).set_position(('center', 'center'))
        
        final_video = CompositeVideoClip([scaled_clip], size=(W, H)).set_duration(clip.duration)
        output_file = "ready_for_ig.mp4"
        
        # 60FPS HD Render
        final_video.write_videofile(output_file, fps=60, codec="libx264", bitrate="8000k", threads=4)
        return output_file
    except Exception as e:
        send_alert(chat_id, f"Edit Error: {str(e)}")
        return None

def upload_to_instagram(video_path, final_caption, chat_id):
    try:
        cl = Client()
        session_file = "session.json"
        if os.path.exists(session_file):
            cl.load_settings(session_file)
            
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(session_file)
        
        # Location Tagging (Los Angeles)
        try:
            us_location = cl.location_search("Los Angeles, California")[0]
        except:
            us_location = None
            
        # Uploading with Location and Smart Caption
        cl.clip_upload(video_path, caption=final_caption, location=us_location)
        return True
    except Exception as e:
        send_alert(chat_id, f"Upload Fail: {str(e)}")
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id == ALLOWED_CHAT_ID:
        bot.reply_to(message, "🇺🇸 US Bot Ready! Insta Reel ka link bhejiye.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    if message.chat.id != ALLOWED_CHAT_ID: return
    url = message.text.strip()
    
    if "instagram.com" not in url:
        bot.reply_to(message, "❌ Sirf Instagram link bhejein!")
        return
        
    bot.reply_to(message, "📥 Link received! Processing start...")
    
    # 1. Download & Get Original Title
    raw_vid, original_title = download_video(url, message.chat.id)
    if not raw_vid: return
        
    # 2. AI Creates Caption based on Title
    bot.reply_to(message, f"🤖 AI original caption padh raha hai: '{original_title}'...")
    final_caption = generate_us_caption(original_title)
    
    # 3. Clean HD Edit
    bot.reply_to(message, "✂️ Clean Editing Video (1080p 60FPS) Without Text...")
    final_vid = edit_video(raw_vid, message.chat.id)
    if not final_vid: return
        
    # 4. Upload with US Location
    bot.reply_to(message, "🚀 Uploading to Instagram with Los Angeles Location...")
    if upload_to_instagram(final_vid, final_caption, message.chat.id):
        bot.reply_to(message, "✅ Reel successfully uploaded with USA Location & Hashtags!")

bot.polling(none_stop=True)
