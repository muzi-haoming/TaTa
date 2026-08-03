import pyautogui
import time
import sys

# 设置pyautogui的故障保护机制。当鼠标移动到屏幕左上角(0,0)时，程序将中止。
pyautogui.FAILSAFE = True

def search_and_open_app(app_name: str = "weixin"):
    """
    点击Windows任务栏的搜索图标，输入应用程序名称，然后按回车键打开它。
    """
    try:
        # 获取屏幕分辨率，以便计算相对坐标
        screen_width, screen_height = pyautogui.size()
        print(f"检测到的屏幕分辨率: {screen_width}x{screen_height}")

        # --- 根据截图分析确定坐标 ---
        # 1. 任务栏高度:
        #    从截图来看，Windows 10/11的任务栏高度通常在48像素左右。
        #    任务栏位于屏幕底部。
        # 2. 搜索图标位置:
        #    搜索图标 (放大镜) 位于任务栏的左侧，在Windows开始按钮的右边。
        #    水平位置 (X轴): 从截图估算，搜索图标中心大约在屏幕左侧105像素处。
        #    垂直位置 (Y轴): 任务栏的中心位置。如果任务栏高48像素，则其中心在
        #    屏幕底部边缘上方24像素处 (screen_height - 24)。
        
        search_icon_x = 105  # 搜索图标中心距离屏幕左边缘的像素距离
        search_icon_y = screen_height - 24 # 搜索图标中心距离屏幕顶部的像素距离 (屏幕高度 - 任务栏中心点到屏幕底部的距离)

        print(f"尝试点击搜索图标，坐标: X:{search_icon_x}, Y:{search_icon_y}")
        
        # 步骤 1: 点击任务栏中的搜索图标/搜索框
        # pyautogui.click() 会将鼠标移动到指定坐标并点击
        pyautogui.click(x=search_icon_x, y=search_icon_y)
        print("已点击搜索图标。")
        time.sleep(1.5) # 等待搜索栏或搜索界面出现

        # 步骤 2: 输入 "weixin" 到搜索框
        print(f"正在搜索框中输入: '{app_name}'。")
        pyautogui.write(app_name)
        time.sleep(1.5) # 等待搜索结果加载

        # 步骤 3: 按下回车键打开排名第一的搜索结果 (通常就是微信)
        print("按下回车键以打开应用程序。")
        pyautogui.press("enter")
        time.sleep(3) # 等待应用程序启动

        print(f"成功尝试打开 '{app_name}'。")

    except pyautogui.FailSafeException:
        print("\n错误: PyAutoGUI 故障保护已触发 (鼠标移动到屏幕左上角)。")
        print("自动化操作已中止。")
    except pyautogui.PyAutoGUIException as e:
        print(f"\n错误: 发生 PyAutoGUI 错误: {e}")
        print("请确保屏幕可见，并且鼠标没有被阻挡。")
    except Exception as e:
        print(f"\n发生未知错误: {e}")
        print("请检查您的环境并重试。")
    finally:
        print("脚本执行完毕。")

if __name__ == "__main__":
    search_and_open_app("weixin")