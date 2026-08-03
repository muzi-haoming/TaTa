"""
应用入口

启动::

    streamlit run app.py
"""
from dotenv import load_dotenv
load_dotenv()
from utils import setup_logger
from ui import main

if __name__ == "__main__":
    setup_logger()
    main()
