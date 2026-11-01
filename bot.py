import os
import time
import random
import subprocess
import requests
import telebot
import google.generativeai as genai

# --- Credentials ---
TELEGRAM_TOKEN = "8985439812:AAG8MOcfiB7Lplr_IjcSu0bet42LJk2oJLw"
GEMINI_API_KEY = "AQ.Ab8RN6J3t8huhvllFs2EgfsrMUJ_a0MLKNYEMZJazJZ6mcV9Yw"

# Meta Official API Credentials
ACCESS_TOKEN = "EAATdbGETDAMBS5G1kQuroVurnVu9HkF5ZAqe00fs5uHwaT5zKQj8108l62ZBsYn38G2y2XANZCTytzKoNrOjRfMFPFZC02uoIfyNmylwsK8wmZC4daTe25ZCgfZBGg59mNa0RngzZBaZCCPK42EsOPkIDoDWxoZCmvt5gc179wbn8lz9dLqBfAgjke3yI1JwosIZB6M"
IG_USER_ID = "17841440705100139"
LA_LOCATION_ID = "110970792260960"

# Setup
bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

HISTORY_FILE = "processed_links.txt"
QUEUE_FILE = "pending_queue.txt"

def read_lines(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.read().splitlines() if line.strip()]

def write_lines(filepath, lines):
    with open(filepath, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip():
                f.write(line.strip() + "\n")

def sync_queue_to_github(commit_msg="Sync queue and processed links"):
    """Queue aur Processed files ko GitHub par permanently save karta hai taaki bot kabhi na bhoole"""
    try:
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        os.system('git config user.name "github-actions[bot]"')
        os.system('git config user.email "github-actions[bot]@users.noreply.github.com"')
        for f_name in [HISTORY_FILE, QUEUE_FILE]:
            if os.path.exists(f_name):
                os.system(f"git add -f {f_name}")
        os.system(f'git commit -m "{commit_msg}" || true')
        os.system(f"git pull origin {branch} --rebase || true")
        os.system(f"git push origin HEAD:{branch} || true")
    except Exception as e:
        print("GitHub queue sync error:", e)

def fetch_and_queue_telegram_links():
    """
    Telegram se SAARE naye links (100 tak) ek baar mein utha kar pending_queue.txt 
    mein save kar leta hai aur Telegram offset clear kar deta hai.
    """
    processed = read_lines(HISTORY_FILE)
    queue = read_lines(QUEUE_FILE)  # Format: link|chat_id
    queued_links = [item.split("|")[0] for item in queue]

    new_added = 0
    last_chat_id = None
    max_update_id = None

    try:
        updates = bot.get_updates(limit=100, timeout=10)
        for update in updates:
            max_update_id = update.update_id
            if update.message and update.message.text:
                chat_id = update.message.chat.id
                last_chat_id = chat_id
                # Agar ek message mein multiple links bheje hon toh sab alag-alag pakdega
                words = update.message.text.split()
                for word in words:
                    word = word.strip()
                    if "instagram.com/reel/" in word or "instagram.com/p/" in word:
                        # Clean tracking params (?igsh=...) taaki duplicate na ho
                        clean_link = word.split("?")[0].rstrip("/")
                        if clean_link not in processed and clean_link not in queued_links:
                            queue.append(f"{clean_link}|{chat_id}")
                            queued_links.append(clean_link)
                            new_added += 1

        # Acknowledge updates to Telegram so buffer stays clean after saving to file
        if max_update_id is not None:
            bot.get_updates(offset=max_update_id + 1, limit=1)

        if new_added > 0:
            write_lines(QUEUE_FILE, queue)
            sync_queue_to_github(f"Added {new_added} new links to queue")
            if last_chat_id:
                bot.send_message(
                    last_chat_id,
                    f"📥 {new_added} naye links Permanent Queue mein save ho gaye!\n"
                    f"📋 Total Pending Links in Queue: {len(queue)}"
                )

    except Exception as e:
        print("Telegram fetch error:", e)

    # Ab queue se sabse pehla link nikalo upload ke liye
    queue = read_lines(QUEUE_FILE)
    if not queue:
        return None, None, 0

    first_item = queue[0]
    parts = first_item.split("|")
    link = parts[0]
    chat_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else last_chat_id
    return link, chat_id, len(queue)

def mark_link_completed(link):
    """Upload hone ke baad link ko pending_queue se hata kar processed_links mein daal deta hai"""
    processed = read_lines(HISTORY_FILE)
    if link not in processed:
        processed.append(link)
    write_lines(HISTORY_FILE, processed)

    queue = read_lines(QUEUE_FILE)
    new_queue = [item for item in queue if item.split("|")[0] != link]
    write_lines(QUEUE_FILE, new_queue)

    sync_queue_to_github("Marked reel as completed and updated queue")
    return len(new_queue)

def get_related_bgm(caption, output_bgm="bgm.mp3"):
    cap_lower = caption.lower() if caption else ""
    bgm_pool = {
        "funny": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sneaky%20Snitch.mp3",
        "hype": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Local%20Forecast%20-%20Elevator.mp3",
        "chill": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3",
        "default": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Wallpaper.mp3"
    }

    if any(w in cap_lower for w in ["funny", "lol", "bro", "wait", "meme", "joke", "prank"]):
        url = bgm_pool["funny"]
    elif any(w in cap_lower for w in ["gym", "car", "sigma", "edit", "crazy", "wild", "fight"]):
        url = bgm_pool["hype"]
    elif any(w in cap_lower for w in ["sad", "love", "life", "real", "feel", "night"]):
        url = bgm_pool["chill"]
    else:
        url = bgm_pool["default"]

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(output_bgm, "wb") as f:
                f.write(r.content)
            return True
    except Exception as e:
        print("CDN BGM download skipped, generating synth background beat:", e)

    os.system(f'ffmpeg -f lavfi -i "sine=frequency=110:sample_rate=44100" -t 60 -c:a libmp3lame {output_bgm} -y')
    return os.path.exists(output_bgm)

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

def push_video_to_github_raw(file_path):
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("GITHUB_REF_NAME", "main")

    if not repo:
        repo = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).decode().strip()
        repo = repo.split("github.com/")[-1].replace(".git", "")

    os.system('git config user.name "github-actions[bot]"')
    os.system('git config user.email "github-actions[bot]@users.noreply.github.com"')
    os.system(f"git pull origin {branch} --rebase || true")
    os.system(f"git add -f {file_path}")
    os.system('git commit -m "Temp host reel video for Meta API" || true')
    os.system(f"git push origin HEAD:{branch}")

    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
    print("GitHub Raw Video URL Ready:", raw_url)
    time.sleep(5)
    return raw_url, branch

