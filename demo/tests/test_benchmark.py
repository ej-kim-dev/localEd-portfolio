"""The benchmark doubles as a regression test: every case must keep passing."""

import unittest

from benchmark.run import run


class Benchmark(unittest.TestCase):
    def test_all_benchmark_cases_pass(self):
        res = run()
        failed = [r["case"] for r in res["cases"] if not r["pass"]]
        self.assertEqual(failed, [], f"benchmark cases failing: {failed}")


if __name__ == "__main__":
    unittest.main()
