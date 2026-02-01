import unittest

from dogent.outline_edit import parse_outline_edit_payload


class OutlineEditPayloadTests(unittest.TestCase):
    def test_parse_outline_edit_payload(self) -> None:
        payload, errors = parse_outline_edit_payload(
            {"response_type": "outline_edit", "title": "Review", "outline_text": "A"}
        )
        self.assertIsNotNone(payload)
        self.assertFalse(errors)
        self.assertEqual(payload.title, "Review")
        self.assertEqual(payload.outline_text, "A")

    def test_missing_required_fields_returns_error(self) -> None:
        payload, errors = parse_outline_edit_payload(
            {"response_type": "outline_edit", "title": "", "outline_text": "A"}
        )
        self.assertIsNone(payload)
        self.assertTrue(errors)

    def test_non_object_returns_error(self) -> None:
        payload, errors = parse_outline_edit_payload("not-a-dict")
        self.assertIsNone(payload)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
