"""
Exercise Library — Structured exercises for targeted communication skill building.

Provides a curated set of exercises categorized by skill area, along with
methods to recommend exercises based on identified weaknesses and track completion.
"""

import logging
import random
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Exercise Definitions
# =============================================================================


EXERCISES = [
    # --- Filler Word Elimination ---
    {
        "id": "filler_01",
        "type": "filler_elimination",
        "skill": "filler_words",
        "title": "The Silent Pause",
        "prompt": (
            "Describe your morning routine from waking up to leaving home. "
            "Challenge: replace every urge to say 'um' or 'like' with a silent 2-second pause. "
            "A confident pause is more powerful than any filler word."
        ),
        "time_limit": 60,
        "difficulty": "beginner",
    },
    {
        "id": "filler_02",
        "type": "filler_elimination",
        "skill": "filler_words",
        "title": "News Anchor",
        "prompt": (
            "Pretend you're a news anchor delivering today's top 3 headlines. "
            "Speak clearly and smoothly with zero filler words. "
            "News anchors never say 'um' — neither will you."
        ),
        "time_limit": 90,
        "difficulty": "intermediate",
    },
    {
        "id": "filler_03",
        "type": "filler_elimination",
        "skill": "filler_words",
        "title": "Filler Word Sprint",
        "prompt": (
            "I'll give you a random topic and you must speak about it for 60 seconds "
            "with absolutely no filler words. Ready? Your topic: "
            "Why is breakfast the most important meal of the day?"
        ),
        "time_limit": 60,
        "difficulty": "advanced",
    },

    # --- Pace Control ---
    {
        "id": "pace_01",
        "type": "pace_control",
        "skill": "pace",
        "title": "Recipe Walk-Through",
        "prompt": (
            "Explain how to make your favorite meal, step by step. "
            "Speak slowly and clearly — imagine the listener is writing down every word. "
            "Take a breath between each step."
        ),
        "time_limit": 90,
        "difficulty": "beginner",
    },
    {
        "id": "pace_02",
        "type": "pace_control",
        "skill": "pace",
        "title": "Storyteller's Rhythm",
        "prompt": (
            "Tell a story about something memorable that happened to you. "
            "Vary your pace: slow down for important moments, speed up slightly "
            "for exciting parts, and pause before key reveals."
        ),
        "time_limit": 120,
        "difficulty": "intermediate",
    },
    {
        "id": "pace_03",
        "type": "pace_control",
        "skill": "pace",
        "title": "The Metronome",
        "prompt": (
            "Count to 10 slowly, taking 2 seconds per number. "
            "Now, explain your favorite hobby at that same measured pace. "
            "Each sentence should feel deliberate and unhurried."
        ),
        "time_limit": 60,
        "difficulty": "beginner",
    },

    # --- Confidence Building ---
    {
        "id": "conf_01",
        "type": "confidence_building",
        "skill": "hedging",
        "title": "Opinion Ownership",
        "prompt": (
            "State three opinions you hold strongly. For each one, "
            "start with 'I believe...' and give one clear reason why. "
            "No hedging — no 'I think maybe', no 'I guess', no 'sort of'. "
            "Own every word."
        ),
        "time_limit": 90,
        "difficulty": "beginner",
    },
    {
        "id": "conf_02",
        "type": "confidence_building",
        "skill": "hedging",
        "title": "The Bold Pitch",
        "prompt": (
            "You have a brilliant invention that will change the world. "
            "Pitch it to me in 60 seconds with absolute conviction. "
            "Speak as if you have zero doubt this will succeed."
        ),
        "time_limit": 60,
        "difficulty": "intermediate",
    },
    {
        "id": "conf_03",
        "type": "confidence_building",
        "skill": "hedging",
        "title": "Disagree Respectfully",
        "prompt": (
            "I'll state an opinion: 'Working from home is always better than being in an office.' "
            "Disagree with me clearly and respectfully. "
            "Use 'I believe', 'Here's why', 'The evidence shows' — not 'maybe' or 'I guess'."
        ),
        "time_limit": 90,
        "difficulty": "advanced",
    },

    # --- Vocabulary Expansion ---
    {
        "id": "vocab_01",
        "type": "vocabulary_expansion",
        "skill": "vocabulary",
        "title": "Forbidden Words",
        "prompt": (
            "Describe your favorite place without using these words: "
            "nice, good, great, really, very, amazing, awesome. "
            "Find more specific, vivid, descriptive alternatives."
        ),
        "time_limit": 60,
        "difficulty": "beginner",
    },
    {
        "id": "vocab_02",
        "type": "vocabulary_expansion",
        "skill": "vocabulary",
        "title": "Synonym Swap",
        "prompt": (
            "I'll say a simple sentence: 'The food was good and the place was nice.' "
            "Now say the same thing 3 different ways, each time using completely "
            "different words. Make each version more vivid than the last."
        ),
        "time_limit": 60,
        "difficulty": "intermediate",
    },

    # --- Clarity & Structure ---
    {
        "id": "clarity_01",
        "type": "clarity",
        "skill": "clarity",
        "title": "The Elevator Pitch",
        "prompt": (
            "You're in an elevator with someone important. "
            "Introduce yourself and explain what you do in exactly 30 seconds. "
            "Be clear, concise, and memorable. Go!"
        ),
        "time_limit": 30,
        "difficulty": "beginner",
    },
    {
        "id": "clarity_02",
        "type": "clarity",
        "skill": "clarity",
        "title": "Explain Like I'm Five",
        "prompt": (
            "Pick something complex from your work or studies "
            "(a concept, process, or technology). Now explain it to me "
            "as if I'm 5 years old. Use simple words, analogies, and examples."
        ),
        "time_limit": 90,
        "difficulty": "intermediate",
    },
    {
        "id": "clarity_03",
        "type": "clarity",
        "skill": "clarity",
        "title": "One Sentence Summary",
        "prompt": (
            "Think of a book, movie, or show you love. "
            "Summarize it in exactly one sentence that makes someone want to watch/read it. "
            "Then expand that into a 30-second recommendation."
        ),
        "time_limit": 45,
        "difficulty": "beginner",
    },

    # --- Role Play ---
    {
        "id": "role_01",
        "type": "role_play",
        "skill": "situational",
        "title": "Job Interview: Tell Me About Yourself",
        "prompt": (
            "Imagine you're in a job interview. I just asked: "
            "'Tell me about yourself.' Give a 60-second answer that covers "
            "who you are, what you do, and why you're interested in this role."
        ),
        "time_limit": 60,
        "difficulty": "intermediate",
    },
    {
        "id": "role_02",
        "type": "role_play",
        "skill": "situational",
        "title": "Constructive Feedback",
        "prompt": (
            "Your colleague gave a presentation that had good content but "
            "was poorly delivered — too many slides, they read from notes, "
            "and went over time. Give them constructive feedback that's "
            "honest but encouraging. Use the compliment sandwich."
        ),
        "time_limit": 90,
        "difficulty": "advanced",
    },
    {
        "id": "role_03",
        "type": "role_play",
        "skill": "situational",
        "title": "Networking Intro",
        "prompt": (
            "You're at a networking event and someone asks 'What do you do?' "
            "Give an engaging answer that goes beyond just your job title. "
            "Make it interesting enough that they want to keep talking to you."
        ),
        "time_limit": 45,
        "difficulty": "beginner",
    },

    # --- Active Listening ---
    {
        "id": "listen_01",
        "type": "active_listening",
        "skill": "listening",
        "title": "Summarize Back",
        "prompt": (
            "I'm going to tell you a short story about my weekend. "
            "Your job is to listen carefully and then summarize back the "
            "key points in your own words. Ready? Here goes: "
            "I went to a farmers market on Saturday morning, tried fresh honey "
            "from a local beekeeper, bought way too many vegetables, then spent "
            "the afternoon cooking a huge meal for friends who came over for dinner."
        ),
        "time_limit": 45,
        "difficulty": "beginner",
    },

    # --- Eye Contact & Body Language ---
    {
        "id": "body_01",
        "type": "body_language",
        "skill": "eye_contact",
        "title": "Camera Eye Lock",
        "prompt": (
            "Tell a 2-minute story about something that happened to you recently. "
            "Keep your eyes on the camera the entire time — pretend it's a person "
            "you're having a one-on-one conversation with."
        ),
        "time_limit": 120,
        "difficulty": "beginner",
    },
    {
        "id": "body_02",
        "type": "body_language",
        "skill": "posture",
        "title": "Power Posture Pitch",
        "prompt": (
            "Sit up straight, relax your shoulders, plant both feet on the floor, "
            "and take three deep breaths. Now — with that confident posture — "
            "pitch me an idea for 60 seconds. Let your body support your words."
        ),
        "time_limit": 60,
        "difficulty": "beginner",
    },
]


