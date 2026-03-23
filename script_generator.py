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
FUNNY_MODEL = "qwen/qwen3-32b"

# Script history file — persists across all generations
SCRIPT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "used_scripts.json")


def _load_script_history():
    """Load list of previously generated titles, captions, and narrations."""
    if os.path.exists(SCRIPT_HISTORY_FILE):
        try:
            with open(SCRIPT_HISTORY_FILE, "r") as f:
                data = json.load(f)
                # Ensure narrations key exists (backward compat)
                if "narrations" not in data:
                    data["narrations"] = []
                return data
        except Exception:
            pass
    return {"titles": [], "captions": [], "narrations": []}


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


def _is_too_similar(new_text, existing_list, threshold=0.8):
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

    # Check captions AND narrations — remove scenes too similar to history or each other
    seen_captions = []
    seen_narrations = []
    unique_scenes = []
    for scene in script.get("scenes", []):
        caption = scene.get("caption", "")
        narration = scene.get("narration", "")
        if not caption:
            continue
        # Check caption against history and current batch
        if _is_too_similar(caption, history.get("captions", [])):
            continue
        if _is_too_similar(caption, seen_captions):
            continue
        # Check narration against history and current batch
        if narration and _is_too_similar(narration, history.get("narrations", []), threshold=0.6):
            continue
        if narration and _is_too_similar(narration, seen_narrations, threshold=0.6):
            continue
        seen_captions.append(caption)
        if narration:
            seen_narrations.append(narration)
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
        narration = scene.get("narration", "")
        if caption and caption not in history["captions"]:
            history["captions"].append(caption)
        if narration and narration not in history["narrations"]:
            history["narrations"].append(narration)
    # Keep last N entries to avoid unbounded growth
    history["titles"] = history["titles"][-100:]
    history["captions"] = history["captions"][-200:]
    history["narrations"] = history["narrations"][-200:]
    _save_script_history(history)

# Stock footage keywords — calm for educational, action for funny
FOOTAGE_KEYWORDS_CALM = [
    # Breeds
    "persian cat", "siamese cat", "maine coon cat", "british shorthair cat",
    "bengal cat", "ragdoll cat", "sphynx cat", "scottish fold cat",
    "orange tabby cat", "black cat", "white cat", "calico cat",
    "grey cat", "fluffy cat", "kitten",
    # Calm behaviors
    "cat purring", "cat kneading", "cat stretching", "cat grooming",
    "cat sleeping", "cat in sunlight", "cat on window", "cat eating",
    "cat and kitten", "two cats cuddling", "cat in garden",
    "cat close up face", "cat eyes", "cat whiskers",
    "cat in bed", "cat on couch", "cute kitten", "newborn kitten",
    "cat tail moving", "cat yawning", "cat sitting", "cat looking",
]

FOOTAGE_KEYWORDS_FUNNY = [
    # Action/funny behaviors
    "funny cat", "cat jumping", "cat running", "cat chasing",
    "cat playing toy", "kitten playing", "cat scared", "cat surprised",
    "crazy cat", "cat zoomies", "cat knocking things", "clumsy cat",
    "cat falling", "cat box", "cat stuck", "cat vs cucumber",
    "cat hissing", "cat walking", "cat fail", "cat jump fail",
    # Still need some cute ones for variety
    "cat close up face", "cat eyes", "fluffy cat", "kitten",
    "orange tabby cat", "cat yawning", "cat stretching",
]

# Default — used in prompt (overridden per format below)
FOOTAGE_KEYWORDS = FOOTAGE_KEYWORDS_CALM


