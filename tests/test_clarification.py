import unittest

from dogent.clarification import (
    CLARIFICATION_JSON_TAG,
    extract_clarification_payload,
    recommended_index,
    validate_clarification_payload,
)


class ClarificationPayloadTests(unittest.TestCase):
    def test_extracts_payload_from_tagged_json(self) -> None:
        text = (
            f"{CLARIFICATION_JSON_TAG}\n"
            "{"
            "\"response_type\": \"clarification\","
            "\"title\": \"Need details\","
            "\"preface\": \"Please answer these.\","
            "\"questions\": ["
            "  {"
            "    \"id\": \"audience\","
            "    \"question\": \"Who is the audience?\","
            "    \"options\": ["
            "      {\"label\": \"Engineers\", \"value\": \"engineers\"},"
            "      {\"label\": \"Managers\", \"value\": \"managers\"}"
            "    ],"
            "    \"recommended\": \"engineers\","
            "    \"allow_freeform\": true,"
            "    \"placeholder\": \"e.g., PMs\""
            "  }"
            "]"
            "}"
        )
        payload, errors = extract_clarification_payload(text)
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

    def test_extract_returns_none_without_tag(self) -> None:
        payload, errors = extract_clarification_payload("{\"title\":\"No tag\"}")
        self.assertIsNone(payload)
        self.assertEqual(errors, [])

    def test_extract_allows_missing_options_and_extra_fields(self) -> None:
        text = (
            f"{CLARIFICATION_JSON_TAG}\n"
            "{"
            "\"response_type\": \"clarification\","
            "\"title\": \"Need info\","
            "\"questions\": ["
            "  {"
            "    \"id\": \"role\","
            "    \"question\": \"Preferred role?\","
            "    \"allow_freeform\": true,"
            "    \"extra\": \"ignore\""
            "  }"
            "]"
            "}"
        )
        payload, errors = extract_clarification_payload(text)
        self.assertEqual(errors, [])
        self.assertIsNotNone(payload)

    def test_extract_coerces_string_options(self) -> None:
        text = (
            f"{CLARIFICATION_JSON_TAG}\n"
            "{"
            "\"response_type\": \"clarification\","
            "\"title\": \"Pick one\","
            "\"questions\": ["
            "  {"
            "    \"id\": \"tone\","
            "    \"question\": \"Tone?\","
            "    \"options\": [\"Formal\", \"Casual\"],"
            "    \"recommended\": 1"
            "  }"
            "]"
            "}"
        )
        payload, errors = extract_clarification_payload(text)
        self.assertEqual(errors, [])
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.questions[0].options[1].value, "Casual")
        self.assertEqual(payload.questions[0].recommended, "Casual")

    def test_extract_accepts_fenced_payload(self) -> None:
        text = (
            "```\n"
            f"{CLARIFICATION_JSON_TAG}\n"
            "{"
            "\"response_type\": \"clarification\","
            "\"title\": \"Need info\","
            "\"questions\": ["
            "  {"
            "    \"id\": \"role\","
            "    \"question\": \"Preferred role?\","
            "    \"options\": []"
            "  }"
            "]"
            "}\n"
            "```"
        )
        payload, errors = extract_clarification_payload(text)
        self.assertEqual(errors, [])
        self.assertIsNotNone(payload)

    def test_extract_accepts_tag_then_fenced_json(self) -> None:
        text = (
            f"{CLARIFICATION_JSON_TAG}\n"
            "```json\n"
            "{"
            "\"response_type\": \"clarification\","
            "\"title\": \"Need info\","
            "\"questions\": ["
            "  {"
            "    \"id\": \"role\","
            "    \"question\": \"Preferred role?\","
            "    \"options\": []"
            "  }"
            "]"
            "}\n"
            "```"
        )
        payload, errors = extract_clarification_payload(text)
        self.assertEqual(errors, [])
        self.assertIsNotNone(payload)

    def test_recommended_index_falls_back(self) -> None:
        text = (
            f"{CLARIFICATION_JSON_TAG}\n"
            "{"
            "\"response_type\": \"clarification\","
            "\"title\": \"Choose\","
            "\"questions\": ["
            "  {"
            "    \"id\": \"tone\","
            "    \"question\": \"Select tone\","
            "    \"options\": ["
            "      {\"label\": \"Formal\", \"value\": \"formal\"},"
            "      {\"label\": \"Casual\", \"value\": \"casual\"}"
            "    ],"
            "    \"recommended\": \"unknown\""
            "  }"
            "]"
            "}"
        )
        payload, _ = extract_clarification_payload(text)
        assert payload is not None
        index = recommended_index(payload.questions[0])
        self.assertEqual(index, 0)

    def test_extract_ignores_tag_in_mid_text(self) -> None:
        text = f"Note: {CLARIFICATION_JSON_TAG} not a tag\n{{\"response_type\":\"clarification\"}}"
        payload, errors = extract_clarification_payload(text)
        self.assertIsNone(payload)
        self.assertEqual(errors, [])

    def test_extract_requires_response_type(self) -> None:
        text = (
            f"{CLARIFICATION_JSON_TAG}\n"
            "{"
            "\"title\": \"Need info\","
            "\"questions\": ["
            "  {"
            "    \"id\": \"role\","
            "    \"question\": \"Preferred role?\","
            "    \"options\": []"
            "  }"
            "]"
            "}"
        )
        payload, errors = extract_clarification_payload(text)
        self.assertIsNone(payload)
        self.assertTrue(errors)
