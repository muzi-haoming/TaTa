"""
结果格式化

把工作流状态转成 Markdown 文本。纯函数、无 Streamlit 依赖，便于单测。
"""
from typing import Any, List, Mapping, Tuple

_UNKNOWN = "未知"

#: 角色档案表格中展示的字段：(表头, state 键)
_PROFILE_TABLE_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("姓名", "name"),
    ("种族", "race"),
    ("性格", "personality"),
)

#: 表格之后逐段展示的字段：(标题, state 键, 值的 Markdown 包裹符)
_PROFILE_DETAIL_FIELDS: Tuple[Tuple[str, str, str], ...] = (
    ("背景故事", "background", ""),
    ("开场白", "opening_line", "_"),
    ("外观描述", "appearance", ""),
)

#: 最终产物文件：(图标, 名称, state 键)
_ARTIFACT_FIELDS: Tuple[Tuple[str, str, str], ...] = (
    ("📄", "角色档案", "npc_json_path"),
    ("🖼️", "角色图片", "npc_image_path"),
    ("🎮", "3D模型", "npc_model_path"),
)


def format_npc_json_result(npc_json: Mapping[str, Any]) -> str:
    """把角色档案格式化为 Markdown（表格 + 长文本段落）。"""
    if not npc_json:
        return ""

    lines: List[str] = ["#### 📋 角色档案\n", "| 属性 | 内容 |", "|------|------|"]
    lines += [
        f"| **{title}** | {npc_json.get(key, _UNKNOWN)} |"
        for title, key in _PROFILE_TABLE_FIELDS
    ]
    for title, key, wrapper in _PROFILE_DETAIL_FIELDS:
        value = npc_json.get(key, _UNKNOWN)
        lines += ["", f"**{title}**: {wrapper}{value}{wrapper}"]

    return "\n".join(lines)


def format_final_result(state: Mapping[str, Any]) -> str:
    """列出最终生成的文件路径。"""
    lines: List[str] = ["#### 📁 生成的文件\n"]
    lines += [
        f"- {icon} {title}: `{state.get(key)}`"
        for icon, title, key in _ARTIFACT_FIELDS
        if state.get(key)
    ]
    return "\n".join(lines)


def format_completed_result(state: Mapping[str, Any], title: str = "### ✨ NPC角色生成完成！") -> str:
    """把「档案 + 文件清单」拼成一条完整的助手消息。"""
    return "\n\n".join([
        title,
        format_npc_json_result(state.get("npc_json", {})),
        format_final_result(state),
    ])