def _call_llm(prompt, model=None):
    """Call Groq API and return text response."""
    import re
    use_model = model or MODEL
    # Qwen3 uses tokens for thinking, so give it more room
    max_tok = 8000 if use_model == FUNNY_MODEL else 2500
    response = client.chat.completions.create(
        model=use_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=max_tok,
    )
    text = response.choices[0].message.content.strip()
    # Qwen3 wraps responses in <think>...</think> tags — strip them
    text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
    # Also handle unclosed think tags
    if '<think>' in text:
        text = text.split('</think>')[-1].strip()
        if not text:
            text = re.sub(r'<think>.*', '', response.choices[0].message.content, flags=re.DOTALL).strip()
    return text


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

    # Funny = fewer scenes (voiceover adds time), educational = more scenes (text-only, fast)
    if content_format == "funny_cat_facts":
        scene_count = "5" if video_type == "short" else "20-30"
    else:
        scene_count = "6-7" if video_type == "short" else "20-30"

    keyword_pool = FOOTAGE_KEYWORDS_FUNNY if content_format == "funny_cat_facts" else FOOTAGE_KEYWORDS_CALM
    keyword_sample = random.sample(keyword_pool, min(25, len(keyword_pool)))
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
        "funny_cat_facts": {
            "desc": "COMEDY cat facts — deliver real facts in the funniest possible way. Think Twitter memes, TikTok humor, stand-up comedy. The fact is real but the delivery is HILARIOUS.",
            "example_captions": [
                "Sleeps 16hrs. Judges you 8.",
                "Headbutts you. Means MINE.",
                "Group of cats? A clowder. WHY.",
                "Cant taste sweet. Explains the attitude.",
                "Cat was MAYOR. 20 years. Legend.",
                "Purrs to heal YOU. Still scratches.",
                "3AM zoomies. Every. Single. Night.",
                "Brings you dead mouse. Youre welcome.",
                "Knocks stuff off table. For science.",
                "Fits in any box. Its the law.",
            ],
            "title_style": "Your Cat Is SCAMMING You",
        },
    }

    guide = format_guides.get(content_format, format_guides["cat_facts"])
    examples = "\n".join(f'  - "{c}"' for c in guide["example_captions"])

    # Load past scripts to avoid repetition
    history = _load_script_history()
    avoid_section = ""
    if history["titles"] or history["captions"] or history.get("narrations"):
        avoid_titles = "\n".join(f'  - "{t}"' for t in history["titles"][-20:])
        avoid_captions = "\n".join(f'  - "{c}"' for c in history["captions"][-30:])
        avoid_narrations = "\n".join(f'  - "{n}"' for n in history.get("narrations", [])[-30:])
        avoid_section = f"""
ALREADY USED — DO NOT repeat, rephrase, or use similar words/structure:
Previous titles (DO NOT use the same key words like "SECRETS", "EXPOSED", "REVEALED", "DEBUNKED" etc.):
{avoid_titles}

Previous captions (DO NOT reuse the same topics — no more purring, whiskers, kneading, eyes, paws unless you have a genuinely NEW angle):
{avoid_captions}

Previous narrations (DO NOT repeat these facts or rephrase them — find COMPLETELY NEW information):
{avoid_narrations}

CRITICAL: Every caption, narration, and title must be COMPLETELY DIFFERENT from the above — not just reworded. Use different TOPICS and ANGLES, not just different words for the same idea. If the above mentions "purrs heal", do NOT write "purring heals" or "purrfect healers". If a narration says "cats can hear 64,000 hertz", do NOT write "cats hear up to 64 kHz" — find a DIFFERENT fact entirely.
"""

    # Rotate title formulas — pick one randomly each time
    if content_format == "funny_cat_facts":
        title_formulas = [
            'Roast: "Your Cat Is SCAMMING You" / "Cats Are Professional FREELOADERS" / "Your Cat Has ZERO Respect For You"',
            'POV comedy: "POV Your Cat at 3AM" / "POV You Bought a CAT" / "POV Your Cat Runs the House"',
            'Relatable: "Every Cat Owner FELT This" / "Living With a Cat Be Like..." / "Cat Owners Will CRY Laughing"',
            'Expose: "EXPOSING Your Cats Secret Life" / "Your Cat Is LYING To You" / "What Your Cat REALLY Thinks"',
            'Sarcastic: "Cats Are SO Helpful" / "Thanks For Nothing CAT" / "My Cat Does NOTHING And I Love It"',
            'Dramatic: "The AUDACITY of Cats" / "Cats Have ZERO Shame" / "Your Cat Is a DRAMA Queen"',
        ]
    else:
        title_formulas = [
            'Curiosity gap: "Nobody Told You THIS About Cats" / "Your Cat Does This BUT You Never Noticed" / "What Happens When Cats..."',
            'Emotional hook: "This Is Why CATS Are Therapists" / "Cats That Will MELT Your Heart" / "The Reason Cats Choose YOU"',
            'Challenge: "Only 1% of Cat Owners Know This" / "Bet You Didn\'t Know CATS Can..." / "Name All 5 Cat Breeds"',
            'Question: "Why Do CATS Do This?" / "Is Your Cat Trying To WARN You?" / "What Does Your Cat SEE At Night?"',
            'Shock/reaction: "I Can\'t Believe CATS Can Do This" / "When Your Cat Does THIS... Watch Out" / "Scientists STUNNED By Cats"',
            'POV/relatable: "POV Your Cat At 3AM" / "Every Cat Owner Knows This FEELING" / "Living With a Cat Be Like"',
            'Number hook: "5 Things Your CAT Wishes You Knew" / "3 Cat Breeds That Act Like DOGS" / "7 Signs Your Cat Is HAPPY"',
        ]
    title_formula = random.choice(title_formulas)

    # Rotate narration styles for variety
    if content_format == "funny_cat_facts":
        narration_styles = [
            "hilarious, like a comedian roasting cats with love. Short punchy delivery.",
            "sarcastic and witty, like a cat would talk if it could. Deadpan humor.",
            "excited and goofy, like you just found out the funniest thing about cats ever",
        ]
    else:
        narration_styles = [
            "conversational, like telling a friend a cool fact. Jump straight into the fact — NO filler phrases like 'did you know' or 'here's the thing'",
            "calm and educational, like a nature documentary narrator stating facts directly",
            "enthusiastic and energetic, but lead with the actual fact — NO setup phrases like 'get this' or 'you won't believe this' or 'this one is wild'",
        ]
    narration_style = random.choice(narration_styles)

    # Funny format gets a completely different prompt tone
    if content_format == "funny_cat_facts":
        tone_section = f"""You are creating a VIRAL FUNNY cat YouTube Short.
These videos go viral because they make people LAUGH while learning something real about cats.
The tone is COMEDY FIRST, facts second. Think memes, not textbooks.

FORMAT: {content_format} — {guide["desc"]}

STYLE:
- Each scene = one FUNNY cat fact as text on screen + cute cat footage
- Each scene has TWO text fields:
  * "caption": 3-6 words shown ON SCREEN — funny, sarcastic, meme-like. Examples: "Sleeps 16hrs. Judges you 8." / "Knocks stuff off. For science." / "3AM zoomies. Every. Night."
  * "narration": 15-18 words for VOICEOVER — setup + punchline in one sentence. Must be FUNNY, not just factual.
    Every narration needs a PUNCHLINE — the funny part at the end that makes viewers think "so true!"
    EXAMPLES (notice each has setup + punchline):
    - "Cats can ignore you for hours but the second you get on a phone call they demand attention"
    - "Cats shed on everything you own and somehow it is always on the one black shirt you need"
    - "They steal your warm spot the second you stand up and act like they were always there"
    - "Cats will stare at a wall for twenty minutes and make you question your own sanity"
    - "They bring you a dead mouse at 3am like it is a five star gift and expect praise"
    RULES for narration:
    - Structure: SETUP (relatable cat behavior) + PUNCHLINE (why it is funny/annoying for the owner)
    - Write like a cat owner venting about their ridiculous cat
    - The punchline must be RELATABLE — viewers should think "my cat does that too!"
    - BANNED phrases: "like a little", "like a feline", "basically making them", "which is", "allowing them to"
    - NO technical facts disguised as jokes. NO dad jokes. NO fake percentages
    - Good: "Cats can ignore you for hours but the second you get on a phone call they demand attention"
    - Good: "Cats shed fur on everything you own and somehow it is always on the one black shirt you need"
    - Bad: "Cats have 530 bones, clearly a superiority complex" — this is a dad joke, do NOT do this
    - Bad: "Cats have paws covering 30% of their body for grip" — this is a textbook fact, NOT funny
    - Narration tone: {narration_style}
- Title must be FUNNY like a meme, not a documentary
- GOOD titles: "Your Cat Is SCAMMING You", "Cats Are Professional FREELOADERS", "The AUDACITY of Cats", "Your Cat Has ZERO Respect For You"
- BAD titles (too boring): "CATS Are Little Therapists", "Cat Facts You Should Know", "CATS Are Tiny Dictators", "CATS Are MASTER Manipulators\""""
    else:
        tone_section = f"""You are creating a VIRAL educational cat YouTube Short.
These videos get millions of views because people LOVE learning surprising things about cats.

FORMAT: {content_format} — {guide["desc"]}

STYLE:
- Each scene = one SHORT surprising fact as text on screen + beautiful cat footage
- Each scene has TWO text fields:
  * "caption": 3-6 words shown ON SCREEN — short, punchy, eye-catching (e.g. "Cats hear ultrasonic")
  * "narration": 8-15 words read by VOICEOVER — a full interesting sentence expanding the caption (e.g. "Cats can hear ultrasonic frequencies up to 64,000 hertz, way beyond human range")
- The narration should feel like someone explaining a cool fact to a friend
- Narration tone: {narration_style}"""

    prompt = f"""{tone_section}
- NEVER start narration with filler phrases like: "Get this", "You won't believe", "This is interesting", "This one is wild", "Here's the thing", "Did you know", "Fun fact". Just STATE the fact directly. Example: instead of "Get this, cats can rotate their ears 180 degrees" just say "Cats can rotate their ears a full 180 degrees independently"
- Captions MUST contain a SPECIFIC fact — NOT generic labels like "Sleep Patterns" or "Grooming Habits"
- Facts MUST be real and accurate — do NOT make up numbers. If unsure, use a qualitative fact instead of a fake number
- Mix mind-blowing facts with cute/heartwarming ones
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
- Do NOT reuse words like "DEBUNKED", "FACTS", "MYTHS", "SECRETS", "REVEALED", "EXPOSED", "DOMINATE" if they appear in previous titles
- TITLE FORMULA — you MUST use this specific formula for this video:
  {title_formula}
- AVOID generic titles like "CATS ROCK", "CAT LOVE", "CATS Win", "CATS Have Hidden Talents" — these get the LEAST views
- The title should make someone STOP scrolling and click
- Every caption and title MUST be unique — never repeat previous videos

Return ONLY valid JSON:
{{
    "title": "Curiosity-driven title under 60 chars — make them STOP scrolling (use CAPS for 1-2 key words)",
    "description": "YouTube description: Start with a hook question or statement. Then 1-2 sentences about what the video covers. Then add hashtags at the end: #shorts #cats #catfacts #catlover #catlovers #cute #cutecat #kitten #catlife #cattok #funnycats #catmom #catdad #pets #animals",
    "tags": ["cat facts", "cats", "cute cats", "cat lovers", "shorts", "kitten", "cat tips", "funny cats", "cat behavior", "cat breeds", "cat life", "pets", "animals", "cat mom", "cat dad"],
    "scenes": [
        {{
            "scene_number": 1,
            "caption": "3-6 word fact for screen",
            "narration": "Full sentence 8-15 words for voiceover — expand the caption with detail",
            "search_query": "pick ONE from the available footage list"
        }}
    ],
    "thumbnail_text": "2-4 words that make people click"
}}
"""

    # Try up to 3 times to get enough scenes after dedup
    MIN_SCENES = 4

    # Use Qwen3 for funny format (Llama can't do humor consistently)
    llm_model = FUNNY_MODEL if content_format == "funny_cat_facts" else None

    for attempt in range(3):
        text = _call_llm(prompt, model=llm_model)
        script = _parse_json(text)
        script["content_format"] = content_format
        script["video_type"] = video_type

        # Deduplicate — remove captions too similar to past videos
        script = _deduplicate_script(script)

        scene_count_actual = len(script.get("scenes", []))
        if scene_count_actual >= MIN_SCENES:
            break
        print(f"  Only {scene_count_actual} scenes after dedup (need {MIN_SCENES}), retrying... ({attempt + 1}/3)")

    # Trim narrations — Qwen3 can't count words, so enforce max length in code
    if content_format == "funny_cat_facts":
        MAX_NARRATION_WORDS = 18
        for scene in script.get("scenes", []):
            narration = scene.get("narration", "")
            words = narration.split()
            if len(words) > MAX_NARRATION_WORDS:
                # Cut at last natural break (comma, period, "then", "and", "but") before limit
                trimmed = " ".join(words[:MAX_NARRATION_WORDS])
                for sep in [", then ", ", and ", ", but ", ", ", ". "]:
                    if sep in trimmed:
                        trimmed = trimmed[:trimmed.rfind(sep)]
                        break
                scene["narration"] = trimmed

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
