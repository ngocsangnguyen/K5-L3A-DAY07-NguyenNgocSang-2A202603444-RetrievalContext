import unittest

from starter.context_expansion import expanded_context


class ContextExpansionTests(unittest.TestCase):
    def test_package_import_and_context_build(self):
        chunk = {
            "id": "c1",
            "source_id": "doc",
            "source": "doc.pdf",
            "page": 1,
            "text": "An algorithm is a sequence of steps.",
            "metadata": {},
        }

        context, ids = expanded_context([chunk], [chunk])

        self.assertIn("An algorithm is a sequence of steps.", context)
        self.assertEqual(ids, ["c1"])


if __name__ == "__main__":
    unittest.main()
