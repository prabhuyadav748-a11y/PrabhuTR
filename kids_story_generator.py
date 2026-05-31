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
    "Gommateshwara statue - King Chavundaraya, sculptor Arishtanemi, mother Kalala, and elephant Bahubali build the giant statue of peace - MORAL: Peace is the greatest victory",
    "Akbar and Birbal's clever lesson - Young Akbar, witty Birbal, courtiers and a clever monkey learn that honesty matters - MORAL: Truth and fairness win respect",
    "Vikram and Betaal's riddles - Brave king Vikram, ghostly Betaal, and court sages solve puzzles to learn wisdom - MORAL: Think before you act",
    "Ram and Sita's forest adventure - Little Rama, sister Sita, loyal brother Lakshmana, and monkey friend Hanuman learn about duty and love - MORAL: Kindness and courage go together",
    "Hanuman's leap of faith - Young Hanuman, monkey warriors, and Lord Rama help each other to find strength - MORAL: Faith and friendship move mountains",
    "The clever rabbit and the lion (Panchatantra) - A quick-thinking rabbit, proud lion, and friendly tortoise teach cleverness over strength - MORAL: Brains can beat brawn",
    "The greedy dog learns sharing - A greedy dog, kind children, and a wise farmer learn to share food - MORAL: Sharing brings happiness",
    "The mango tree and the children - A magical mango tree, playful kids, and a caring gardener show gratitude - MORAL: Respect nature and be thankful",
    "The boy who planted trees - Young boy Arjun, villagers, and a thirsty land bring life back with patience - MORAL: Small acts grow big change",
    "The little boat and the big river - A tiny boat, helpful fish, and wise elder teach perseverance - MORAL: Keep going even when waves come",
    "Sage Valmiki's change - Young hunter turned poet Valmiki, family, and the forest learn redemption - MORAL: People can change for the better",
    "The lost jewel of the palace - Princess Meera, brave guard Ramu, wise minister, and clever parrot find a lost jewel - MORAL: Honesty solves mysteries",
    "The brave washerman (Panchatantra) - A humble washerman, a king, and clever plans show courage - MORAL: Do the right thing even if poor",
    "The talking mango (folk tale) - A magic mango, curious children, and a trickster teach respect for elders - MORAL: Listen to good advice",
    "Onion and the clever farmer - Farmer Raju, animals, and a clever trick show resourcefulness - MORAL: Use your head to solve problems",
    "The festival of lights - Siblings preparing for Diwali with neighbors, lanterns, and kindness - MORAL: Celebrations are better when shared",
    "The boy and the banyan tree - Young Sohan, friends, and an old banyan provide shelter and lessons - MORAL: Protect and care for elders",
    "The princess who loved books - Bookish princess Tara, librarian, and village children spread learning - MORAL: Knowledge frees the mind",
    "The clever tailor - Tailor Hari, king, and friends teach humility and quick thinking - MORAL: Humility is strength",
    "The honest woodcutter - Kind woodcutter, magical spirit, and lost axe tell truth wins reward - MORAL: Honesty is its own reward",
    "The boy who raced the train - Curious boy Kunal, helpful conductor, and cautious parents learn safety - MORAL: Safety first",
    "The kite that would not fly - Little girl Maya, her brother, and a wise neighbor fix the kite with patience - MORAL: Practice makes better",
    "The golden sparrow - Crafty court, humble artisan, and a loyal bird teach justice - MORAL: Greed brings trouble",
    "The three brothers and the mango - Three brothers, a mango tree, and fair sharing teach fairness - MORAL: Share with love",
    "The village that sang - Music-loving villagers, traveling musician, and shy child show joy of art - MORAL: Music brings people together",
    "The brave fisher boy - Young fisher Anil, father, and sea creatures show bravery and care - MORAL: Courage with care helps others",
    "The little temple bell - A small bell, temple priest, and children learn respect for traditions - MORAL: Small things matter",
    "The elephant who wanted to dance - Playful elephant, circus friends, and a kind trainer learn acceptance - MORAL: Be yourself",
    "The rainmaker's promise - Farmer Lata, rainmaker elder, and village celebrate cooperation - MORAL: Work together to succeed",
    "The silver flute - Child musician, village fair, and a shy songbird teach confidence - MORAL: Share your gift",
    "The brave girl who climbed the mountain - Adventurous girl, guide, and mountain animals learn perseverance - MORAL: Aim high and be brave",
    "The little bridge that connected two villages - Builders, children, and elders unite for friendship - MORAL: Bridges bring people closer",
    "The moonlight thief (gentle ghost tale) - Kind ghost, curious children, and town elders learn kindness - MORAL: Understand before judging",
    "The gardener's secret - Gardener Meena, children, and plants show care for environment - MORAL: Nature rewards patience",
    "The tiny hero of the granary - Mouse, farmer, and clever cat protect the grain - MORAL: Even small friends help big tasks",
    "The princess and the talking parrot - Princess Leela, talking parrot, and court learn truth matters - MORAL: Truth always helps",
    "The wise tortoise and the impatient hare (Panchatantra) - Tortoise, hare, and race teach steady progress - MORAL: Slow and steady wins",
    "The festival of kites - Neighborhood children, kites, and friendly competition teach sportsmanship - MORAL: Win with grace",
    "The mystery of the missing cow - Village detective child, cows, and kind neighbor solve with teamwork - MORAL: Help your community",
    "The cloud who forgot to rain - Cloud, thirsty field, and children remind compassion - MORAL: Care for those in need",
    "The little boat that became a big ship - Dreamer Raju, mentors, and sea friends show growth - MORAL: Dreams grow with effort",
    "The toy maker's lesson - Toy maker, children, and a broken toy teach repair and love - MORAL: Fix, don't discard",
    "The brave squirrel and the mango festival - Squirrel, children, and festival guards protect the harvest - MORAL: Protect what matters",
    "The festival of colors - Siblings celebrate Holi with neighbors learning forgiveness - MORAL: Colors of kindness",
    "The shepherd who saved the night - Shepherd boy, animals, and stars show responsibility - MORAL: Care for those who depend on you",
    "The star that fell in the river - Curious child, wise elder, and river spirits learn wonder - MORAL: Keep curiosity alive",
    "The boy who learned to count - Little student, teacher, and chalk teach math is fun - MORAL: Learn with joy",
    "The copper coin and the wise king - Poor family, king, and a test of honesty teach fairness - MORAL: True wealth is honesty",
    "The lost tambourine - Music class, missing instrument, and teamwork solve the case - MORAL: Work together to find solutions",
    "The brave camel at the desert fair - Camel, child rider, and desert folk show adaptability - MORAL: Adjust and keep going",
    "The little lighthouse keeper - Young keeper, ships, and storm teach duty - MORAL: Perseverance saves lives",
    "The mango seller's kindness - Seller, hungry child, and neighbors teach giving - MORAL: Small kindness counts",
    "The painter who painted the sun - Young painter, village wall, and children learn expression - MORAL: Art brightens life",
    "The lost letter - Postman, child, and long journey reunite friends - MORAL: Keep promises",
    "The child who taught the tiger to be gentle - Clever child, tiger cub, and forest friends teach taming anger - MORAL: Patience changes hearts",
    "The little shop that helped everyone - Shopkeeper, villagers, and shared trust build community - MORAL: Be helpful",
    "The moon and the mango tree - Night tale where moon visits a tree to comfort it - MORAL: Care comforts",
    "The kite of hope - Orphan child, a kite, and a kind mentor show hope - MORAL: Hope lifts us",
    "The cinnamon merchant's journey - Merchant, helpful animals, and markets teach honesty in trade - MORAL: Fair trade matters",
    "The clever crow and the pitcher (classic fable) - Thirsty crow, water pitcher, and pebbles show ingenuity - MORAL: Use your wit",
    "The rabbit who loved carrots - Rabbit, friends, and a kind farmer teach gratitude - MORAL: Appreciate helpers",
    "The boy who made a clock - Inventive child, teacher, and village learn creativity - MORAL: Create to help others",
    "The little festival of lamps - Village lights, children, and neighbors celebrate unity - MORAL: Light beats darkness",
    "The story of the banyan and the peepal - Two trees teach cooperation and sharing shade - MORAL: Share resources",
    "The fisherman and the moonfish - Fisher, magical fish, and choice teach responsibility - MORAL: Take care of gifts",
    "The tailor who mended a kingdom - Tailor, king, and villagers mend clothes and hearts - MORAL: Small acts heal",
    "The brave boy and the wild horse - Boy, horse, and trainer build trust - MORAL: Trust matters",
    "The little doctor of the village - Young healer, sick animals, and learning teach care - MORAL: Help where you can",
    "The silversmith's promise - Silversmith, apprentice, and community learn keeping promises - MORAL: Keep your word",
    "The story of two sisters - Sisterly bond, challenges, and kindness teach family love - MORAL: Sisters support each other",
    "The seed that never gave up - Tiny seed, gardener, and forest show persistence - MORAL: Never give up",
    "The brave rooster - Rooster, farm friends, and sunrise teach duty - MORAL: Wake up and do your part",
    "The little library - Children start a library, share books, and change the town - MORAL: Share knowledge",
    "The festival of boats - Riverfolk, boats, and children celebrate safe journeys - MORAL: Prepare and help others",
    "The story of the gentle giant - Gentle giant, children, and village learn kindness regardless of size - MORAL: Size doesn't define heart",
    "The child who mended songs - Shy singer, teacher, and friends find voice - MORAL: Practice brings confidence",
    "The lost seedling - Child gardener, storm, and neighbors save a sapling - MORAL: Protect new life",
    "The night the moon sang - Magical night story about music and dreams - MORAL: Dream with joy",
    "The brave painter and the rainbow - Painter, children, and rain create joy - MORAL: Spread color and cheer",
    "The little clocktower - Town clock, caretaker, and children learn punctuality - MORAL: Value time",
    "The story of a small hero - Every-day courage from ordinary kids helping others - MORAL: Small heroes matter",
    "The festival of harvest - Farmers, families, and children celebrate hard work - MORAL: Appreciate effort",
    "The little boat that shared its shade - Boat, sun, and friends help others cool off - MORAL: Share what you have",
    "The child and the paper bird - Origami bird, imagination, and flight teach creativity - MORAL: Make things with love",
    "The story of the two gardens - Neighboring gardens learn to share water and grow together - MORAL: Cooperation grows abundance"
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
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    # write a short part of the prompt to make placeholder images unique
    short = (prompt[:180] + '...') if len(prompt) > 180 else prompt
    draw.text((30, 340), short, fill=(0, 0, 0), font=font)
    img.save(output_path)
    return False


