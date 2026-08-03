"""
单例基础设施

提供线程安全的单例元类，替代散落在各处的 ``__new__`` + ``_initialized`` 写法。
"""
import threading
from typing import Any, ClassVar, Dict


class SingletonMeta(type):
    """
    线程安全的单例元类。

    使用方式::

        class Foo(metaclass=SingletonMeta):
            def __init__(self, x: int = 1):
                self.x = x

        Foo() is Foo()  # True

    相比 ``__new__`` + ``_initialized`` 标志位的手写方案：
    1. ``__init__`` 只会执行一次，无需在初始化逻辑里加守卫；
    2. 每个子类持有独立实例，不会互相覆盖；
    3. 双重检查锁保证多线程（如 Streamlit 的 script runner）下的唯一性。
    """

    _instances: ClassVar[Dict[type, Any]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in SingletonMeta._instances:
            with SingletonMeta._lock:
                # 二次检查：可能在等锁期间已被其它线程创建
                if cls not in SingletonMeta._instances:
                    SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta._instances[cls]

    def clear_instance(cls) -> None:
        """丢弃已缓存的实例（主要供测试或热重载使用）。"""
        with SingletonMeta._lock:
            SingletonMeta._instances.pop(cls, None)
