import base64
from io import BytesIO

import pyautogui
from langchain.tools import tool

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


# @tool
# def capture_screenshot() -> str:
#     """
#     截取屏幕
#
#     Returns:
#         截图的base64字符串
#     """
#     import pyautogui
#
#     # 截取全屏
#     screenshot = pyautogui.screenshot()
#     buffer = BytesIO()
#     screenshot.save(buffer, format='JPEG')
#     screenshot_base_64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
#
#     return screenshot_base_64


@tool
def capture_screenshot_for_ai(resize_ratio: float = 0.5, quality: int = 70) -> str:
    """
    获取当前屏幕的截图，并将其转换为 Base64 编码字符串。
    Agent 可以在执行操作后调用此工具来“看”屏幕状态，或者在报错时查看界面。

    Args:
        resize_ratio (float): 缩放比例，范围 0.1 到 1.0。
                              默认 0.5 (即长宽各缩小一半)。如果屏幕分辨率很高（如4K），
                              建议保持 0.5 或更小，以减少 Token 消耗和网络延迟。
        quality (int): JPEG 图片压缩质量 (1-100)，默认 70。
                       数值越低图片体积越小，建议 60-80 之间，既能看清文字又能保持轻量。

    Returns:
        str: 图片的 Base64 编码字符串 (不包含 'data:image/jpeg;base64,' 前缀)。
    """
    import pyautogui
    from PIL import Image  # pyautogui 依赖 Pillow，所以环境里肯定有这个

    # 1. 截取全屏 (返回 PIL.Image 对象)
    screenshot = pyautogui.screenshot()

    # 2. (可选) 缩放图片
    # 对于 AI 来说，通常不需要原生 4K 分辨率也能看清按钮和文字
    if 0 < resize_ratio < 1.0:
        width, height = screenshot.size
        new_size = (int(width * resize_ratio), int(height * resize_ratio))
        # 使用 LANCZOS 滤镜进行高质量缩放
        screenshot = screenshot.resize(new_size, Image.Resampling.LANCZOS)

    # 3. 转换为内存中的字节流
    buffer = BytesIO()

    # 4. 保存为 JPEG 格式
    # 强烈建议使用 JPEG 而不是 PNG，因为 PNG 的 Base64 字符串体积通常是 JPEG 的 5-10 倍
    screenshot.save(buffer, format='JPEG', quality=quality)

    # 5. 转 Base64 字符串
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return img_str


@tool
def get_screen_size() -> str:
    """
    获取当前屏幕的分辨率（宽度和高度）。
    Agent 在移动鼠标前应该先调用此工具以了解坐标边界。

    Returns:
        str: 格式为 "width=1920, height=1080" 的字符串
    """
    import pyautogui
    w, h = pyautogui.size()
    return f"width={w}, height={h}"


@tool
def get_mouse_position() -> str:
    """
    获取当前鼠标指针的坐标位置。

    Returns:
        str: 格式为 "x=500, y=300" 的字符串
    """
    import pyautogui
    x, y = pyautogui.position()
    return f"x={x}, y={y}"


