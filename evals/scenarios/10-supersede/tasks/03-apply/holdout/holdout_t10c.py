import unittest, pagination
class H(unittest.TestCase):
    def test_clamps_to_current_default_100(self):
        self.assertEqual(pagination.clamp_page_size(500), 100)  # superseded 50 would fail
    def test_passes_through_small(self):
        self.assertEqual(pagination.clamp_page_size(30), 30)
if __name__=="__main__": unittest.main()
