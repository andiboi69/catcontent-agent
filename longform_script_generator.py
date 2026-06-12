"""
Long-Form Script Generator — Creates 8-10 minute educational cat video scripts.
Structured with chapters, longer narrations, and YouTube-optimized descriptions.
Reuses dedup system from script_generator.py.
"""

import random
from groq import Groq
from config import GROQ_API_KEY
from longform_config import LONGFORM_CONTENT_FORMATS, LONGFORM_SCENE_COUNT
from script_generator import (
    _call_llm, _parse_json,
    _load_script_history, _deduplicate_script, _record_script,
    FOOTAGE_KEYWORDS,
)


def generate_longform_script(content_format=None):
    """Generate a structured long-form cat video script (8-10 min).

    Returns a script dict with chapters and 25-30 scenes.
    """
    if content_format is None:
        content_format = random.choice(LONGFORM_CONTENT_FORMATS)

    keyword_sample = random.sample(FOOTAGE_KEYWORDS, min(25, len(FOOTAGE_KEYWORDS)))
    keywords_str = "\n".join(f'- "{k}"' for k in keyword_sample)

    format_guides = {
        "cat_facts": {
            "desc": "25-30 mind-blowing cat facts organized into themed chapters",
            "chapter_hint": "Group facts into chapters like: Body, Senses, Behavior, Intelligence, History",
        },
        "cat_breeds": {
            "desc": "Deep dive into the most fascinating cat breeds in the world",
            "chapter_hint": "Group by: Large Breeds, Exotic Breeds, Rare Breeds, Most Popular, Unique Traits",
        },
        "reasons_to_get_cat": {
            "desc": "Comprehensive reasons why cats make the best pets",
            "chapter_hint": "Group by: Health Benefits, Emotional Support, Practical Advantages, Fun Facts, Lifestyle",
        },
        "signs_cat_loves_you": {
            "desc": "Complete guide to understanding your cat's love language",
            "chapter_hint": "Group by: Body Language, Sounds, Actions, Habits, Subtle Signs",
        },
        "cat_psychology": {
            "desc": "Deep dive into what cats are actually thinking and feeling",
            "chapter_hint": "Group by: Hunting Instinct, Social Behavior, Memory, Emotions, Communication",
        },
        "cat_vs_dog": {
            "desc": "Epic comprehensive comparison — cats vs dogs across every category",
            "chapter_hint": "Group by: Intelligence, Independence, Health, Senses, Loyalty, Fun Factor",
        },
        "cat_myths": {
            "desc": "Every major cat myth debunked with real science",
            "chapter_hint": "Group by: Health Myths, Behavior Myths, History Myths, Ability Myths, Superstitions",
        },
        "cat_tips": {
            "desc": "Complete guide for cat owners — everything you wish you knew",
            "chapter_hint": "Group by: Diet, Health, Environment, Play, Bonding, Common Mistakes",
        },
        "cat_history": {
            "desc": "The incredible 10,000-year history of cats and humans",
            "chapter_hint": "Group by: Ancient Egypt, Medieval Era, Cats at Sea, Modern Domestication, Cats in Culture",
        },
        "cat_science": {
            "desc": "The science behind cat behavior explained",
            "chapter_hint": "Group by: Senses, Brain, Genetics, Evolution, Physics of Cats",
        },
        "cat_breeds_deep": {
            "desc": "Complete guide to the world's most interesting cat breeds",
            "chapter_hint": "Group by: Origin Stories, Physical Traits, Personality, Rarity, Best For Families",
        },
        "cat_communication": {
            "desc": "How cats actually communicate with humans and each other",
            "chapter_hint": "Group by: Vocalizations, Tail Language, Eye Contact, Scent Marking, Touch",
        },
    }

    guide = format_guides.get(content_format, format_guides["cat_facts"])

    # Load history for dedup
    history = _load_script_history()
    avoid_section = ""
    if history["titles"] or history["captions"] or history.get("narrations"):
        avoid_titles = "\n".join(f'  - "{t}"' for t in history["titles"][-20:])
        avoid_captions = "\n".join(f'  - "{c}"' for c in history["captions"][-30:])
        avoid_narrations = "\n".join(f'  - "{n}"' for n in history.get("narrations", [])[-30:])
        avoid_section = f"""
ALREADY USED — DO NOT repeat or rephrase:
Previous titles:
{avoid_titles}

Previous captions:
{avoid_captions}

Previous narrations:
{avoid_narrations}

Every fact must be COMPLETELY DIFFERENT from the above.
"""

    narration_styles = [
        "conversational and engaging, like a popular science YouTuber explaining cool facts to friends",
        "calm and authoritative, like a nature documentary narrator (think David Attenborough but casual)",
        "enthusiastic and energetic, like a passionate cat expert sharing their favorite discoveries",
    ]
    narration_style = random.choice(narration_styles)

    prompt = f"""You are creating a LONG-FORM educational cat YouTube video (8-10 minutes).
These videos earn ad revenue and get recommended by YouTube's algorithm for their depth and watch time.

FORMAT: {content_format} — {guide["desc"]}

STRUCTURE:
- Organize into 5-6 CHAPTERS with clear chapter titles
- Each chapter has 4-6 scenes
- Total: {LONGFORM_SCENE_COUNT} scenes
- Each scene has:
  * "caption": 3-6 words shown ON SCREEN (short, punchy)
  * "narration": 45-60 words for VOICEOVER — 3 complete sentences that explore the fact in depth: state it, explain WHY, add a vivid detail or example. COUNT THE WORDS — narrations under 45 words make the video too short. Must sound natural when spoken aloud. (This narration length is what makes the video reach 8+ minutes.)
  * "search_query": footage keyword from the available list
  * "chapter": which chapter this scene belongs to (string)
- ONLY the first scene has chapter "intro" and ONLY the last scene has chapter "outro" — every other scene MUST be assigned to one of the content chapters

CHAPTER STRUCTURE HINT: {guide["chapter_hint"]}

NARRATION STYLE: {narration_style}
- NEVER start with filler like "Did you know", "Get this", "You won't believe"
- Just STATE the fact directly and make it interesting
- Each narration should flow naturally to the next — the viewer should want to keep watching
- Vary sentence structure — don't start every narration the same way

FACTS:
- Every fact MUST be real and accurate
- Go DEEP — not surface-level facts everyone knows
- Mix surprising science with heartwarming observations
- Include specific numbers and studies where possible
{avoid_section}
AVAILABLE FOOTAGE (pick search_query from these):
{keywords_str}

RULES:
- Generate exactly {LONGFORM_SCENE_COUNT} scenes
- search_query MUST be from the available list — use DIFFERENT ones for each scene
- Title should be compelling for a long-form video (not Shorts style)
- Description should include chapter timestamps (e.g., "0:00 Intro")
- Do NOT include #shorts anywhere
- Tags should be relevant to long-form cat content

Return ONLY valid JSON:
{{
    "title": "Compelling long-form title under 70 chars (use CAPS for 1-2 key words)",
    "description": "YouTube description with hook + chapter timestamps + hashtags (NO #shorts)",
    "tags": ["cat facts", "cats", "cat documentary", "cat behavior", "cat science", "pets", "animals", "cat breeds", "cat tips", "educational"],
    "chapters": ["Intro", "Chapter 1 Title", "Chapter 2 Title", "Chapter 3 Title", "Chapter 4 Title", "Chapter 5 Title", "Outro"],
    "scenes": [
        {{
            "scene_number": 1,
            "caption": "3-6 word fact for screen",
            "narration": "Full sentence 15-25 words for voiceover",
            "search_query": "pick from available footage list",
            "chapter": "Intro"
        }}
    ],
    "thumbnail_text": "2-4 words that make people click"
}}
"""

    # Long-form needs more tokens
    client = Groq(api_key=GROQ_API_KEY)
    MODEL = "llama-3.3-70b-versatile"

    MIN_SCENES = 25

    for attempt in range(3):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=8000,
        )
        text = response.choices[0].message.content.strip()
        script = _parse_json(text)
        script["content_format"] = content_format
        script["video_type"] = "longform"

        # Deduplicate
        script = _deduplicate_script(script)

        scene_count = len(script.get("scenes", []))
        if scene_count >= MIN_SCENES:
            break
        print(f"  Only {scene_count} scenes after dedup (need {MIN_SCENES}), retrying... ({attempt + 1}/3)")

    # Record to history
    _record_script(script)

    return script