def cleanup_github_temp_video(file_path, branch="main"):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        os.system(f"git rm -f {file_path} || true")
        os.system('git commit -m "Cleanup temp reel video" || true')
        os.system(f"git push origin HEAD:{branch} || true")
    except Exception as e:
        print("GitHub cleanup error:", e)

def publish_reel_meta_url(video_url, caption):
    init_url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "location_id": LA_LOCATION_ID,
        "access_token": ACCESS_TOKEN
    }
    res = requests.post(init_url, data=payload).json()

    if "error" in res:
        print("Retrying container without location_id...", res)
        payload.pop("location_id", None)
        res = requests.post(init_url, data=payload).json()

    if "id" not in res:
        raise Exception(f"Meta Container Init Error: {res}")

    creation_id = res["id"]
    print(f"Container Created! ID: {creation_id}. Waiting for Meta to download & process...")

    status_url = f"https://graph.facebook.com/v20.0/{creation_id}"
    for attempt in range(25):
        time.sleep(10)
        status_res = requests.get(status_url, params={"fields": "status_code,status", "access_token": ACCESS_TOKEN}).json()
        status = status_res.get("status_code")
        print(f"Check {attempt+1}: Video Status = {status} ({status_res.get('status', '')})")
        
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
    link, chat_id, total_pending = fetch_and_queue_telegram_links()
    
    if not link:
        print("Koi nayi link nahi mili Telegram ya Queue mein. Sab khali hai.")
        return

    video_path = "downloaded_video.mp4"
    desc_file = "downloaded_video.description"
    bgm_path = "bgm.mp3"
    edited_path = "temp_reel_upload.mp4"
    branch_name = "main"

    try:
        if chat_id:
            bot.send_message(
                chat_id,
                f"🚀 Queue se Reel #{1} process ho rahi hai (Total Pending: {total_pending})\nLink: {link}"
            )
        
        # 1. Download Video + Original Caption
        if chat_id: bot.send_message(chat_id, "⬇️ HD Video aur Asli Caption download ho raha hai...")
        os.system(f"yt-dlp --write-description -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o '{video_path}' '{link}'")
        
        if not os.path.exists(video_path):
            # Agar koi broken/deleted link ho toh queue se hata do taaki queue atke nahi
            mark_link_completed(link)
            raise Exception("Download fail ho gaya! Broken link queue se hata di gayi hai.")

        orig_caption = ""
        if os.path.exists(desc_file):
            with open(desc_file, "r", encoding="utf-8", errors="ignore") as f:
                orig_caption = f.read().strip()

        # 2. Download Related Background Music & Mix (Original 100% + BGM 5%)
        if chat_id: bot.send_message(chat_id, "🎵 Related Music 5% volume par aur Original Audio 100% par mix ho raha hai...")
        has_bgm = get_related_bgm(orig_caption, bgm_path)

        probe_audio = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
            capture_output=True, text=True
        ).stdout.strip()

        if has_bgm and probe_audio:
            ffmpeg_cmd = (
                f'ffmpeg -i {video_path} -stream_loop -1 -i {bgm_path} -filter_complex '
                f'"[0:v]setpts=0.98*PTS,eq=saturation=1.04,scale=720:1280:force_original_aspect_ratio=decrease,'
                f'pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v];'
                f'[0:a]atempo=1.02,volume=1.0[a0];'
                f'[1:a]volume=0.05[a1];'
                f'[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[a]" '
                f'-map "[v]" -map "[a]" -r 30 -c:v libx264 -profile:v main -level:v 4.0 -b:v 3500k -maxrate 4000k -bufsize 8000k '
                f'-c:a aac -b:a 128k -ar 44100 -movflags +faststart -shortest {edited_path} -y'
            )
        else:
            ffmpeg_cmd = (
                f'ffmpeg -i {video_path} -filter_complex '
                f'"[0:v]setpts=0.98*PTS,eq=saturation=1.04,scale=720:1280:force_original_aspect_ratio=decrease,'
                f'pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v]" '
                f'-map "[v]" -map 0:a? -r 30 -c:v libx264 -profile:v main -level:v 4.0 -b:v 3500k '
                f'-c:a aac -b:a 128k -ar 44100 -movflags +faststart {edited_path} -y'
            )

        os.system(ffmpeg_cmd)
        
        if not os.path.exists(edited_path):
            raise Exception("Video editing (FFmpeg) fail ho gayi.")

        # 3. Enhance Original Caption
        if chat_id: bot.send_message(chat_id, "✍️ Video ke original caption ko enhance kiya ja raha hai...")
        final_caption = enhance_original_caption(orig_caption)

        # 4. Push Video to GitHub Raw URL
        if chat_id: bot.send_message(chat_id, "🔗 GitHub Server par temporary direct link ban raha hai...")
        raw_video_url, branch_name = push_video_to_github_raw(edited_path)

        # 5. Upload via Official Meta Graph API
        if chat_id: bot.send_message(chat_id, "📤 Official Meta API se Reel upload ho rahi hai (30-40 sec lagenge)...")
        media_id = publish_reel_meta_url(raw_video_url, final_caption)
        
        # 6. Mark Completed & Sync Queue to GitHub
        remaining = mark_link_completed(link)
        if chat_id:
            bot.send_message(
                chat_id,
                f"✅ SUCCESS! Reel upload ho gayi!\n"
                f"🆔 Post ID: {media_id}\n"
                f"📋 Queue mein bachi hui Reels: {remaining}\n\n"
                f"📝 Caption:\n{final_caption}"
            )
        print("Upload Successful! Media ID:", media_id)

    except Exception as e:
        print(f"Error aa gaya: {e}")
        if chat_id: bot.send_message(chat_id, f"❌ Error: {e}")
    
    finally:
        for f_path in [video_path, desc_file, bgm_path]:
            if os.path.exists(f_path):
                os.remove(f_path)
        cleanup_github_temp_video(edited_path, branch_name)

if __name__ == "__main__":
    process_and_upload()