def translate_text(text, target_lang_code, retries=2):
    """Try to translate text from English to target_lang_code using public LibreTranslate endpoints.
    If translation fails, return original text."""
    if not target_lang_code or target_lang_code == 'en':
        return text
    endpoints = ["https://libretranslate.de/translate", "https://libretranslate.com/translate"]
    for ep in endpoints:
        for attempt in range(retries):
            try:
                resp = requests.post(ep, data={
                    'q': text,
                    'source': 'en',
                    'target': target_lang_code,
                    'format': 'text'
                }, timeout=10)
                if resp.status_code == 200:
                    j = resp.json()
                    translated = j.get('translatedText') or j.get('translation') or ''
                    if translated:
                        return translated
                else:
                    # try next endpoint
                    break
            except Exception:
                continue
    return text


def generate_fallback_story(topic, num_scenes, video_language='english'):
    # Create a lively, kid-friendly topic-driven fallback story
    print(f"Using fallback story for topic: {topic[:120]}")

    # Extract title and moral when available
    title = None
    moral = "Be kind to everyone"
    desc = topic

    if " - " in topic:
        title_candidate, rest = topic.split(" - ", 1)
        title = title_candidate.strip()
        desc = rest.strip()
    else:
        title = " ".join(topic.split()[:6]).strip()

    if "MORAL:" in topic:
        moral_candidate = topic.split("MORAL:", 1)[1].strip()
        if moral_candidate:
            moral = moral_candidate
    else:
        if "MORAL" in desc:
            parts = desc.rsplit("MORAL", 1)
            if len(parts) > 1:
                moral = parts[1].strip(': -\n ')

    # Friendly character pool and vibrant backgrounds/props
    char_pool = ["Asha", "Ravi", "Mira", "Kiran", "Gajraj", "Devi", "Lila", "Veer", "Anu", "Satya", "Bittu", "Rani", "Arjun", "Tara", "Neel"]
    random.shuffle(char_pool)
    characters = char_pool[:4]

    backgrounds = ["sunny village", "colorful market", "bamboo forest", "sea shore", "flower garden", "royal courtyard", "mountain path", "ancient temple"]
    props = ["bright kite", "golden drum", "paper boat", "shiny lamp", "wooden toy", "magic mango", "friendly elephant"]

    # Kid-friendly narration templates with action and emotion cues
    templates = [
        "{c} jumps out of bed with a big smile and says, 'Today we will explore {title}!'",
        "{c} and friends discover a sparkling place where something surprising happens.",
        "When {c} helps a friend, everyone claps and learns how kindness saves the day.",
        "{c} shares a tasty snack and learns how sharing makes new friends.",
        "Together they build a playful invention and dance to celebrate teamwork.",
        "{c} tells a funny little story about {title} that makes everyone giggle.",
        "A friendly animal pops in to guide {c} on a cheerful adventure.",
        "{c} bravely stands up to help someone and learns that courage is gentle."
    ]

    scenes = []
    for i in range(num_scenes):
        # pick random character and template for variety
        name = random.choice(characters)
        template = random.choice(templates)
        narration = template.format(c=name, title=title)
        # Keep narrations short and cheerful
        narration = narration.replace('  ', ' ').strip()
        if not narration.endswith('.'):
            narration += '.'

        # Build an animation-friendly image prompt: character action, expression, background, prop, camera angle
        bg = random.choice(backgrounds)
        prop = random.choice(props)
        actions = ["running", "jumping", "dancing", "smiling", "pointing", "hugging", "playing", "discovering"]
        action = random.choice(actions)
        expressions = ["happy", "curious", "surprised", "proud", "gentle"]
        expr = random.choice(expressions)
        camera_angles = ["wide shot", "close-up", "mid shot", "low angle", "overhead"]
        cam = random.choice(camera_angles)

        image_prompt = (
            f"animated, cute cartoon {name} {action} with a {expr} expression, "
            f"background: {bg}, prop: {prop}, {cam}, bright colorful lighting, Pixar style, kid-friendly action"
        )

        scenes.append({"narration": narration, "image_prompt": image_prompt})

    story = {
        "title": title or "A Wonderful Story",
        "moral": moral or "Be kind to everyone",
        "scenes": scenes[:num_scenes]
    }
    # Translate fallback into target language (except image_prompts remain English)
    lang_map = {
        'english': 'en', 'hindi': 'hi', 'tamil': 'ta', 'telugu': 'te', 'kannada': 'kn',
        'malayalam': 'ml', 'bengali': 'bn', 'marathi': 'mr'
    }
    target_code = lang_map.get(video_language.lower(), 'en')
    if video_language.lower() != 'english' and target_code != 'en':
        print(f"Translating fallback story to {video_language} ({target_code})")
        try:
            story['title'] = translate_text(story['title'], target_code)
            story['moral'] = translate_text(story['moral'], target_code)
            for s in story['scenes']:
                s['narration'] = translate_text(s['narration'], target_code)
            print("Translation complete for fallback story.")
        except Exception as e:
            print(f"Fallback translation failed: {e}")

    return story


