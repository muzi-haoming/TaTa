"""FileUtil 单元测试（全部在临时目录内进行，不触碰项目数据）"""
import base64
import tempfile
import unittest
from pathlib import Path

from utils import FileUtil


class TestFileUtil(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fs = FileUtil(root_dir=self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_root_is_created(self):
        nested = Path(self._tmp.name) / "a" / "b"
        fs = FileUtil(root_dir=nested)
        self.assertTrue(fs.root.is_dir())

    def test_write_and_read_text(self):
        self.fs.write_text("notes/hello.txt", "你好")
        self.assertEqual(self.fs.read_text("notes/hello.txt"), "你好")

    def test_write_text_append(self):
        self.fs.write_text("a.txt", "1")
        self.fs.write_text("a.txt", "2", append=True)
        self.assertEqual(self.fs.read_text("a.txt"), "12")

    def test_write_text_overwrite(self):
        self.fs.write_text("a.txt", "first")
        self.fs.write_text("a.txt", "second")
        self.assertEqual(self.fs.read_text("a.txt"), "second")

    def test_json_roundtrip_keeps_unicode(self):
        path = self.fs.write_json("npc/npc.json", {"name": "米洛"})
        self.assertIn("米洛", Path(path).read_text(encoding="utf-8"))
        self.assertEqual(self.fs.read_json("npc/npc.json"), {"name": "米洛"})

    def test_yaml_roundtrip(self):
        self.fs.write_yaml("c.yaml", {"k": [1, 2]})
        self.assertEqual(self.fs.read_yaml("c.yaml"), {"k": [1, 2]})

    def test_image_roundtrip_with_data_uri_header(self):
        raw = b"\x89PNG\r\n"
        encoded = base64.b64encode(raw).decode()
        self.fs.write_image("i.png", f"data:image/png;base64,{encoded}")
        self.assertEqual(self.fs.read_bytes("i.png"), raw)
        self.assertTrue(self.fs.read_image("i.png", add_header=True).startswith("data:image/png;base64,"))

    def test_read_image_normalizes_jpg_to_jpeg(self):
        self.fs.write_bytes("i.jpg", b"\xff\xd8\xff")
        self.assertTrue(self.fs.read_image("i.jpg", add_header=True).startswith("data:image/jpeg;base64,"))

    def test_write_image_rejects_invalid_base64(self):
        with self.assertRaises(ValueError):
            self.fs.write_image("bad.png", "not base64 @@@")

    def test_read_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.read_text("nope.txt")

    def test_path_traversal_is_blocked(self):
        with self.assertRaises(ValueError):
            self.fs.read_text("../../secret.txt")
        self.assertFalse(self.fs.exists("../../secret.txt"))

    def test_list_files_recursive(self):
        self.fs.write_text("x.txt", "x")
        self.fs.write_text("sub/y.txt", "y")
        self.assertEqual(self.fs.list_files(), ["x.txt"])
        self.assertEqual(sorted(self.fs.list_files(recursive=True)), [str(Path("sub/y.txt")), "x.txt"])

    def test_delete_file_and_directory(self):
        self.fs.write_text("sub/y.txt", "y")
        self.fs.delete("sub/y.txt")
        self.assertFalse(self.fs.exists("sub/y.txt"))
        self.fs.write_text("sub/z.txt", "z")
        self.fs.delete("sub")
        self.assertFalse(self.fs.exists("sub"))
        self.fs.delete("sub")  # 不存在时静默返回

    def test_exists_and_abs_path(self):
        self.fs.write_text("e.txt", "e")
        self.assertTrue(self.fs.exists("e.txt"))
        self.assertEqual(self.fs.get_abs_path("e.txt"), str(self.fs.root / "e.txt"))


if __name__ == "__main__":
    unittest.main()
