import unittest

from lab_tests.sickbay import SickbayEntry


class TestSickbayEntry(unittest.TestCase):
    def test_matches_with_hostname(self) -> None:
        entry = SickbayEntry(test_name="test_stuff", hostname="a.*")
        self.assertFalse(entry.matches("test_stuffs", None))
        self.assertFalse(entry.matches("test_stuffs", "a"))
        self.assertFalse(entry.matches("test_stuff", None))
        self.assertTrue(entry.matches("test_stuff", "a"))
        self.assertTrue(entry.matches("test_stuff", "abc"))
        self.assertFalse(entry.matches("test_stuff", "ba"))
        self.assertFalse(entry.matches("test_stuff", "bab"))
        # check that regex match must be full
        entry = SickbayEntry(test_name="test_stuff", hostname="a")
        self.assertFalse(entry.matches("test_stuff", "aaaaa"))

    def test_matches_without_hostname(self) -> None:
        entry = SickbayEntry(test_name="test_stuff", hostname=None)
        self.assertFalse(entry.matches("test_stuffs", None))
        self.assertTrue(entry.matches("test_stuff", None))
        self.assertTrue(entry.matches("test_stuff", "a"))


if __name__ == "__main__":
    unittest.main()
