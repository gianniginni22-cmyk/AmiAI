import unittest
from app.crochet_engine.benchmark import BenchmarkCase, run_benchmark, run_standard_benchmark, standard_cases


class TestCore008Benchmark(unittest.TestCase):
    def test_standard_multi_subject_benchmark_passes(self):
        report = run_standard_benchmark()
        self.assertEqual(report["benchmark"], "CORE-008")
        self.assertEqual(report["case_count"], 6)
        self.assertEqual(report["passed_cases"], 6)
        self.assertEqual(report["failed_cases"], 0)
        self.assertTrue(report["pass"])
        self.assertGreaterEqual(report["reference_match_avg"], 90)
        self.assertGreaterEqual(report["pattern_validity_avg"], 80)

    def test_wrong_subject_is_not_a_reference_match(self):
        case = standard_cases()[0]
        wrong = dict(case.design)
        wrong["subject"] = "Kangaroo"
        wrong["semantic_summary"] = "animale saltatore con coda lunga"
        wrong["distinctive_features"] = ["zampe posteriori grandi"]
        result = run_benchmark([BenchmarkCase("wrong", wrong, case.expected_roles, case.required_features, case.expected_subject_tokens)])
        self.assertLess(result["cases"][0]["reference_match"], 80)
        self.assertFalse(result["cases"][0]["pass"])

    def test_each_case_has_independent_structural_gates(self):
        report = run_standard_benchmark()
        for case in report["cases"]:
            self.assertTrue(all(case["independent_gates"].values()), case)


if __name__ == "__main__":
    unittest.main()
