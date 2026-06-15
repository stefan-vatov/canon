import unittest, pagination
class H(unittest.TestCase):
    def test_default_now_100(self):
        self.assertEqual(pagination.default_page_size(), 100)
if __name__=="__main__": unittest.main()
