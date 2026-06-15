import unittest, pagination
class H(unittest.TestCase):
    def test_default_is_50(self):
        self.assertEqual(pagination.default_page_size(), 50)
if __name__=="__main__": unittest.main()
