"""
工作流状态定义

状态的默认值由类型注解推导（见 :func:`initial_state`），不再手工维护一份
与 ``TypedDict`` 平行的默认值字典——新增字段时不会遗漏初始化。
"""
from typing import Any, Dict, TypedDict, get_type_hints

#: 各类型对应的零值工厂
_ZERO_VALUE_FACTORIES = {
    str: str,
    bool: bool,
    int: int,
    float: float,
    dict: dict,
    list: list,
}


class NpcState(TypedDict):
    """NPC 生成工作流的状态。"""

    # 输入
    prompt: str

    # 参考资料
    worldview: str
    model_style: str
    npc_relevent_lore: str

    # 角色档案
    npc_json: dict
    npc_json_is_ok: bool
    npc_json_feedback: str
    npc_json_path: str

    # 图片提示词
    npc_image_prompt: str
    npc_image_prompt_is_ok: bool
    npc_image_prompt_feedback: str

    # 图片
    npc_image_base64: str
    npc_image_is_ok: bool
    npc_image_feedback: str
    npc_image_path: str

    # 3D 模型
    npc_model_path: str


def initial_state(schema: type) -> Dict[str, Any]:
    """
    根据 ``TypedDict`` 的注解生成零值初始状态。

    :param schema: 状态的 TypedDict 类型。
    :return: 每个字段取其类型零值（str -> ""、bool -> False、dict -> {} ...）的字典。
    :raises TypeError: 存在无法推导零值的字段类型。
    """
    state: Dict[str, Any] = {}
    for key, annotation in get_type_hints(schema).items():
        factory = _ZERO_VALUE_FACTORIES.get(annotation)
        if factory is None:
            raise TypeError(f"无法为字段 {key}: {annotation!r} 推导零值，请在 _ZERO_VALUE_FACTORIES 中登记")
        state[key] = factory()
    return state
