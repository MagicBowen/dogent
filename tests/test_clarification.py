import unittest

from dogent.features.clarification import (
    parse_clarification_payload,
    recommended_index,
    validate_clarification_payload,
)


class ClarificationPayloadTests(unittest.TestCase):
    def test_parse_payload(self) -> None:
        payload, errors = parse_clarification_payload(
            {
                "response_type": "clarification",
                "title": "Need details",
                "preface": "Please answer these.",
                "questions": [
                    {
                        "id": "audience",
                        "question": "Who is the audience?",
                        "options": [
                            {"label": "Engineers", "value": "engineers"},
                            {"label": "Managers", "value": "managers"},
                        ],
                        "recommended": "engineers",
                        "allow_freeform": True,
                        "placeholder": "e.g., PMs",
                    }
                ],
            }
        )
        self.assertIsNotNone(payload)
        self.assertEqual(errors, [])
        assert payload is not None
        self.assertEqual(payload.title, "Need details")
        self.assertEqual(payload.questions[0].question_id, "audience")

    def test_invalid_payload_reports_errors(self) -> None:
        payload = {
            "response_type": "clarification",
            "title": "Missing questions",
            "questions": [],
        }
        errors = validate_clarification_payload(payload)
        self.assertTrue(errors)

    def test_parse_allows_missing_options(self) -> None:
        payload, errors = parse_clarification_payload(
            {
                "response_type": "clarification",
                "title": "Need info",
                "questions": [
                    {
                        "id": "role",
                        "question": "Preferred role?",
                        "allow_freeform": True,
                    }
                ],
            }
        )
        self.assertEqual(errors, [])
        self.assertIsNotNone(payload)

    def test_parse_coerces_string_options(self) -> None:
        payload, errors = parse_clarification_payload(
            {
                "response_type": "clarification",
                "title": "Pick one",
                "questions": [
                    {
                        "id": "tone",
                        "question": "Tone?",
                        "options": ["Formal", "Casual"],
                        "recommended": 1,
                    }
                ],
            }
        )
        self.assertEqual(errors, [])
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.questions[0].options[1].value, "Casual")
        self.assertEqual(payload.questions[0].recommended, "Casual")

    def test_recommended_index_falls_back(self) -> None:
        payload, _ = parse_clarification_payload(
            {
                "response_type": "clarification",
                "title": "Choose",
                "questions": [
                    {
                        "id": "tone",
                        "question": "Select tone",
                        "options": [
                            {"label": "Formal", "value": "formal"},
                            {"label": "Casual", "value": "casual"},
                        ],
                        "recommended": "unknown",
                    }
                ],
            }
        )
        assert payload is not None
        index = recommended_index(payload.questions[0])
        self.assertEqual(index, 0)

    def test_parse_requires_object(self) -> None:
        payload, errors = parse_clarification_payload("not-a-dict")
        self.assertIsNone(payload)
        self.assertTrue(errors)
