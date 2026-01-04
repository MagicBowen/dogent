import unittest

from dogent.outline_edit import (
    OUTLINE_EDIT_JSON_TAG,
    extract_outline_edit_payload,
    has_outline_edit_tag,
)


class OutlineEditPayloadTests(unittest.TestCase):
    def test_extract_outline_edit_payload(self) -> None:
        text = "\n".join(
            [
                OUTLINE_EDIT_JSON_TAG,
                '{"response_type": "outline_edit", "title": "Review", "outline_text": "A"}',
            ]
        )
        payload, errors = extract_outline_edit_payload(text)
        self.assertIsNotNone(payload)
        self.assertFalse(errors)
        self.assertEqual(payload.title, "Review")
        self.assertEqual(payload.outline_text, "A")

    def test_tag_must_be_first_line(self) -> None:
        text = "Preface\n" + OUTLINE_EDIT_JSON_TAG + "\n{}"
        payload, errors = extract_outline_edit_payload(text)
        self.assertIsNone(payload)
        self.assertFalse(has_outline_edit_tag(text))
        self.assertFalse(errors)

    def test_invalid_json_returns_error(self) -> None:
        text = "\n".join([OUTLINE_EDIT_JSON_TAG, "{not-json}"])
        payload, errors = extract_outline_edit_payload(text)
        self.assertIsNone(payload)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
