"""SingletonMeta 单元测试"""
import threading
import unittest

from utils import SingletonMeta


class TestSingletonMeta(unittest.TestCase):
    def setUp(self):
        class Counter(metaclass=SingletonMeta):
            instances = 0

            def __init__(self, value: int = 0):
                type(self).instances += 1
                self.value = value

        self.Counter = Counter
        self.addCleanup(Counter.clear_instance)

    def test_returns_same_instance(self):
        self.assertIs(self.Counter(1), self.Counter(2))

    def test_init_runs_only_once(self):
        self.Counter(1)
        self.Counter(2)
        self.assertEqual(self.Counter.instances, 1)
        self.assertEqual(self.Counter().value, 1)

    def test_subclasses_get_independent_instances(self):
        class Other(metaclass=SingletonMeta):
            pass

        self.addCleanup(Other.clear_instance)
        self.assertIsNot(self.Counter(), Other())

    def test_clear_instance_allows_recreation(self):
        first = self.Counter()
        self.Counter.clear_instance()
        self.assertIsNot(self.Counter(), first)

    def test_thread_safe_single_construction(self):
        results = []
        barrier = threading.Barrier(8)

        def create():
            barrier.wait()
            results.append(self.Counter())

        threads = [threading.Thread(target=create) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(set(map(id, results))), 1)
        self.assertEqual(self.Counter.instances, 1)


if __name__ == "__main__":
    unittest.main()
