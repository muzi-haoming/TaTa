"""配置加载的单元测试"""
import os
import tempfile
import unittest
from pathlib import Path

from config import ConfigLoader, MeshySettings, Settings, get_config, meshy_config, settings


class TestSettingsLoading(unittest.TestCase):
    def test_loader_is_singleton(self):
        self.assertIs(get_config(), ConfigLoader())

    def test_module_level_shortcuts_point_to_loader(self):
        self.assertIs(settings, get_config().settings)
        self.assertIs(meshy_config, get_config().meshy)

    def test_values_come_from_yaml(self):
        self.assertEqual(settings.google_cloud.project, "tata-482008")
        self.assertEqual(settings.vector_store.collection_name, "npc_lore_collection")

    def test_environment_variables_are_injected(self):
        self.assertEqual(os.environ["GOOGLE_CLOUD_PROJECT"], settings.google_cloud.project)
        self.assertEqual(os.environ["GOOGLE_CLOUD_LOCATION"], settings.google_cloud.location)

    def test_missing_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            fallback = Settings.load(Path(empty_dir))
        self.assertEqual(fallback.google_cloud.project, "tata-482008")
        self.assertEqual(fallback.retriever.search_kwargs.k, 10)

    def test_yaml_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / Settings.source_filename).write_text(
                "google_cloud:\n  project: other-project\n", encoding="utf-8"
            )
            loaded = Settings.load(Path(tmp))
        self.assertEqual(loaded.google_cloud.project, "other-project")
        # 未覆盖的字段仍使用默认值
        self.assertEqual(loaded.google_cloud.location, "us-central1")

    def test_subclass_without_filename_raises(self):
        class Nameless(Settings):
            source_filename = ""

        with self.assertRaises(NotImplementedError):
            Nameless.load(Path("."))


class TestMeshySettings(unittest.TestCase):
    def test_endpoint_url_composition(self):
        self.assertEqual(
            meshy_config.api.get_endpoint_url("image_to_3d"),
            "https://api.meshy.ai/openapi/v1/image-to-3d",
        )

    def test_unknown_endpoint_yields_base_url(self):
        self.assertEqual(meshy_config.api.get_endpoint_url("nope"), meshy_config.api.base_url)

    def test_defaults_are_available_without_file(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            fallback = MeshySettings.load(Path(empty_dir))
        self.assertEqual(fallback.multi_image_to_3d.ai_model, "meshy-5")
        self.assertEqual(fallback.download.chunk_size, 8192)


if __name__ == "__main__":
    unittest.main()
