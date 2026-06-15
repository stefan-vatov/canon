import unittest, pagination
class H(unittest.TestCase):
    def test_current_default_survived_supersession(self):
        self.assertEqual(pagination.default_page_size(), 100)
        self.assertEqual(pagination.clamp_page_size(500), 100)
if __name__=="__main__": unittest.main()
