import os
import time
import telebot
import yt_dlp
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, vfx
import google.generativeai as genai
from instagrapi import Client

# Aapki Saari Details (Ab sab kuch ek jagah hai)
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

def generate_us_caption():
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = "Write a short, viral US Gen-Z Instagram Reel caption for a funny comedy/streamer video. Use slang like 'bro really thought 💀', 'ain't no way 😭'. Max 1 sentence + 3 US hashtags."
        response = model.generate_text(prompt)
        return response.text.strip()
    except:
        return "Bro really thought 💀😭 #ishowspeed #usareels #viral"

def download_video(url, chat_id):
    temp_file = "raw_video.mp4"
    if os.path.exists(temp_file): os.remove(temp_file)
    try:
        ydl_opts = {'format': 'best', 'outtmpl': temp_file, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return temp_file
    except Exception as e:
        send_alert(chat_id, f"Download Fail: {str(e)}")
        return None

def edit_video(video_path, chat_id):
    try:
        clip = VideoFileClip(video_path)
        clip = clip.fx(vfx.speedx, 1.03).fx(vfx.colorx, 1.05)
        W, H = 1080, 1920
        scaled_clip = clip.resize(width=int(W * 0.95)).set_position(('center', 'center'))
        meme_text = (TextClip(generate_us_caption(), fontsize=45, color='white', font='Impact', stroke_color='black', stroke_width=2.5)
                     .set_position(('center', 150)).set_duration(clip.duration))
        final_video = CompositeVideoClip([scaled_clip, meme_text], size=(W, H))
        output_file = "ready_for_ig.mp4"
        final_video.write_videofile(output_file, fps=60, codec="libx264", bitrate="8000k", threads=4)
        return output_file
    except Exception as e:
        send_alert(chat_id, f"Edit Error: {str(e)}")
        return None

def upload_to_instagram(video_path, chat_id):
    try:
        cl = Client()
        session_file = "session.json"
        if os.path.exists(session_file):
            cl.load_settings(session_file)
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(session_file)
        cl.clip_upload(video_path, caption=generate_us_caption())
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
    
    raw_vid = download_video(url, message.chat.id)
    if not raw_vid: return
        
    bot.reply_to(message, "✂️ Editing Video (1080p 60FPS)...")
    final_vid = edit_video(raw_vid, message.chat.id)
    if not final_vid: return
        
    bot.reply_to(message, "🚀 Uploading to Instagram...")
    if upload_to_instagram(final_vid, message.chat.id):
        bot.reply_to(message, "✅ Reel successfully uploaded!")

bot.polling(none_stop=True)

