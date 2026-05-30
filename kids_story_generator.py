#!/usr/bin/env python3
import os
import json
import asyncio
import requests
import random
import argparse
from pathlib import Path
from datetime import datetime
from io import BytesIO

import edge_tts
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips
)
from PIL import Image, ImageDraw, ImageFont

# Optional Google / GitHub upload imports
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except Exception:
    Credentials = None

# Configuration
OUTPUT_DIR = Path("./output")
TEMP_DIR = Path("./temp")
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Multi-language voice configuration (Edge-TTS)
LANGUAGE_CONFIG = {
    "english": {"voice": "en-US-AnaNeural", "lang_code": "en", "name": "English"},
    "hindi": {"voice": "hi-IN-SwaraNeural", "lang_code": "hi", "name": "Hindi"},
    "tamil": {"voice": "ta-IN-PallaviNeural", "lang_code": "ta", "name": "Tamil"},
    "telugu": {"voice": "te-IN-ShrutiNeural", "lang_code": "te", "name": "Telugu"},
    "kannada": {"voice": "kn-IN-SapnaNeural", "lang_code": "kn", "name": "Kannada"},
    "malayalam": {"voice": "ml-IN-SobhanaNeural", "lang_code": "ml", "name": "Malayalam"},
    "bengali": {"voice": "bn-IN-TanishaaNeural", "lang_code": "bn", "name": "Bengali"},
    "marathi": {"voice": "mr-IN-AarohiNeural", "lang_code": "mr", "name": "Marathi"}
}

TRENDING_TOPICS = [
    "Young Chandragupta Maurya - Little Chandragupta, his wise guru Chanakya, friend Bindusara, and loyal guard Pushyamitra learn to build the great Maurya empire - MORAL: Unity makes us stronger",
    "Emperor Ashoka's transformation - Young warrior prince Ashoka, his wife Devi, advisor Radhagupta, and elephant friend Gajraj witness the Kalinga war and learn peace is better than war - MORAL: True victory is winning hearts with kindness",
    "Raja Raja Chola builds the great temple - Young prince Raja Raja, architect Kunjaramallan, sculptor Shilpi, and elephant Airavata work together to build the magnificent Brihadeeswarar Temple - MORAL: Great dreams need great teamwork",
    "Young Shivaji's courage - Little Shivaji, mother Jijabai, guru Dadoji Konddev, and horse Vishwas learn about bravery and protecting people - MORAL: Even children can dream of greatness",
    "Tenali Rama's clever tricks - Witty Tenali Rama, king Krishnadevaraya, jealous minister Tathacharya, and parrot Shuka solve problems with humor - MORAL: Wit and wisdom are mightier than swords",
    "Aryabhata counts the stars - Young mathematician Aryabhata, his teacher Narayana, friend Varahamihira, and owl Uluka discover that Earth is round - MORAL: Curiosity and knowledge light up the world",
    "Rana Pratap's resistance - Brave Rana Pratap, loyal horse Chetak, general Hakim Khan, and friend Bhama Shah never give up their freedom - MORAL: Freedom is more precious than comfort",
    "Krishnadevaraya the just king - Wise king Krishnadevaraya, court jester Tenali Rama, queen Tirumalamba, and elephant Bhadra bring justice to Hampi - MORAL: A just ruler is loved by all",
    "The Hoysala lion slayer - Young prince Sala, guru Sudatta, friend Lakshmi, and dog Simha face a fierce lion to protect their village - MORAL: Bravery protects the innocent",
    "Kailasa temple at Ellora - King Krishna I, master architect Kokasa, sculptor Vishwakarma, and elephant Nandi carve an entire temple from a mountain - MORAL: Impossible dreams become real with determination",
    "Konark Sun Temple - King Narasimhadeva, architect Bisu Maharana, sculptor Sadashiva, and twelve stone horses build the chariot temple - MORAL: Imagination creates wonders",
    "Nalanda University - Teacher Shilabhadra, student Xuanzang, librarian Dharmakirti, and elephant Bodhi study at the world's first university - MORAL: Education is the light that removes darkness",
    "Chanakya's clever plan - Wise teacher Chanakya, young student Chandragupta, helper Sharangrav, and spy Ratnagupta work together to free India - MORAL: Intelligence defeats even the mightiest enemy",
    "Rajendra Chola's sea voyage - Brave king Rajendra, naval commander Arjuna, navigator Samudra, and parrot guide Kili sail across the ocean - MORAL: Courage and curiosity lead to great discoveries",
    "Gommateshwara statue - King Chavundaraya, sculptor Arishtanemi, mother Kalala, and elephant Bahubali build the giant statue of peace - MORAL: Peace is the greatest victory"
]

