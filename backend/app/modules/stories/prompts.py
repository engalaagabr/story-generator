"""Story-specific instructions and their provider-neutral prompt builder."""

import json

from app.modules.stories.generation_schemas import GeneratedStory

STORY_PROMPT = """
You are a creative story writer that creates engaging choose-your-own-adventure stories.
Generate a complete branching story with multiple paths and endings in the JSON format I'll specify.

The story should have:
1. A compelling title
2. A starting situation (root node) with 2-3 options
3. Each option should lead to another node with its own options
4. Some paths should lead to endings (both winning and losing)
5. At least one path should lead to a winning ending

Story structure requirements:
- Each node should have 2-3 options except for ending nodes
- The story should be 3-4 levels deep (including root node)
- Add variety in the path lengths (some end earlier, some later)
- Make sure there's at least one winning path

Output your story in this exact JSON structure:
{format_instructions}

Don't simplify or omit any part of the story structure.
Don't add any text outside of the JSON structure.
"""

EXAMPLE_STORY = {
    "title": "The Moonlit Gate",
    "root_node_id": 1,
    "nodes": [
        {
            "id": 1,
            "content": "A silver gate stands between you and the lost village.",
            "is_ending": False,
            "is_winning_ending": False,
            "options": [
                {"text": "Ask the gatekeeper for help", "node_id": 2},
                {"text": "Cross the broken bridge", "node_id": 3},
            ],
        },
        {
            "id": 2,
            "content": "The gatekeeper offers a lantern and points to two paths.",
            "is_ending": False,
            "is_winning_ending": False,
            "options": [
                {"text": "Follow the lantern-lit path", "node_id": 4},
                {"text": "Take the unmarked shortcut", "node_id": 5},
            ],
        },
        {
            "id": 3,
            "content": "The bridge gives way and you must abandon your journey.",
            "is_ending": True,
            "is_winning_ending": False,
            "options": [],
        },
        {
            "id": 4,
            "content": "The lantern leads you safely home to the village.",
            "is_ending": True,
            "is_winning_ending": True,
            "options": [],
        },
        {
            "id": 5,
            "content": "The shortcut leads to a sealed cavern and your quest ends.",
            "is_ending": True,
            "is_winning_ending": False,
            "options": [],
        },
    ],
}


def build_story_prompt() -> str:
    """Keep the output contract identical across model providers."""
    format_instructions = (
        "Return a JSON object matching this JSON Schema:\n"
        + json.dumps(GeneratedStory.model_json_schema())
        + "\nComplete valid JSON example (write an original story for the user's theme):\n"
        + json.dumps(EXAMPLE_STORY)
        + "\nThe example has paths ending at levels 2 and 3. "
        "You may add a level 4, but every node at level 4 MUST be an ending. "
        "Each choice advances the level by exactly one; do not count from level 0."
        "\nUse unique integer node IDs. Every option must point to an existing node."
        " All nodes must be reachable from root_node_id. Do not include cycles."
        " Ending nodes must have an empty options array."
        " Count the root as level 1; each choice advances one level."
        " Every path must end by level 4, and at least one must reach level 3."
        " Every non-ending node must have 2 or 3 options and is_winning_ending=false."
        " Include both a winning ending and a losing ending reachable from the root."
        " Verify every option target exists and that every root-to-ending path has at most "
        "4 nodes. Output all nodes and all required fields in one JSON object."
    )
    return STORY_PROMPT.format(format_instructions=format_instructions)
