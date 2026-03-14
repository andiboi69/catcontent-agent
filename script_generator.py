"""
Script Generator — Creates educational/cute cat video scripts.
Text-on-screen format with interesting facts and beautiful footage.
Tracks past scripts to avoid repeating captions/titles (YouTube spam prevention).
"""

import os
import json
import random
from groq import Groq
from config import GROQ_API_KEY, CONTENT_FORMATS


client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

# Script history file — persists across all generations
SCRIPT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "used_scripts.json")


def _load_script_history():
    """Load list of previously generated titles and captions."""
    if os.path.exists(SCRIPT_HISTORY_FILE):
        try:
            with open(SCRIPT_HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"titles": [], "captions": []}


def _save_script_history(history):
    """Save script history to disk."""
    try:
        with open(SCRIPT_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def _normalize(text):
    """Normalize text for fuzzy comparison — lowercase, strip punctuation/spaces."""
    return "".join(c for c in text.lower() if c.isalnum())


def _is_too_similar(new_text, existing_list, threshold=0.7):
    """Check if new_text is too similar to any existing entry."""
    new_norm = _normalize(new_text)
    if not new_norm:
        return False
    # Short captions (3 words or less) — only block exact normalized matches
    new_words = set(new_text.lower().split())
    is_short = len(new_words) <= 3
    for existing in existing_list:
        existing_norm = _normalize(existing)
        if not existing_norm:
            continue
        # Exact normalized match — always block
        if new_norm == existing_norm:
            return True
        # Skip fuzzy checks for short captions — too many false positives
        if is_short:
            continue
        # One contains the other
        if new_norm in existing_norm or existing_norm in new_norm:
            return True
        # Word overlap check
        existing_words = set(existing.lower().split())
        if len(new_words) >= 2 and len(existing_words) >= 2:
            overlap = len(new_words & existing_words)
            max_len = max(len(new_words), len(existing_words))
            if overlap / max_len >= threshold:
                return True
    return False


def _deduplicate_script(script):
    """Remove duplicate/similar captions and regenerate title if too similar."""
    history = _load_script_history()

    # Check captions — remove ones too similar to history or each other
    seen_captions = []
    unique_scenes = []
    for scene in script.get("scenes", []):
        caption = scene.get("caption", "")
        if not caption:
            continue
        if _is_too_similar(caption, history.get("captions", [])):
            continue
        if _is_too_similar(caption, seen_captions):
            continue
        seen_captions.append(caption)
        unique_scenes.append(scene)

    script["scenes"] = unique_scenes
    return script


def _record_script(script):
    """Record a generated script's title and captions to history."""
    history = _load_script_history()
    title = script.get("title", "")
    if title and title not in history["titles"]:
        history["titles"].append(title)
    for scene in script.get("scenes", []):
        caption = scene.get("caption", "")
        if caption and caption not in history["captions"]:
            history["captions"].append(caption)
    # Keep last 500 captions and 100 titles to avoid unbounded growth
    history["titles"] = history["titles"][-100:]
    history["captions"] = history["captions"][-500:]
    _save_script_history(history)

# Stock footage keywords that return GOOD-LOOKING clips on Pexels
FOOTAGE_KEYWORDS = [
    # Breeds (Pexels has beautiful breed-specific footage)
    "persian cat", "siamese cat", "maine coon cat", "british shorthair cat",
    "bengal cat", "ragdoll cat", "sphynx cat", "scottish fold cat",
    "orange tabby cat", "black cat", "white cat", "calico cat",
    "grey cat", "fluffy cat", "kitten",

    # Behaviors (cute/interesting — cats only, no humans)
    "cat purring", "cat kneading", "cat stretching", "cat grooming",
    "cat sleeping", "cat playing toy",
    "kitten playing", "cat in sunlight",
    "cat on window", "cat walking", "cat eating",
    "cat and kitten", "two cats cuddling", "cat in garden",
    "cat close up face", "cat eyes", "cat whiskers",
    "cat in bed", "cat on couch", "cute kitten", "newborn kitten",
    "cat tail moving", "cat yawning", "cat sitting", "cat looking",
]


def _call_llm(prompt):
    """Call Groq API and return text response."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=2500,
    )
    return response.choices[0].message.content.strip()


def _parse_json(text):
    """Parse JSON from LLM response, handling code blocks and control chars."""
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # LLM sometimes puts literal newlines/tabs inside JSON strings — fix them
        import re
        text = re.sub(r'(?<!\\)\n', '\\n', text)
        text = re.sub(r'(?<!\\)\t', '\\t', text)
        # Also try stripping any non-JSON prefix/suffix
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end+1]
        return json.loads(text)


def generate_script(content_format=None, video_type="short"):
    """Generate an educational/cute cat video script.

    Each scene = an interesting fact/caption + matching beautiful footage.
    """
    if content_format is None:
        content_format = random.choice(CONTENT_FORMATS)

    scene_count = "12-15" if video_type == "short" else "20-30"

    keyword_sample = random.sample(FOOTAGE_KEYWORDS, min(25, len(FOOTAGE_KEYWORDS)))
    keywords_str = "\n".join(f'- "{k}"' for k in keyword_sample)

    format_guides = {
        "cat_facts": {
            "desc": "Mind-blowing cat facts that make people say 'Wait, REALLY?'",
            "example_captions": [
                "Cats can rotate their ears 180 degrees",
                "A group of cats is called a clowder",
                "Cats sleep 70% of their lives",
                "Cats have over 20 vocalizations",
                "A cats purr vibrates at 25-150 Hz",
            ],
            "title_style": "Cat Facts That Will Blow Your Mind",
        },
        "cat_breeds": {
            "desc": "Showcase the most beautiful/interesting cat breeds",
            "example_captions": [
                "Maine Coon - gentle giants",
                "Bengal - mini leopard",
                "Ragdoll - goes limp when held",
                "Sphynx - not actually hairless",
                "Scottish Fold - those ears though",
            ],
            "title_style": "Most Beautiful Cat Breeds in the World",
        },
        "reasons_to_get_cat": {
            "desc": "Heartwarming reasons why cats are amazing pets",
            "example_captions": [
                "They lower your stress levels",
                "They purr to heal you",
                "Low maintenance compared to dogs",
                "They choose to love you",
                "Built-in alarm clock at 5AM",
            ],
            "title_style": "Reasons You NEED a Cat in Your Life",
        },
        "signs_cat_loves_you": {
            "desc": "How to tell your cat actually loves you (body language)",
            "example_captions": [
                "Slow blinking means I love you",
                "Head bumps = you are mine",
                "Showing their belly = total trust",
                "Kneading on you = pure comfort",
                "Following you everywhere = obsessed",
            ],
            "title_style": "Signs Your Cat Actually Loves You",
        },
        "cat_psychology": {
            "desc": "What cats are actually thinking — behavior explained",
            "example_captions": [
                "Staring at nothing? Hunting mode",
                "Knocking things off? Testing gravity",
                "3AM zoomies? Peak hunting instinct",
                "Ignoring you? Processing emotions",
                "Bringing you gifts? Youre family",
            ],
            "title_style": "What Your Cat Is ACTUALLY Thinking",
        },
        "cat_vs_dog": {
            "desc": "Fun cat vs dog comparison — cats obviously win",
            "example_captions": [
                "Dogs need walks. Cats need naps.",
                "Dogs have owners. Cats have staff.",
                "Dogs fetch. Cats judge.",
                "Dogs beg. Cats demand.",
                "Dogs are loyal. Cats are royalty.",
            ],
            "title_style": "Cat vs Dog - Theres a Clear Winner",
        },
        "cat_myths": {
            "desc": "Common cat myths debunked with real facts",
            "example_captions": [
                "MYTH Cats always land on feet",
                "MYTH Black cats are bad luck",
                "MYTH Cats are antisocial",
                "MYTH Milk is good for cats",
                "MYTH Cats have 9 lives",
            ],
            "title_style": "Cat Myths You Still Believe (DEBUNKED)",
        },
        "cat_tips": {
            "desc": "Useful tips for cat owners — things you wish you knew",
            "example_captions": [
                "Never punish a cat. They dont understand.",
                "Cats need vertical space",
                "Wet food is better than dry",
                "One litter box per cat plus one extra",
                "Slow blink back at your cat",
            ],
            "title_style": "Things I Wish I Knew Before Getting a Cat",
        },
    }

    guide = format_guides.get(content_format, format_guides["cat_facts"])
    examples = "\n".join(f'  - "{c}"' for c in guide["example_captions"])

    # Load past scripts to avoid repetition
    history = _load_script_history()
    avoid_section = ""
    if history["titles"] or history["captions"]:
        avoid_titles = "\n".join(f'  - "{t}"' for t in history["titles"][-20:])
        avoid_captions = "\n".join(f'  - "{c}"' for c in history["captions"][-60:])
        avoid_section = f"""
ALREADY USED — DO NOT repeat, rephrase, or use similar words/structure:
Previous titles (DO NOT use the same key words like "SECRETS", "EXPOSED", "REVEALED", "DEBUNKED" etc.):
{avoid_titles}

Previous captions (DO NOT reuse the same topics — no more purring, whiskers, kneading, eyes, paws unless you have a genuinely NEW angle):
{avoid_captions}

CRITICAL: Every caption and title must be COMPLETELY DIFFERENT from the above — not just reworded. Use different TOPICS and ANGLES, not just different words for the same idea. If the above mentions "purrs heal", do NOT write "purring heals" or "purrfect healers".
"""

    prompt = f"""You are creating a VIRAL educational cat YouTube Short.
These videos get millions of views because people LOVE learning surprising things about cats.

FORMAT: {content_format} — {guide["desc"]}

STYLE:
- Each scene = one SHORT interesting fact/tip as text on screen + beautiful cat footage
- Facts should make viewers go "I didn't know that!" or "Aww that's so cute!"
- Keep captions VERY SHORT — 3 to 5 words MAXIMUM. Never exceed 5 words or 25 characters.
- Mix surprising facts with cute/heartwarming ones
- The video should feel satisfying to watch — beautiful cats + interesting text

EXAMPLE CAPTIONS (match this style):
{examples}
{avoid_section}
AVAILABLE FOOTAGE (you MUST pick search_query from these):
{keywords_str}

RULES:
- Generate exactly {scene_count} scenes
- search_query MUST be copied exactly from the available footage list above
- Use DIFFERENT search_query for each scene — variety is key
- Match the footage to the fact (e.g., fact about purring → "cat purring" footage)
- Title MUST be completely unique and different from previous titles — use different words, angles, and structures each time
- Do NOT reuse words like "DEBUNKED", "FACTS", "MYTHS" if they appear in previous titles
- Title style inspiration: "{guide["title_style"]}" but vary it — try questions, numbers, emotional hooks, "POV:", "Watch till the end", etc.
- Every caption and title MUST be unique — never repeat previous videos

Return ONLY valid JSON:
{{
    "title": "Catchy YouTube title under 60 chars (use CAPS for 1-2 words)",
    "description": "YouTube description: Start with a hook question or statement. Then 1-2 sentences about what the video covers. Then add hashtags at the end: #shorts #cats #catfacts #catlover #catlovers #cute #cutecat #kitten #catlife #cattok #funnycats #catmom #catdad #pets #animals",
    "tags": ["cat facts", "cats", "cute cats", "cat lovers", "shorts", "kitten", "cat tips", "funny cats", "cat behavior", "cat breeds", "cat life", "pets", "animals", "cat mom", "cat dad"],
    "scenes": [
        {{
            "scene_number": 1,
            "caption": "Short interesting fact or tip",
            "search_query": "pick ONE from the available footage list"
        }}
    ],
    "thumbnail_text": "2-4 words that make people click"
}}
"""

    # Try up to 3 times to get enough scenes after dedup
    MIN_SCENES = 8

    for attempt in range(3):
        text = _call_llm(prompt)
        script = _parse_json(text)
        script["content_format"] = content_format
        script["video_type"] = video_type

        # Deduplicate — remove captions too similar to past videos
        script = _deduplicate_script(script)

        scene_count_actual = len(script.get("scenes", []))
        if scene_count_actual >= MIN_SCENES:
            break
        print(f"  Only {scene_count_actual} scenes after dedup (need {MIN_SCENES}), retrying... ({attempt + 1}/3)")

    # Record this script to history so future videos avoid these captions
    _record_script(script)

    return script


def generate_batch(count=7, video_type="short"):
    """Generate multiple unique scripts."""
    scripts = []
    formats = CONTENT_FORMATS.copy()
    random.shuffle(formats)

    for i in range(count):
        fmt = formats[i % len(formats)]
        print(f"  Generating script {i+1}/{count} ({fmt})...")
        try:
            script = generate_script(content_format=fmt, video_type=video_type)
            scripts.append(script)
            print(f"    -> \"{script['title']}\"")
        except Exception as e:
            print(f"    -> Error: {e}")

    return scripts


def generate_title_variations(topic, count=10):
    """Generate multiple title options for A/B testing."""
    prompt = f"""Generate {count} YouTube title variations for a cat video about: {topic}

Return ONLY a JSON array of strings. Each title should:
- Be under 60 characters
- Be interesting/clickable (educational or cute angle)
- Use CAPS for 1-2 emphasis words

Example format: ["Title 1", "Title 2", "Title 3"]
"""

    text = _call_llm(prompt)
    return _parse_json(text)
