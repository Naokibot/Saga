from __future__ import annotations

import os
import unittest

from saga import compile_source, run_source


class SagaUnboundedParallel080Tests(unittest.TestCase):
    def test_function_arity_is_not_capped_at_64(self):
        names = [f"p{i}" for i in range(80)]
        params = ", ".join(f"{name}: int" for name in names)
        args = ", ".join("1" for _ in names)
        source = f"fn many({params}) -> int = p0 + p79\nprint(many({args}))"
        output: list[str] = []
        run_source(source, output=output.append)
        self.assertEqual(output, ["2"])

    def test_precision_has_no_saga_fixed_upper_ceiling(self):
        output: list[str] = []
        run_source('precision(20000)\nprint(1 / 3)', output=output.append)
        self.assertTrue(output[0].startswith("1/3"))

    def test_thread_pool_has_no_saga_256_worker_ceiling(self):
        output: list[str] = []
        run_source('use task\nlet pool = task.pool(257)\ntask.shutdown(pool)\nprint("ok")', output=output.append)
        self.assertEqual(output, ["ok"])

    def test_cpu_map_and_reduce(self):
        output: list[str] = []
        source = '''
        use task
        fn square(x: int) -> int = x * x
        fn add(a: int, b: int) -> int = a + b
        print(task.cpu_map(square, [1, 2, 3, 4, 5], 2))
        print(task.cpu_reduce(add, [1, 2, 3, 4], 0, 2))
        '''
        run_source(source, output=output.append)
        self.assertEqual(output, ["[1, 4, 9, 16, 25]", "10"])

    @unittest.skipIf((os.cpu_count() or 1) < 2, "parallel PID test needs at least two logical CPUs")
    def test_cpu_map_uses_multiple_processes(self):
        output: list[str] = []
        source = '''
        use task
        use time
        fn worker(x: int) -> int {
            time.sleep(0.05)
            return task.process_id()
        }
        print(unique(task.cpu_map(worker, [1,2,3,4,5,6,7,8], 4)))
        '''
        run_source(source, output=output.append)
        payload = output[0].strip()[1:-1].strip()
        pids = {part.strip() for part in payload.split(",") if part.strip()}
        self.assertGreaterEqual(len(pids), 2)


if __name__ == "__main__":
    unittest.main()
