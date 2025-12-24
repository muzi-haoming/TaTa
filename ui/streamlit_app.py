# import streamlit as st
# from langchain.agents import AgentState
# from langchain_core.messages import HumanMessage, ToolMessage, AIMessageChunk
#
# from core import create_npc_generation_agent
# from middlewares import handle_tool_errors
# from tools import search_relevent_lore
#
#
# def init_session_state():
#     if "lore_container_expander" not in st.session_state:
#         st.session_state.lore_container_expanded = False
#
#
# # def render_sidebar():
# #     """
# #     渲染侧边栏
# #     """
# #     with st.sidebar:
# #         st.
#
#
# def render_main_content():
#     """
#     渲染主内容区域
#     """
#     st.title("🎭 TaTa NPC Architect System")
#     st.caption("AI 驱动的游戏 NPC 角色生成工具")
#
#     # 用户输入
#     prompt = st.text_area(
#         "描述你要生成的 NPC:",
#         height=120,
#         placeholder="例如：一个在死亡之山脚下卖防火药水的哥布林商人，性格胆小...",
#     )
#
#     col1, col2 = st.columns([1, 4])
#     with col1:
#         generate_btn = st.button("✨ 生成 NPC 档案", type="primary")
#
#     # 生成逻辑
#     if generate_btn and prompt:
#         _generate_npc(prompt)
#     elif generate_btn and not prompt:
#         st.warning("请先输入 NPC 描述")
#
#
# def _generate_npc(prompt: str):
#     """
#     执行 NPC 生成
#
#     Args:
#         prompt: 用户输入的描述
#         temperature: 温度参数
#     """
#     messages = []
#     query_content = prompt
#     messages.append(HumanMessage(content=query_content))
#     agent_state = AgentState(messages=messages)
#     npc_generation_agent = create_npc_generation_agent([search_relevent_lore], [handle_tool_errors], checkpointer)
#
#     chunks = npc_generation_agent.stream(
#         input=agent_state,
#         stream_mode="messages",
#     )
#
#     lore_expander = st.expander("📚 参考资料", expanded=st.session_state.lore_container_expanded)
#     lore_placeholder = lore_expander.empty()    # 在 Expander 内部放一个占位符，用来实时刷新工具输出
#     st.subheader("📋 生成结果")
#     response_placeholder = st.empty()
#     success_container = st.empty()
#
#     lore_result = ""
#     response_result = ""
#
#     for chunk in chunks:
#         token, metadata = chunk
#         if not token.content: continue
#         if isinstance(token, ToolMessage):
#             if "search_relevent_lore" == token.name:
#                 lore_result += f"\n\n**[{token.name}]**: {token.content}"
#                 lore_placeholder.info(lore_result)
#                 continue
#             if "NPCGenerationResponseStructure" == token.name:
#                 response_result += token.content
#                 response_placeholder.markdown(response_result)
#                 continue
#             continue
#         if isinstance(token, AIMessageChunk):
#             response_result += token.content
#             response_placeholder.markdown(response_result)
#             continue
#
#     if lore_result:
#         st.session_state.lore_container_expanded = True
#
#     if response_result:
#         success_container.success("✅ 生成完成！")
#     else:
#         success_container.empty()
#
#
# def main():
#     st.set_page_config(
#         page_title="TaTa",
#         page_icon="🎭",
#         layout="wide",
#     )
#
#     init_session_state()
#     # render_sidebar()
#     render_main_content()
#
#
# if __name__ == "__main__":
#     main()
