import unittest

from pydantic import ValidationError

from app.modules.stories.generation_schemas import GeneratedStory
from tests.support import story_payload


class GeneratedStoryTests(unittest.TestCase):
    def test_valid_branching_story(self):
        story = GeneratedStory.model_validate(story_payload())
        self.assertEqual(len(story.nodes), 5)

    def test_invalid_graphs(self):
        for case in (
            "duplicate",
            "missing_root",
            "missing_target",
            "cycle",
            "unreachable",
            "ending_options",
            "winning_non_ending",
            "single_option",
            "no_winner",
            "no_loser",
            "too_shallow",
            "too_deep",
            "blank_content",
        ):
            with self.subTest(case=case):
                story = story_payload()
                nodes = story["nodes"]
                if case == "duplicate":
                    nodes[1]["id"] = nodes[0]["id"]
                elif case == "missing_root":
                    story["root_node_id"] = 999
                elif case == "missing_target":
                    nodes[0]["options"][0]["node_id"] = 999
                elif case == "cycle":
                    nodes[1]["options"][0]["node_id"] = 10
                elif case == "unreachable":
                    nodes.append({**nodes[-1], "id": 999})
                elif case == "ending_options":
                    nodes[-1]["options"] = [{"text": "Continue", "node_id": 10}]
                elif case == "winning_non_ending":
                    nodes[0]["is_winning_ending"] = True
                elif case == "single_option":
                    nodes[0]["options"].pop()
                elif case == "no_winner":
                    nodes[3]["is_winning_ending"] = False
                elif case == "no_loser":
                    for node in nodes:
                        node["is_winning_ending"] = node["is_ending"]
                elif case == "too_shallow":
                    nodes[0]["options"] = [
                        {"text": "Win", "node_id": 40},
                        {"text": "Lose", "node_id": 50},
                    ]
                    story["nodes"] = [nodes[0], nodes[3], nodes[4]]
                elif case == "too_deep":
                    for node_id, target in ((50, 60), (60, 70)):
                        node = next((n for n in nodes if n["id"] == node_id), None)
                        if node is None:
                            node = {
                                "id": node_id,
                                "content": "Continue",
                                "is_winning_ending": False,
                            }
                            nodes.append(node)
                        node.update(
                            is_ending=False,
                            options=[
                                {"text": "Continue", "node_id": target},
                                {"text": "Escape", "node_id": 40},
                            ],
                        )
                    nodes.append(
                        {
                            "id": 70,
                            "content": "Lost",
                            "is_ending": True,
                            "is_winning_ending": False,
                            "options": [],
                        }
                    )
                elif case == "blank_content":
                    nodes[0]["content"] = "  "
                with self.assertRaises(ValidationError):
                    GeneratedStory.model_validate(story)
