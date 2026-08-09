"""
应用入口

启动::

    chainlit run app.py -w

说明：
    Chainlit 会导入本模块，ui.index 中的 @cl.on_chat_start / @cl.on_message
    等装饰器在导入时即完成注册，因此不需要 __main__ 里再调用 main()。
"""

from dotenv import load_dotenv

load_dotenv()  # 必须在导入业务模块之前执行

import logging

from utils import setup_logger

setup_logger(logging.DEBUG)

# 导入即注册 Chainlit 事件处理器
from ui import index
