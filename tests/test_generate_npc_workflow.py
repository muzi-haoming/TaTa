"""
工作流构件的单元测试（不触网、不调用大模型）

需要真实调用模型的端到端流程见 ``python -m scripts.run_npc_workflow``。
"""
import unittest
from typing import TypedDict

from core import prompts
from workflows import ACCEPTED, REJECTED, LlmWorkflow, NpcState, Section, initial_state
from workflows.generate_npc_workflow import (
    NPC_IMAGE_EVALUATOR_SPEC,
    NPC_IMAGE_PROMPT_GENERATOR_SPEC,
    NPC_JSON_EVALUATOR_SPEC,
    NPC_JSON_GENERATOR_SPEC,
    REFERENCE_SPECS,
    REVIEW_SPECS,
    GenerateNpcWorkflow,
)


class TestInitialState(unittest.TestCase):
    """零值初始状态由类型注解推导"""

    def test_covers_every_declared_field(self):
        state = initial_state(NpcState)
        self.assertEqual(set(state), set(NpcState.__annotations__))

    def test_zero_values_by_type(self):
        state = initial_state(NpcState)
        self.assertEqual(state["prompt"], "")
        self.assertEqual(state["npc_json"], {})
        self.assertFalse(state["npc_json_is_ok"])

    def test_dict_fields_are_not_shared_between_calls(self):
        first, second = initial_state(NpcState), initial_state(NpcState)
        first["npc_json"]["name"] = "x"
        self.assertEqual(second["npc_json"], {})

    def test_unsupported_annotation_raises(self):
        class Bad(TypedDict):
            weird: complex

        with self.assertRaises(TypeError):
            initial_state(Bad)


class TestRouter(unittest.TestCase):
    """条件边路由"""

    def test_accepts_when_flag_true(self):
        route = LlmWorkflow.make_router("npc_json_is_ok")
        self.assertEqual(route({"npc_json_is_ok": True}), ACCEPTED)

    def test_rejects_when_flag_false(self):
        route = LlmWorkflow.make_router("npc_json_is_ok")
        self.assertEqual(route({"npc_json_is_ok": False}), REJECTED)

    def test_router_is_named_after_its_flag(self):
        self.assertEqual(LlmWorkflow.make_router("npc_image_is_ok").__name__, "route_npc_image_is_ok")


class TestSectionRendering(unittest.TestCase):
    """提示词分段渲染"""

    def setUp(self):
        self.state = {"worldview": "WV", "npc_json": {"name": "米洛"}}

    def test_renders_label_and_value(self):
        rendered = LlmWorkflow._render_sections([Section("worldview", "worldview")], self.state)
        self.assertEqual(rendered, ["[worldview]: WV"])

    def test_suffix_is_appended(self):
        rendered = LlmWorkflow._render_sections(
            [Section("worldview", "worldview")], self.state, suffix="\n\n"
        )
        self.assertEqual(rendered, ["[worldview]: WV\n\n"])

    def test_dict_values_are_stringified(self):
        rendered = LlmWorkflow._render_sections([Section("npc_json", "npc_json")], self.state)
        self.assertEqual(rendered, ["[npc_json]: {'name': '米洛'}"])

    def test_image_block_shape(self):
        block = LlmWorkflow._image_block("QUJD", "jpeg")
        self.assertEqual(block["type"], "image_url")
        self.assertEqual(block["image_url"]["url"], "data:image/jpeg;base64,QUJD")

    def test_preview_truncates(self):
        self.assertEqual(LlmWorkflow._preview("abcdef", 3), "abc")


class TestWorkflowSpecs(unittest.TestCase):
    """节点声明与提示词的对应关系（纯数据，不实例化工作流，避免触网）"""

    def test_json_generator_spec_uses_the_right_prompts(self):
        spec = NPC_JSON_GENERATOR_SPEC
        self.assertEqual(spec.generate_prompt, prompts.NPC_JSON_GENERATE)
        self.assertEqual(spec.refine_prompt, prompts.NPC_JSON_REFINE)
        self.assertEqual(spec.target_key, "npc_json")
        # 二次优化时才追加档案与反馈
        self.assertEqual([s.label for s in spec.refine_sections], ["npc_json", "feedback"])

    def test_json_generator_sections_keep_legacy_label(self):
        """标签 'promot' 是历史拼写，属于提示词内容，不能顺手改掉。"""
        self.assertEqual(NPC_JSON_GENERATOR_SPEC.sections[0].label, "promot")
        self.assertEqual(NPC_JSON_GENERATOR_SPEC.sections[0].key, "prompt")

    def test_image_prompt_generator_spec(self):
        spec = NPC_IMAGE_PROMPT_GENERATOR_SPEC
        self.assertEqual(spec.target_key, "npc_image_prompt")
        self.assertEqual([s.label for s in spec.sections],
                         ["worldview", "model_style", "npc_relevent_lore", "npc_json"])

    def test_image_evaluator_spec_is_multimodal(self):
        self.assertEqual(NPC_IMAGE_EVALUATOR_SPEC.image_key, "npc_image_base64")
        self.assertEqual(NPC_IMAGE_EVALUATOR_SPEC.system_prompt, prompts.NPC_IMAGE_EVALUATE)

    def test_json_evaluator_spec_is_text_only(self):
        self.assertIsNone(NPC_JSON_EVALUATOR_SPEC.image_key)
        self.assertEqual(NPC_JSON_EVALUATOR_SPEC.flag_key, "npc_json_is_ok")

    def test_every_spec_key_exists_in_state(self):
        """所有 spec 引用的 state 键都必须在 NpcState 中声明。"""
        declared = set(NpcState.__annotations__)
        referenced = set()
        for spec in (NPC_JSON_GENERATOR_SPEC, NPC_IMAGE_PROMPT_GENERATOR_SPEC):
            referenced.add(spec.target_key)
            referenced |= {s.key for s in spec.sections + spec.refine_sections}
        for spec in (NPC_JSON_EVALUATOR_SPEC, NPC_IMAGE_EVALUATOR_SPEC):
            referenced |= {spec.flag_key, spec.feedback_key}
            referenced |= {s.key for s in spec.sections}
            if spec.image_key:
                referenced.add(spec.image_key)
        for spec in REVIEW_SPECS.values():
            referenced |= {spec.detail_key, spec.flag_key, spec.feedback_key}
        for spec in REFERENCE_SPECS:
            referenced.add(spec.state_key)

        self.assertEqual(referenced - declared, set())

    def test_retry_policy_covers_vertex_errors(self):
        policy = GenerateNpcWorkflow.build_retry_policy()
        self.assertEqual(policy.max_attempts, 3)
        self.assertIn(TimeoutError, policy.retry_on)
        self.assertIn(ConnectionError, policy.retry_on)


if __name__ == "__main__":
    unittest.main()
