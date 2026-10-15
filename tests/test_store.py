import os
import tempfile
import unittest

os.environ["FUZZYFRIEND_HOME"] = tempfile.mkdtemp()

from fuzzyfriend import store  # noqa: E402
from fuzzyfriend.models import Pet  # noqa: E402


def pets(n, foster=False):
    return [Pet(source="t", id=str(i), name=f"cat{i}", species="cat", url=f"u{i}", foster=foster) for i in range(n)]


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.db = store.connect()
        self.db.execute("DELETE FROM pets")
        self.db.execute("DELETE FROM runs")
        self.db.execute("DELETE FROM events")

    def test_gone_needs_two_misses(self):
        store.sync(self.db, "t", pets(10))
        _, gone, _, _ = store.sync(self.db, "t", pets(9))
        self.assertEqual(gone, [])
        _, gone, _, _ = store.sync(self.db, "t", pets(9))
        self.assertEqual([g["id"] for g in gone], ["9"])

    def test_reappearing_resets_miss_count(self):
        store.sync(self.db, "t", pets(10))
        store.sync(self.db, "t", pets(9))
        store.sync(self.db, "t", pets(10))
        _, gone, _, _ = store.sync(self.db, "t", pets(9))
        self.assertEqual(gone, [])

    def test_partial_scrape_marks_nothing(self):
        store.sync(self.db, "t", pets(10))
        store.sync(self.db, "t", pets(3))
        _, gone, _, _ = store.sync(self.db, "t", pets(3))
        self.assertEqual(gone, [])

    def test_foster_to_center_is_a_change(self):
        store.sync(self.db, "t", pets(2, foster=True))
        _, _, changes, _ = store.sync(self.db, "t", pets(2, foster=False))
        self.assertEqual({(c[1], c[2], c[3]) for c in changes}, {("foster", True, False)})


if __name__ == "__main__":
    unittest.main()
