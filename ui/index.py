"""
首页
"""
import streamlit as st
from uuid import uuid4

# 创建新对话
def create_new_conversation(id):
    st.session_state.conversations[id] = st.session_state.current_conversation

# 选择对话
def select_conversation(id):
    st.session_state.current_conversation = st.session_state.conversations[id]

# 获取AI回复（示例函数，实际应调用模型或API）
def get_assistant_response(user_input):
    return f"这是AI的回复: {user_input[::-1]}"  # 简单示例：返回用户输入的反转字符串

def main() -> None:
    # 初始化会话状态
    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = {"id": None, "title": "", "messages": []}
    if "conversations" not in st.session_state:
        # st.session_state.conversations = []
        st.session_state.conversations = {"0": {"id": 0, "title": "conversation1", "messages": []}, "1": {"id": 1, "title": "conversation2", "messages": []}}

    # 页面配置
    st.set_page_config(page_title="TaTa Chat", layout="wide")

    # 设置侧边栏
    with st.sidebar:
        if st.button("新对话"):
            st.session_state.current_conversation = {"id": None, "title": "", "messages": []}
            st.rerun()  # 显式触发重新渲染，确保右侧内容立即刷新

        #===== 历史会话列表 =====
        st.markdown("### 历史会话")
        for id, conversation_item in st.session_state.conversations.items():
            # 判断当前这一项是不是被选中的对话，用来高亮显示
            is_selected = (st.session_state.current_conversation["id"] == id)

            # print("调试：conversation_item =", conversation_item)

            # 按钮
            if st.button(
                f"{conversation_item["title"]}" if not is_selected else f"{conversation_item["title"]}",    # 按钮文本，选中时可以加上标记
                key=f"conv_btn_{id}",           # key必须唯一，否则Streamlit会报错
                use_container_width=True,         # 按钮占满侧边栏宽度，视觉上更像列表项
                type="primary" if is_selected else "secondary"  # 选中的按钮用主色高亮
            ):
                select_conversation(id)
                st.rerun()  # 显式触发重新渲染，确保右侧内容立即刷新

    # ===== 顶部标题：显示当前对话名，或"新对话"提示 =====
    st.markdown(f"##### {st.session_state.current_conversation['title'] or '新对话'}")

    st.divider()

    # ===== 消息显示区域 =====
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.current_conversation["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # ===== 输入区域：chat_input 自带回车发送、固定底部 =====
    user_input = st.chat_input("输入你的问题或消息")

    if user_input:
        # 如果是新对话，先创建一条新记录
        if st.session_state.current_conversation["id"] is None:
            id = str(uuid4())
            st.session_state.current_conversation["id"] = id
            st.session_state.current_conversation["title"] = f"{user_input[:20]}"
            create_new_conversation(id)

        # 把用户消息加入当前对话历史
        st.session_state.current_conversation["messages"].append({
            "role": "user",
            "content": user_input
        })

        # 调用你的模型/agent生成回复
        assistant_reply = get_assistant_response(user_input)

        # 把AI回复加入消息历史
        st.session_state.current_conversation["messages"].append({
            "role": "assistant",
            "content": assistant_reply
        })

        # 刷新页面，显示新消息
        st.rerun()

if __name__ == "__main__":
    main()