"""
AI 控制鼠标测试

功能：根据屏幕截图，使用 AI 分析并生成 pyautogui 脚本，从搜索框搜索并打开微信
"""
import asyncio
import base64
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_experimental.tools import PythonREPLTool

from config import settings
from utils.file_util import FileUtil


# ==================== 配置 ====================

ROOT_DIR = Path("data/ai_control")
SCREENSHOT_FILE = "screenshot.png"
SCRIPT_FILE = "auto_open_weixin.py"


# ==================== 工具函数 ====================

def capture_screenshot(fs: FileUtil) -> str:
    """
    截取屏幕截图并保存

    Returns:
        截图文件的绝对路径
    """
    import pyautogui

    # 截取全屏
    screenshot = pyautogui.screenshot()

    # 保存到文件
    screenshot_path = fs.get_abs_path(SCREENSHOT_FILE)
    screenshot.save(screenshot_path)
    print(f"[截图] 已保存到: {screenshot_path}")

    return screenshot_path


def analyze_screenshot_and_generate_code(fs: FileUtil) -> str:
    """
    使用 AI 分析截图并生成自动化代码

    Returns:
        生成的 Python 代码
    """
    # 读取截图为 base64
    screenshot_b64 = fs.read_image(SCREENSHOT_FILE, add_header=True)

    # 初始化视觉模型
    model = init_chat_model(model=settings.models.chat_model)

    # 构建分析和代码生成提示
    prompt = """你是一个 pyautogui 自动化专家。请分析这张 Windows 桌面截图，然后生成一个完整的 Python 脚本来完成以下任务：

**任务**：从左下角的搜索框搜索 "weixin" 并打开微信

**分析要求**：
1. 仔细观察截图中左下角的搜索框/开始按钮的位置
2. 注意任务栏的高度和搜索框的具体坐标
3. 考虑不同分辨率的适配

**生成的代码要求**：
1. 使用 pyautogui 库
2. 设置 pyautogui.FAILSAFE = True 确保安全
3. 添加适当的 time.sleep() 等待
4. 包含完整的错误处理
5. 代码必须可以直接运行

**重要**：
- 只输出 Python 代码，不要有任何解释文字
- 代码必须以 ```python 开头，以 ``` 结尾
- 使用点击左下角搜索框 -> 输入 weixin -> 按回车的流程

请分析截图并生成代码："""

    # 调用模型
    response = model.invoke([
        HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": screenshot_b64}},
        ])
    ])

    # 提取代码
    content = response.content
    if "```python" in content:
        code = content.split("```python")[1].split("```")[0].strip()
    elif "```" in content:
        code = content.split("```")[1].split("```")[0].strip()
    else:
        code = content.strip()

    print(f"[AI] 生成代码:\n{code[:500]}...")

    return code


def save_and_validate_code(fs: FileUtil, code: str) -> str:
    """
    保存代码并进行基本验证

    Returns:
        代码文件的绝对路径
    """
    # 添加安全头部（如果没有）
    if "pyautogui.FAILSAFE" not in code:
        safety_header = """import pyautogui
import time

# 安全设置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

"""
        if "import pyautogui" in code:
            code = code.replace("import pyautogui", safety_header.strip(), 1)
        else:
            code = safety_header + code

    # 保存代码
    script_path = fs.write_text(SCRIPT_FILE, code)
    print(f"[保存] 脚本已保存到: {script_path}")

    # 基本语法检查
    try:
        compile(code, SCRIPT_FILE, 'exec')
        print("[验证] 代码语法检查通过")
    except SyntaxError as e:
        print(f"[警告] 代码语法错误: {e}")

    return script_path


def execute_with_repl(fs: FileUtil) -> str:
    """
    使用 PythonREPLTool 执行代码

    Returns:
        执行结果
    """
    repl = PythonREPLTool()

    # 读取保存的脚本
    script_content = fs.read_text(SCRIPT_FILE)

    print("[执行] 开始运行自动化脚本...")
    print("-" * 50)

    # 执行代码
    result = repl.run(script_content)

    print("-" * 50)
    print(f"[结果] {result}")

    return result


# ==================== 主流程 ====================

def run_ai_control_workflow(target_app: str = "weixin"):
    """
    完整的 AI 控制工作流

    Args:
        target_app: 要搜索并打开的应用名称
    """
    print("=" * 60)
    print("AI 桌面控制系统")
    print("=" * 60)

    # 初始化文件工具
    fs = FileUtil(str(ROOT_DIR))

    try:
        # Step 1: 截取屏幕
        print("\n[Step 1] 截取屏幕截图...")
        capture_screenshot(fs)

        # Step 2: AI 分析并生成代码
        print("\n[Step 2] AI 分析截图并生成自动化代码...")
        code = analyze_screenshot_and_generate_code(fs)

        # Step 3: 保存并验证代码
        print("\n[Step 3] 保存并验证代码...")
        save_and_validate_code(fs, code)

        # Step 4: 执行代码
        print("\n[Step 4] 使用 PythonREPLTool 执行代码...")
        result = execute_with_repl(fs)

        print("\n" + "=" * 60)
        print("任务完成!")
        print("=" * 60)

        return result

    except Exception as e:
        print(f"\n[错误] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        raise


# ==================== 异步版本（可选） ====================

async def run_ai_control_workflow_async(target_app: str = "weixin"):
    """异步版本的工作流"""
    return await asyncio.to_thread(run_ai_control_workflow, target_app)


# ==================== pytest 测试函数 ====================

def test_ai_control_open_weixin():
    """
    测试 AI 控制打开微信

    执行完整流程：截图 -> AI分析 -> 生成代码 -> REPL执行
    """
    run_ai_control_workflow("weixin")


# ==================== 入口 ====================

if __name__ == "__main__":
    run_ai_control_workflow("weixin")