@tool
def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    移动鼠标到屏幕上的指定绝对坐标 (x, y)。

    Args:
        x (int): 目标 X 坐标
        y (int): 目标 Y 坐标
        duration (float): 移动耗时（秒），默认0.5秒，设为0为瞬间移动。

    Returns:
        str: 执行结果信息
    """
    import pyautogui

    # 获取屏幕尺寸防止越界（可选的安全检查）
    screen_w, screen_h = pyautogui.size()
    if not (0 <= x <= screen_w and 0 <= y <= screen_h):
        return f"Error: 坐标 ({x}, {y}) 超出屏幕范围 ({screen_w}x{screen_h})"

    pyautogui.moveTo(x, y, duration=duration)
    return f"Mouse moved to ({x}, {y})"


@tool
def click_mouse(x: int = None, y: int = None, button: str = 'left', clicks: int = 1) -> str:
    """
    执行鼠标点击操作。可以指定位置，也可以在当前位置点击。
    支持左键、右键、中键以及双击。

    Args:
        x (int, optional): 点击的 X 坐标，如果为 None 则在当前位置点击
        y (int, optional): 点击的 Y 坐标
        button (str): 鼠标按键，可选 'left', 'right', 'middle'。默认为 'left'。
        clicks (int): 点击次数。1为单击，2为双击。默认为 1。

    Returns:
        str: 执行结果
    """
    import pyautogui

    # 验证按键参数
    if button not in ['left', 'right', 'middle']:
        return "Error: button 参数必须是 'left', 'right' 或 'middle'"

    pyautogui.click(x=x, y=y, button=button, clicks=clicks)
    return f"Clicked {button} button {clicks} times at ({x if x else 'current'}, {y if y else 'current'})"


@tool
def mouse_drag(x: int, y: int, duration: float = 1.0) -> str:
    """
    按住鼠标左键，从当前位置拖拽到目标坐标 (x, y)。
    常用于滑块验证码、拖动文件或画图。

    Args:
        x (int): 拖拽终点的 X 坐标
        y (int): 拖拽终点的 Y 坐标
        duration (float): 拖拽过程耗时。建议设置在 0.5 以上，太快可能失效。

    Returns:
        str: 执行结果
    """
    import pyautogui
    pyautogui.dragTo(x, y, duration=duration, button='left')
    return f"Dragged mouse to ({x}, {y})"


@tool
def scroll_screen(amount: int) -> str:
    """
    滚动鼠标滚轮。

    Args:
        amount (int): 滚动的“点击”数。
                      正数表示向上滚动（页面内容下移），
                      负数表示向下滚动（页面内容上移）。
                      例如：-500 向下滚动，500 向上滚动。

    Returns:
        str: 执行结果
    """
    import pyautogui
    pyautogui.scroll(amount)
    return f"Scrolled screen by {amount}"


@tool
def type_text(text: str, interval: float = 0.05) -> str:
    """
    模拟键盘逐字输入英文字符串或数字。
    注意：此工具不支持输入中文。

    Args:
        text (str): 要输入的英文/数字内容
        interval (float): 每个字符输入的间隔时间（秒），模拟人类打字速度。

    Returns:
        str: 执行结果
    """
    import pyautogui
    pyautogui.write(text, interval=interval)
    return f"Typed text: {text}"


@tool
def press_key(keys: str) -> str:
    """
    按下并释放一个或多个键盘按键。
    如果是普通按键（如 'enter', 'esc', 'space', 'backspace'），直接传入名称。
    如果是组合键（如 Ctrl+C），请用加号连接，例如 'ctrl+c' 或 'alt+f4'。

    Args:
        keys (str): 按键名称或组合键字符串。
                    常见按键: 'enter', 'esc', 'tab', 'space', 'backspace', 'up', 'down', 'left', 'right'.
                    组合键示例: 'ctrl+c', 'ctrl+v', 'alt+tab', 'win+r'.

    Returns:
        str: 执行结果
    """
    import pyautogui

    # 处理组合键逻辑
    if '+' in keys:
        key_list = keys.split('+')
        # 去除空格
        key_list = [k.strip() for k in key_list]
        # 执行组合键 (例如: hotkey('ctrl', 'c'))
        pyautogui.hotkey(*key_list)
        return f"Pressed hotkey: {keys}"
    else:
        # 执行单键
        pyautogui.press(keys.strip())
        return f"Pressed key: {keys}"


@tool
def mouse_click_with_key(key: str, x: int, y: int) -> str:
    """
    键盘与鼠标联动：按住某个键的同时点击鼠标左键。
    常用于多选文件（Ctrl+Click）或连续选择（Shift+Click）。

    Args:
        key (str): 要按住的修饰键，通常是 'ctrl', 'shift', 'alt' 或 'command'。
        x (int): 点击位置 X
        y (int): 点击位置 Y

    Returns:
        str: 执行结果
    """
    import pyautogui

    pyautogui.keyDown(key)  # 按下键不放
    pyautogui.click(x, y)  # 点击鼠标
    pyautogui.keyUp(key)  # 松开键

    return f"Held '{key}' and clicked at ({x}, {y})"


@tool
def paste_text_to_input(text: str) -> str:
    """
    [推荐] 将文本粘贴到当前输入框。
    比 type_text 更快，且完美支持中文输入。

    原理：将文本复制到系统剪贴板，然后模拟 Ctrl+V (或 Cmd+V) 粘贴。

    Args:
        text (str): 要输入的任意文本（支持中文、特殊符号）。

    Returns:
        str: 执行结果
    """
    import pyautogui
    import pyperclip  # 需要安装: pip install pyperclip
    import platform
    import time

    # 1. 写入剪贴板
    pyperclip.copy(text)

    # 2. 判断系统，选择粘贴快捷键
    # Mac 使用 Command+V，Windows/Linux 使用 Ctrl+V
    modifier_key = 'command' if platform.system() == 'Darwin' else 'ctrl'

    # 3. 执行粘贴
    # 稍微等待一下确保剪贴板已更新
    time.sleep(0.1)
    pyautogui.hotkey(modifier_key, 'v')

    return f"Pasted text: {text}"


ai_auto_control_agent_tools = [
    capture_screenshot_for_ai,
    get_screen_size,
    get_mouse_position,
    move_mouse,
    click_mouse,
    mouse_drag,
    scroll_screen,
    type_text,
    press_key,
    mouse_click_with_key,
    paste_text_to_input,
]