def generate_story_with_groq(topic, num_scenes, groq_api_key, video_language, lang_name):
    print(f"generate_story_with_groq: requested language={video_language}, num_scenes={num_scenes}")
    print(f"GROQ API key provided: {bool(groq_api_key)}")

    if not groq_api_key:
        print("No GROQ_API_KEY found — using local fallback story. Set GROQ_API_KEY to enable remote generation.")
        return generate_fallback_story(topic, num_scenes, video_language)

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
- Aim for about {num_scenes} scenes (the caller may accept fewer or more)
- Each narration: 2-3 simple sentences
- Use 3-4 NAMED cartoon characters with distinct looks
- NO scary content, NO violence
- End with "The End!" and moral

IMAGE PROMPT RULES (IMPORTANT):
- Each scene's "image_prompt" must be a short English phrase describing the scene and include clear animation cues: a simple action (e.g. running, jumping), character expression (e.g. happy, surprised), background, a prop if relevant, and a camera angle (e.g. close-up, wide shot).
- Keep prompts child-friendly, vivid, and suitable for generating bright 2D/3D style animations.

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

        print(f"Groq request completed, status={response.status_code}")
        try:
            snippet = response.text[:300]
            print(f"Groq response snippet: {snippet}")
        except Exception:
            pass

        if response.status_code == 200:
            try:
                content = response.json()['choices'][0]['message']['content']
                content = content.replace('```json', '').replace('```', '').strip()
                print(f"Groq returned content length={len(content)}")
                story = json.loads(content)
                if len(story.get('scenes', [])) >= num_scenes:
                    return story
                else:
                    print(f"Groq story had {len(story.get('scenes', []))} scenes, needed {num_scenes} — falling back.")
            except Exception as e:
                print(f"Failed to parse Groq response as JSON: {e}")
                # show short response to help debugging
                try:
                    print("Groq raw content (short):", response.text[:800])
                except Exception:
                    pass
    except Exception as e:
        print(f"Groq API error: {e}")

    print("Using local fallback story due to Groq failure or invalid response.")
    return generate_fallback_story(topic, num_scenes, video_language)


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

    # Desired scenes but also target duration (seconds) for final video
    DESIRED_NUM_SCENES = 8 if TEST_MODE else 48
    TARGET_SECONDS = 60 if TEST_MODE else 8 * 60  # 8 minutes target for full run

    # Verify voice configuration exists, fallback to English voice if missing
    if not VOICE:
        print(f"Warning: No voice configured for language '{VIDEO_LANGUAGE}'. Falling back to English voice.")
        VOICE = LANGUAGE_CONFIG['english']['voice']

    print("=" * 60)
    print("KIDS STORY VIDEO GENERATOR")
    print("=" * 60)
 
    topic = random.choice(TRENDING_TOPICS)
    print(f"\nSelected topic: {topic[:80]}...")
 
    print("\nGenerating story...")
    story = generate_story_with_groq(topic, DESIRED_NUM_SCENES, groq_api_key, VIDEO_LANGUAGE, LANG_NAME)
 
    title = story.get('title', 'A Wonderful Story')
    moral = story.get('moral', 'Be kind to everyone')
    scenes = story.get('scenes', [])
    ACTUAL_NUM_SCENES = len(scenes)
 
    print(f"Title: {title}")
    print(f"Moral: {moral}")
    print(f"Desired scenes: {DESIRED_NUM_SCENES}, Actual scenes returned: {ACTUAL_NUM_SCENES}")

    video_clips = []
    cumulative_audio_seconds = 0.0

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

        # create a unique id to reduce repeated images and filename collisions
        uid = datetime.now().strftime('%Y%m%d%H%M%S') + f"_{random.randint(1000,9999)}"
        img_path = TEMP_DIR / f"scene_{i}_{uid}.png"
        audio_path = TEMP_DIR / f"scene_{i}_{uid}.mp3"

        # Append a scene uid/seed to the prompt so image service returns varied images
        prompt_with_uid = f"{image_prompt}, scene {i+1}, uid {uid}, seed {random.randint(1,999999)}"
        print(f"  Image prompt: {prompt_with_uid[:200]}")

        # try downloading image (the function already retries), pass the unique prompt
        download_image(prompt_with_uid, img_path)
        await generate_voiceover(narration, str(audio_path), VOICE)

        audio = AudioFileClip(str(audio_path))
        clip = ImageClip(str(img_path)).set_duration(audio.duration).set_audio(audio)
        video_clips.append(clip)
        cumulative_audio_seconds += audio.duration
        print(f"  Done ({audio.duration:.1f}s), cumulative audio: {cumulative_audio_seconds:.1f}s")

    # Ending
    print("\nCreating ending...")
    ending_img = TEMP_DIR / "ending.png"
    ending_audio = TEMP_DIR / "ending.mp3"
    create_ending_card(moral, ending_img)
    await generate_voiceover(f"The End! Remember: {moral}. See you next time!", str(ending_audio), VOICE)
    audio = AudioFileClip(str(ending_audio))
    clip = ImageClip(str(ending_img)).set_duration(audio.duration).set_audio(audio)
    video_clips.append(clip)
    cumulative_audio_seconds += audio.duration

    # If cumulative audio is shorter than target, extend last clip duration to meet target
    if cumulative_audio_seconds < TARGET_SECONDS:
        extra = TARGET_SECONDS - cumulative_audio_seconds
        print(f"Extending final clip by {extra:.1f}s to reach target duration {TARGET_SECONDS}s")
        # extend the last clip (ending card) by extra seconds
        last_clip = video_clips[-1]
        new_duration = last_clip.duration + extra
        last_clip = last_clip.set_duration(new_duration)
        video_clips[-1] = last_clip

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