# =============================================================================
# Exercise Library class
# =============================================================================


class ExerciseLibrary:
    """Manages the exercise catalog and provides recommendations."""

    def __init__(self):
        self._exercises = {ex["id"]: ex for ex in EXERCISES}

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all exercises."""
        return EXERCISES.copy()

    def get_by_id(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Return a specific exercise by ID."""
        return self._exercises.get(exercise_id)

    def get_by_skill(self, skill: str) -> List[Dict[str, Any]]:
        """Return all exercises for a specific skill."""
        return [ex for ex in EXERCISES if ex["skill"] == skill]

    def get_by_type(self, exercise_type: str) -> List[Dict[str, Any]]:
        """Return all exercises of a specific type."""
        return [ex for ex in EXERCISES if ex["type"] == exercise_type]

    def get_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        """Return all exercises at a specific difficulty level."""
        return [ex for ex in EXERCISES if ex["difficulty"] == difficulty]

    def recommend_for_weaknesses(
        self, weaknesses: List[str], count: int = 3
    ) -> List[Dict[str, Any]]:
        """Recommend exercises based on identified weaknesses.

        Args:
            weaknesses: List of weakness descriptions (from session analysis).
            count: Number of exercises to recommend.

        Returns:
            List of recommended exercises.
        """
        # Map weakness keywords to skills
        skill_map = {
            "filler": "filler_words",
            "um": "filler_words",
            "like": "filler_words",
            "pace": "pace",
            "fast": "pace",
            "slow": "pace",
            "speed": "pace",
            "hedging": "hedging",
            "confidence": "hedging",
            "conviction": "hedging",
            "maybe": "hedging",
            "guess": "hedging",
            "vocabulary": "vocabulary",
            "vocab": "vocabulary",
            "words": "vocabulary",
            "clarity": "clarity",
            "structure": "clarity",
            "concise": "clarity",
            "eye contact": "eye_contact",
            "posture": "posture",
            "body language": "posture",
        }

        # Identify relevant skills
        target_skills = set()
        for weakness in weaknesses:
            weakness_lower = weakness.lower()
            for keyword, skill in skill_map.items():
                if keyword in weakness_lower:
                    target_skills.add(skill)

        if not target_skills:
            # Default to a mix
            target_skills = {"filler_words", "clarity", "hedging"}

        # Gather matching exercises
        candidates = [
            ex for ex in EXERCISES if ex["skill"] in target_skills
        ]

        # If not enough, add random from other skills
        if len(candidates) < count:
            others = [ex for ex in EXERCISES if ex["skill"] not in target_skills]
            candidates.extend(random.sample(others, min(count - len(candidates), len(others))))

        # Select up to count
        if len(candidates) > count:
            candidates = random.sample(candidates, count)

        return candidates

    def get_random(self, count: int = 1) -> List[Dict[str, Any]]:
        """Return random exercises."""
        return random.sample(EXERCISES, min(count, len(EXERCISES)))