async def generate_voiceover(text, output_path, voice, retries=3):
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            print(f"  TTS attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                import time
                time.sleep(5 * (attempt + 1))
    return False


def download_image(prompt, output_path, retries=3):
    style_modifiers = (
        ", cute adorable cartoon style, pixar disney animation style, "
        "vibrant bright rainbow colors, sparkles and stars, "
        "soft rounded shapes, big expressive eyes, happy cheerful mood, "
        "children's storybook illustration, magical dreamy atmosphere, "
        "pastel background, high quality, detailed, beautiful lighting, "
        "safe for kids, no scary elements, warm friendly feeling"
    )
    safe_prompt = requests.utils.quote(prompt + style_modifiers)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1280&height=720&seed={random.randint(1, 10000)}"

    for attempt in range(retries):
        try:
            print(f"  Downloading image (attempt {attempt + 1})...")
            response = requests.get(url, timeout=120)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img = img.convert('RGB')
                img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                img.save(output_path)
                return True
        except Exception as e:
            print(f"  Retry {attempt + 1}: {e}")
            import time
            time.sleep(2)

    colors = [(255, 182, 193), (173, 216, 230), (144, 238, 144), (255, 218, 185), (255, 255, 200), (230, 190, 255)]
    img = Image.new('RGB', (1280, 720), random.choice(colors))
    img.save(output_path)
    return False


def generate_fallback_story(topic, num_scenes):
    story = {
        "title": "Emperor Ashoka's Transformation",
        "moral": "True victory is winning hearts with kindness",
        "scenes": [
            {"narration": "Long ago in ancient India, there lived a young warrior prince named Ashoka. He was very brave and strong!", "image_prompt": "cute cartoon young Indian prince Ashoka in golden palace, bright colors, Pixar style"},
            {"narration": "Ashoka had three best friends - his wife Devi, his advisor Radhagupta, and his elephant friend Gajraj!", "image_prompt": "cartoon prince Ashoka with wife Devi, advisor, and cute elephant friend, Indian palace"},
            {"narration": "One day, Ashoka went to fight a big war. He wanted to win and be the greatest king!", "image_prompt": "cartoon prince Ashoka on elephant going to battle, colorful Indian army"},
            {"narration": "But after the war, Ashoka saw something that made him very sad. Many people were hurt.", "image_prompt": "sad cartoon Ashoka looking at aftermath, somber but child-friendly"},
            {"narration": "Ashoka's heart broke. He said - What have I done? This is not victory!", "image_prompt": "cartoon Ashoka with tears, elephant Gajraj comforting him"},
            {"narration": "Kind Devi said - Dear Ashoka, true kings help people, they don't hurt them.", "image_prompt": "cartoon wife Devi comforting Ashoka, warm lighting"},
            {"narration": "From that day, Ashoka changed! He decided to never fight wars again.", "image_prompt": "cartoon Ashoka making a promise, glowing aura, transformation"},
            {"narration": "Instead, Ashoka built hospitals for sick people and animals!", "image_prompt": "cartoon Ashoka building hospital, doctors helping people"},
            {"narration": "He planted thousands of trees so travelers could rest in the shade.", "image_prompt": "cartoon Ashoka planting trees with villagers, sunny day"},
            {"narration": "Ashoka dug wells so everyone had clean water to drink!", "image_prompt": "cartoon Ashoka near a well, villagers drinking water"},
            {"narration": "He built tall pillars with lion statues and messages of peace!", "image_prompt": "cartoon Ashoka with famous lion pillar, four lions on top"},
            {"narration": "Gajraj the elephant was so proud! My friend is the kindest king!", "image_prompt": "happy cartoon elephant Gajraj with Ashoka, celebrating"},
            {"narration": "People from far away came to see the peaceful kingdom!", "image_prompt": "cartoon visitors meeting Ashoka, diverse characters"},
            {"narration": "Children loved Emperor Ashoka. He would play with them!", "image_prompt": "cartoon Ashoka playing with happy children in garden"},
            {"narration": "Even today, the lion pillar is the symbol of India!", "image_prompt": "cartoon showing Ashoka pillar and Indian emblem"},
            {"narration": "Remember - true victory is making others happy!", "image_prompt": "cartoon Ashoka with friends, hearts and peace symbols"},
            {"narration": "And that is the story of Emperor Ashoka! The End!", "image_prompt": "happy ending with Ashoka and friends waving, THE END"}
        ]
    }
    story["scenes"] = story["scenes"][:num_scenes]
    return story


def generate_story_with_groq(topic, num_scenes, groq_api_key, video_language, lang_name):
    if not groq_api_key:
        return generate_fallback_story(topic, num_scenes)

    lang_instruction = ""
    if video_language != "english":
        lang_examples = {
            "kannada": 'narration: "ಒಂದು ಕಾಲದಲ್ಲಿ ಭಾರತದಲ್ಲಿ ಒಬ್ಬ ಧೈರ್ಯಶಾಲಿ ರಾಜ ಇದ್ದನು."',
            "hindi": 'narration: "एक समय की बात है, भारत में एक बहादुर राजा था।"',
            "tamil": 'narration: "ஒரு காலத்தில் இந்தியாவில் ஒரு தைரியமான அரசன் இருந்தான்."',
            "telugu": 'narration: "ఒకప్పుడు భారతదేశంలో ఒక ధైర్యవంతుడైన రాజు ఉండేవాడు."',
            "malayalam": 'narration: "ഒരിക്കൽ ഇന്ത്യയിൽ ഒരു ധീരനായ രാജാവ് ഉണ്ടായിരുന്നു."',
            "bengali": 'narration: "এক সময় ভারতে এক সাহসী রাজা ছিলেন।"',
            "marathi": 'narration: "एकेकाळी भारतात एक शूर राजा होता."'
        }
        example = lang_examples.get(video_language, "")
        lang_instruction = f"""
CRITICAL: Write the ENTIRE story in {lang_name} language.
- "narration" = 100% {lang_name} script
- "title" = {lang_name} script
- "moral" = {lang_name} script
- ONLY "image_prompt" = English
Example: {example}
"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": f"""You are a children's story writer for kids aged 4-8.
{lang_instruction}
REQUIREMENTS:
- Story must have EXACTLY {num_scenes} scenes
- Each narration: 2-3 simple sentences
- Use 3-4 NAMED cartoon characters with distinct looks
- NO scary content, NO violence
- End with "The End!" and moral

Return ONLY valid JSON:
{{"title": "Story Title", "moral": "The moral", "scenes": [{{"narration": "Text", "image_prompt": "Description in English"}}]}}"""
                    },
                    {"role": "user", "content": f"Create a story about: {topic}"}
                ],
                "temperature": 0.85,
                "max_tokens": 6000
            },
            timeout=90
        )
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            content = content.replace('```json', '').replace('```', '').strip()
            story = json.loads(content)
            if len(story.get('scenes', [])) >= num_scenes:
                return story
    except Exception as e:
        print(f"Groq API error: {e}")

    return generate_fallback_story(topic, num_scenes)


def create_intro_card(title, output_path):
    img = Image.new('RGB', (1280, 720), (255, 215, 0))
    draw = ImageDraw.Draw(img)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_large = font_small = ImageFont.load_default()

    draw.rectangle([20, 20, 1260, 700], outline=(139, 69, 19), width=10)
    draw.text((640, 200), "Kids Story Time!", font=font_large, fill=(139, 69, 19), anchor="mm")
    draw.text((640, 350), title[:50], font=font_small, fill=(0, 0, 0), anchor="mm")
    for _ in range(20):
        x, y = random.randint(50, 1230), random.randint(50, 670)
        draw.text((x, y), "*", fill=(255, 255, 255), font=font_small)
    img.save(output_path)


def create_ending_card(moral, output_path):
    img = Image.new('RGB', (1280, 720), (255, 182, 193))
    draw = ImageDraw.Draw(img)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_large = font_small = ImageFont.load_default()

    draw.rectangle([20, 20, 1260, 700], outline=(255, 105, 180), width=10)
    draw.text((640, 200), "THE END", font=font_large, fill=(199, 21, 133), anchor="mm")
    draw.text((640, 350), "Moral:", font=font_small, fill=(0, 0, 0), anchor="mm")
    draw.text((640, 420), moral[:60], font=font_small, fill=(139, 0, 139), anchor="mm")
    img.save(output_path)


def create_thumbnail(title, output_path):
    img = Image.new('RGB', (1280, 720), (135, 206, 250))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
    except:
        font = ImageFont.load_default()

    colors = [(255, 182, 193), (255, 218, 185), (144, 238, 144), (255, 255, 200)]
    for i in range(8):
        draw.rectangle([i*160, 0, (i+1)*160, 720], fill=colors[i % len(colors)])
    draw.text((644, 364), title[:30], font=font, fill=(0, 0, 0), anchor="mm")
    draw.text((640, 360), title[:30], font=font, fill=(255, 255, 255), anchor="mm")
    draw.rectangle([10, 10, 1270, 710], outline=(255, 215, 0), width=15)
    img.save(output_path)


async def generate_video(test_mode: bool, video_language: str, groq_api_key: str, upload_youtube: bool = False, youtube_credentials: str = None, youtube_token: str = None, create_release: bool = False):
    TEST_MODE = test_mode
    VIDEO_LANGUAGE = video_language.lower()
    LANG_CONFIG = LANGUAGE_CONFIG.get(VIDEO_LANGUAGE, LANGUAGE_CONFIG["english"])
    VOICE = LANG_CONFIG["voice"]
    LANG_NAME = LANG_CONFIG["name"]

    print(f"Language: {LANG_NAME} ({VOICE})")

    NUM_SCENES = 8 if TEST_MODE else 35

    print("=" * 60)
    print("KIDS STORY VIDEO GENERATOR")
    print("=" * 60)

    topic = random.choice(TRENDING_TOPICS)
    print(f"\nSelected topic: {topic[:80]}...")

    print("\nGenerating story...")
    story = generate_story_with_groq(topic, NUM_SCENES, groq_api_key, VIDEO_LANGUAGE, LANG_NAME)

    title = story.get('title', 'A Wonderful Story')
    moral = story.get('moral', 'Be kind to everyone')
    scenes = story.get('scenes', [])

    print(f"Title: {title}")
    print(f"Moral: {moral}")
    print(f"Scenes: {len(scenes)}")

    video_clips = []

    # Intro
    print("\nCreating intro...")
    intro_img = TEMP_DIR / "intro.png"
    intro_audio = TEMP_DIR / "intro.mp3"
    create_intro_card(title, intro_img)
    await generate_voiceover(f"Welcome to Kids Story Time! Today's story is: {title}", str(intro_audio), VOICE)
    audio = AudioFileClip(str(intro_audio))
    clip = ImageClip(str(intro_img)).set_duration(audio.duration).set_audio(audio)
    video_clips.append(clip)

    # Scenes
    print("\nProcessing scenes...")
    for i, scene in enumerate(scenes):
        print(f"\nScene {i+1}/{len(scenes)}")
        narration = scene.get('narration', '')
        image_prompt = scene.get('image_prompt', '')

        img_path = TEMP_DIR / f"scene_{i}.png"
        audio_path = TEMP_DIR / f"scene_{i}.mp3"

        download_image(image_prompt, img_path)
        await generate_voiceover(narration, str(audio_path), VOICE)

        audio = AudioFileClip(str(audio_path))
        clip = ImageClip(str(img_path)).set_duration(audio.duration).set_audio(audio)
        video_clips.append(clip)
        print(f"  Done ({audio.duration:.1f}s)")

    # Ending
    print("\nCreating ending...")
    ending_img = TEMP_DIR / "ending.png"
    ending_audio = TEMP_DIR / "ending.mp3"
    create_ending_card(moral, ending_img)
    await generate_voiceover(f"The End! Remember: {moral}. See you next time!", str(ending_audio), VOICE)
    audio = AudioFileClip(str(ending_audio))
    clip = ImageClip(str(ending_img)).set_duration(audio.duration).set_audio(audio)
    video_clips.append(clip)

    print("\nCombining clips...")
    final_video = concatenate_videoclips(video_clips, method="compose")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:50]
    output_path = OUTPUT_DIR / f"kids_story_{safe_title}_{timestamp}.mp4"

    print(f"\nRendering video to: {output_path}")
    final_video.write_videofile(str(output_path), fps=24, codec='libx264', audio_codec='aac', preset='medium', threads=4)

    thumbnail_path = OUTPUT_DIR / f"thumbnail_{timestamp}.png"
    create_thumbnail(title, thumbnail_path)

    total_duration = final_video.duration
    minutes = int(total_duration // 60)
    seconds = int(total_duration % 60)

    metadata = {
        "title": title,
        "moral": moral,
        "duration_seconds": total_duration,
        "duration_formatted": f"{minutes}m {seconds}s",
        "video_path": str(output_path),
        "thumbnail_path": str(thumbnail_path),
        "language": LANG_NAME,
        "timestamp": timestamp
    }
    with open(OUTPUT_DIR / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    # Create release notes and YouTube description files for downstream upload
    release_notes = f"## {title}\n\n**Duration:** {minutes}m {seconds}s\n**Language:** {LANG_NAME}\n\n{title}\n\nMoral: {moral}\n\nDownload the video and thumbnail below.\n"
    with open(OUTPUT_DIR / "release_notes.md", "w") as f:
        f.write(release_notes)

    youtube_description = f"{title}\n\nMoral: {moral}\n\nThis animated kids story was created on {timestamp}.\n\n#kids #story #animation\n"
    with open(OUTPUT_DIR / "youtube_description.txt", "w") as f:
        f.write(youtube_description)

    final_video.close()
    for clip in video_clips:
        clip.close()

    print("\nVIDEO GENERATION COMPLETE!")
    print(f"Title: {title}")
    print(f"Duration: {minutes}m {seconds}s")
    print(f"Video: {output_path}")

    # Validate outputs before upload
    def validate_output(metadata_file=OUTPUT_DIR / 'metadata.json'):
        errors = []
        if not metadata_file.exists():
            errors.append(f"Missing metadata file: {metadata_file}")
            print('\n'.join(errors))
            return False
        try:
            meta = json.load(open(metadata_file))
        except Exception as e:
            print(f"Failed to read metadata: {e}")
            return False
        video_file = Path(meta.get('video_path', ''))
        thumb_file = Path(meta.get('thumbnail_path', ''))
        if not video_file.exists():
            errors.append(f"Video file missing: {video_file}")
        else:
            if video_file.stat().st_size < 1024 * 50:
                errors.append(f"Video file too small: {video_file} ({video_file.stat().st_size} bytes)")
        if not thumb_file.exists():
            errors.append(f"Thumbnail missing: {thumb_file}")
        else:
            try:
                with Image.open(thumb_file) as timg:
                    if timg.size[0] < 200 or timg.size[1] < 200:
                        errors.append(f"Thumbnail dimensions too small: {timg.size}")
            except Exception as e:
                errors.append(f"Failed to open thumbnail: {e}")
        if errors:
            print("Validation failed:")
            for e in errors:
                print(" - ", e)
            return False
        print("Validation passed: metadata, video and thumbnail look good.")
        return True

    valid = validate_output()

    # Optional YouTube upload
    if upload_youtube and valid:
        if not (youtube_credentials and youtube_token):
            print("YouTube upload requested but credentials/token files not provided. Skipping upload.")
        elif Credentials is None:
            print("Google libraries not available. Install google-auth and google-api-python-client to enable upload.")
        else:
            upload_video_to_youtube(youtube_token, output_path, title, youtube_description, thumbnail_path)
    elif upload_youtube and not valid:
        print("Skipping YouTube upload due to validation failure.")

    # Optional GitHub release via workflow/gh CLI
    if create_release and valid:
        print("create_release requested: release_notes.md written to output. The workflow will publish the release using this file. To publish locally, run gh release create manually with the generated files.")
    elif create_release and not valid:
        print("Skipping GitHub release due to validation failure.")

    return metadata


def upload_video_to_youtube(youtube_token_file, video_file, title, description, thumbnail_file=None):
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    try:
        creds = Credentials.from_authorized_user_file(youtube_token_file, SCOPES)
    except Exception as e:
        print(f"Failed to load YouTube credentials: {e}")
        return

    try:
        youtube = build('youtube', 'v3', credentials=creds)
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['kids', 'story', 'animation'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public'
            }
        }

        media = MediaFileUpload(str(video_file), chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")
        print(f"Upload complete: https://youtu.be/{response['id']}")

        if thumbnail_file:
            youtube.thumbnails().set(videoId=response['id'], media_body=MediaFileUpload(str(thumbnail_file))).execute()
    except Exception as e:
        print(f"YouTube upload failed: {e}")


def main():
    parser = argparse.ArgumentParser(description='Generate kids story animation video')
    parser.add_argument('--test', action='store_true', help='Generate a shorter test video')
    parser.add_argument('--language', default='english', help='Video language')
    parser.add_argument('--groq-api-key', default=os.environ.get('GROQ_API_KEY', ''), help='GROQ API key (or set GROQ_API_KEY env)')
    parser.add_argument('--upload-youtube', action='store_true', help='Upload generated video to YouTube (requires youtube_token.json)')
    parser.add_argument('--youtube-token', default='youtube_token.json', help='Path to youtube token JSON')
    parser.add_argument('--create-release', action='store_true', help='Create GitHub release with gh CLI')
    parser.add_argument('--validate', action='store_true', help='Validate files in output directory and exit with error if invalid')
    args = parser.parse_args()

    if args.validate:
        # validation-only mode
        # run the validation function defined inside generate_video by calling generate_video with test flag False but not producing new content
        # Instead, perform direct validation on existing output
        from pathlib import Path as _P
        meta_file = _P('./output/metadata.json')
        if not meta_file.exists():
            print('No metadata.json found in output to validate')
            raise SystemExit(1)
        try:
            meta = json.load(open(meta_file))
        except Exception as e:
            print(f'Failed to load metadata.json: {e}')
            raise SystemExit(2)

        # basic validation checks
        errors = []
        video_file = _P(meta.get('video_path', ''))
        thumb_file = _P(meta.get('thumbnail_path', ''))
        if not video_file.exists():
            errors.append('Video file missing: ' + str(video_file))
        elif video_file.stat().st_size < 1024 * 50:
            errors.append('Video file too small: ' + str(video_file.stat().st_size))
        if not thumb_file.exists():
            errors.append('Thumbnail missing: ' + str(thumb_file))
        if errors:
            print('Validation failed:')
            for e in errors:
                print(' -', e)
            raise SystemExit(3)
        print('Validation passed')
        raise SystemExit(0)

    asyncio.run(generate_video(args.test, args.language, args.groq_api_key, upload_youtube=args.upload_youtube, youtube_token=args.youtube_token, create_release=args.create_release))


if __name__ == '__main__':
    main()
