import io
import json
import unittest
from unittest.mock import patch

import publisher


class PublisherTest(unittest.TestCase):
    def test_extracts_valid_thread(self):
        markdown = "before\n<!-- X_START -->\none\n---THREAD---\ntwo\n<!-- X_END -->"
        self.assertEqual(["one", "two"], publisher.extract_x_posts(markdown))

    def test_rejects_unmarked_content(self):
        with self.assertRaisesRegex(ValueError, "X_START"):
            publisher.extract_x_posts("plain draft")

    def test_posts_thread_as_replies(self):
        with patch.object(publisher, "create_x_post", side_effect=["10", "11"]) as create:
            self.assertEqual(["10", "11"], publisher.publish_x_thread(["one", "two"], "token"))
        self.assertEqual(("one", "token", None), create.call_args_list[0].args)
        self.assertEqual(("two", "token", "10"), create.call_args_list[1].args)

    def test_create_post_uses_official_endpoint(self):
        captured = {}

        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data)
            captured["auth"] = request.get_header("Authorization")
            return io.BytesIO(b'{"data":{"id":"42"}}')

        with patch.object(publisher, "urlopen", fake_open):
            post_id = publisher.create_x_post("hello", "secret", "41")
        self.assertEqual("42", post_id)
        self.assertEqual("https://api.x.com/2/tweets", captured["url"])
        self.assertEqual({"text": "hello", "reply": {"in_reply_to_tweet_id": "41"}}, captured["body"])
        self.assertEqual("Bearer secret", captured["auth"])


if __name__ == "__main__":
    unittest.main()
