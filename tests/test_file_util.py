import unittest

from utils import FileUtil


class MyTestCase(unittest.TestCase):
    def test_file_util(self):
        fs = FileUtil(root_dir="data/npc_generation")
        print(fs.root)
        print(fs.read_text("worldview.txt"))


if __name__ == '__main__':
    unittest.main()
