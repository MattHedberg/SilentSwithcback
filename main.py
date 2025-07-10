
# AI TikTok Automation System: Full Script-to-Video Pipeline

import openai
import datetime
import requests
import subprocess
import random
import os
import json
import time
import threading
import argparse
from flask import Flask, render_template_string

# 1. SCRIPT GENERATION (ChatGPT API)
def generate_script():
    openai.api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
    prompt = (
        "Write a 30-second TikTok story in the style of a short mystery. It should start with a hook and end on a cliffhanger. "
        "Keep the word count under 90 words. Include a product mention subtly if possible."
    )
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    story_text = response['choices'][0]['message']['content'].strip()
    return story_text

# 2. AI VOICE GENERATION (ElevenLabs API)
def generate_voice(text):
    api_key = os.getenv("ELEVENLABS_API_KEY", "your-elevenlabs-api-key")
    voice_id = os.getenv("VOICE_ID", "your-selected-voice-id")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.75, "similarity_boost": 0.75}
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        filename = f"voice_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    else:
        raise Exception("Failed to generate voiceover")

# 3. PIKA PROMPTS GENERATOR (manual)
def generate_pika_prompts():
    base_prompt = (
        "A mystical dark forest trail at night, glowing mist swirling around the trees, dim moonlight casting long shadows, "
        "a mountain bike rider slowly moving through the fog. The camera drifts slightly as if someone is watching. The atmosphere "
        "is eerie but captivating, with cinematic lighting. Add subtle glowing particles in the mist. Vertical 9:16 format. "
        "Add bottom caption text: \"What happens next??\""
    )
    variations = [
        "The rider pauses, sensing something behind them.",
        "A soft whisper echoes from the trees.",
        "A glowing figure flickers in the distance.",
        "The trail forks, one side darker than the other.",
        "A shadow moves quickly across the path.",
        "The mist thickens, almost swallowing the rider.",
        "A strange marking appears on a tree.",
        "The rider’s headlamp flickers, then dies.",
        "An old wooden sign appears: ‘TURN BACK.’",
        "The rider dismounts... and looks up slowly."
    ]
    prompts = [f"{base_prompt} {variation}" for variation in variations]
    for i, prompt in enumerate(prompts):
        with open(f"pika_prompt_{i+1}.txt", "w") as f:
            f.write(prompt)
    print("Pika prompts generated for manual input.")

# 4. ADD SUBTITLES
def add_subtitles(video_input, text, output_file):
    subtitle_cmd = [
        'ffmpeg', '-i', video_input,
        '-vf', f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{text}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=h-60",
        '-codec:a', 'copy', output_file
    ]
    subprocess.run(subtitle_cmd, check=True)

# 5. MERGE AUDIO + VIDEO
def merge_audio_video(audio_file, video_file, output_file):
    command = [
        'ffmpeg',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        output_file
    ]
    subprocess.run(command, check=True)

# 6. EXPORT TO SHORTS FOLDER
def export_to_short_platforms(final_video):
    shorts_dir = "shorts_ready"
    os.makedirs(shorts_dir, exist_ok=True)
    base = os.path.basename(final_video)
    export_path = os.path.join(shorts_dir, base)
    subprocess.run(["cp", final_video, export_path])
    print("Copied for Shorts/Instagram Reels:", export_path)

# 7. POST TO TIKTOK (Mock)
def auto_post_to_tiktok(video_path):
    print("[MOCK] Posting to TikTok via emulator...")
    print("[MOCK] Posted:", video_path)

# 8. FULL PIPELINE
log = []

def run_pipeline():
    script = generate_script()
    voice_file = generate_voice(script)
    video_dir = "videos"
    video_file = random.choice([f for f in os.listdir(video_dir) if f.endswith('.mp4')])
    video_path = os.path.join(video_dir, video_file)
    merged_file = f"merged_tiktok_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
    merge_audio_video(voice_file, video_path, merged_file)
    final_output = f"final_tiktok_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
    add_subtitles(merged_file, script, final_output)
    export_to_short_platforms(final_output)
    auto_post_to_tiktok(final_output)
    log.append({"timestamp": datetime.datetime.now().isoformat(), "video": final_output})
    print("Final video ready:", final_output)

# 9. DASHBOARD
app = Flask(__name__)

dashboard_html = """
<!DOCTYPE html>
<html>
<head><title>AI TikTok Dashboard</title></head>
<body style=\"font-family:sans-serif;padding:2rem\">
<h2>📊 TikTok Automation Dashboard</h2>
<table border=\"1\" cellpadding=\"8\">
<tr><th>Timestamp</th><th>Video File</th></tr>
{% for item in log %}<tr><td>{{ item.timestamp }}</td><td>{{ item.video }}</td></tr>{% endfor %}
</table>
<p><a href=\"/run\">▶ Run Pipeline</a></p>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(dashboard_html, log=log)

@app.route("/run")
def trigger():
    run_pipeline()
    return "Pipeline executed. <a href='/'>Return to Dashboard</a>"

# 10. AUTOMATIC DAILY POSTING (3x per day)
def schedule_daily_runs():
    def job():
        for _ in range(3):
            run_pipeline()
            time.sleep(60 * 60 * 4)
    threading.Thread(target=job).start()

# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Run daily automation pipeline")
    parser.add_argument("--serve", action="store_true", help="Serve the dashboard")
    args = parser.parse_args()

    now = datetime.datetime.now()
    if args.run:
        schedule_daily_runs()
    elif args.serve:
        app.run(debug=True)
    elif now.hour >= 20:
        schedule_daily_runs()
    else:
        print("It's not yet time to start auto-posting. Use --serve to view dashboard or --run to force launch.")
