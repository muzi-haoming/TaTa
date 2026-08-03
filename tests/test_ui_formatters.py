"""UI 格式化与步骤表的单元测试（纯函数，不启动 Streamlit）"""
import unittest

from ui.formatters import format_completed_result, format_final_result, format_npc_json_result
from ui.npc_generation_page import MODES, WORKFLOW_STEPS, WORKFLOW_STEPS_BY_NODE, ChatMode

_NPC = {
    "name": "米洛",
    "race": "利特族",
    "personality": "谨慎",
    "background": "背景故事",
    "opening_line": "别碰我的花",
    "appearance": "外观描述",
}


class TestFormatNpcJson(unittest.TestCase):
    def test_empty_input_returns_empty_string(self):
        self.assertEqual(format_npc_json_result({}), "")

    def test_contains_table_and_details(self):
        result = format_npc_json_result(_NPC)
        self.assertIn("| **姓名** | 米洛 |", result)
        self.assertIn("| **种族** | 利特族 |", result)
        self.assertIn("**背景故事**: 背景故事", result)
        self.assertIn("**开场白**: _别碰我的花_", result)
        self.assertIn("**外观描述**: 外观描述", result)

    def test_missing_fields_fall_back_to_placeholder(self):
        self.assertIn("| **种族** | 未知 |", format_npc_json_result({"name": "米洛"}))


class TestFormatFinalResult(unittest.TestCase):
    def test_lists_only_existing_artifacts(self):
        result = format_final_result({"npc_json_path": "a.json", "npc_image_path": "", "npc_model_path": None})
        self.assertIn("`a.json`", result)
        self.assertNotIn("角色图片", result)
        self.assertNotIn("3D模型", result)

    def test_missing_keys_do_not_raise(self):
        self.assertEqual(format_final_result({}), "#### 📁 生成的文件\n")

    def test_completed_result_joins_sections(self):
        result = format_completed_result({"npc_json": _NPC, "npc_json_path": "a.json"})
        self.assertTrue(result.startswith("### ✨ NPC角色生成完成！\n\n"))
        self.assertIn("角色档案", result)
        self.assertIn("`a.json`", result)


class TestWorkflowStepTable(unittest.TestCase):
    def test_node_names_are_unique(self):
        self.assertEqual(len(WORKFLOW_STEPS_BY_NODE), len(WORKFLOW_STEPS))

    def test_only_last_step_has_no_pending_label(self):
        without_next = [step.node for step in WORKFLOW_STEPS if step.pending_label is None]
        self.assertEqual(without_next, [WORKFLOW_STEPS[-1].node])

    def test_modes_cover_every_enum_value(self):
        self.assertEqual(set(MODES), {mode.value for mode in ChatMode})
        for meta in MODES.values():
            self.assertTrue(meta.display_name and meta.description and meta.input_placeholder)


if __name__ == "__main__":
    unittest.main()
