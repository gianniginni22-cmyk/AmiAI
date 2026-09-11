import unittest
from app.main import fallback, compile_graph

class TestMVPShapeGraphIntegration(unittest.TestCase):
    def test_fallback_goes_through_shape_graph_and_engine(self):
        result = compile_graph(fallback("dinosauro verde", 15, 2.5), 15, 2.5)
        graph = result["shape_graph"]
        validation = result["_graph_validation"]
        self.assertEqual(graph["version"], "0.2")
        self.assertEqual(validation["node_count"], 16)
        self.assertEqual(validation["edge_count"], 15)
        self.assertEqual(validation["pattern_part_count"], 9)
        self.assertTrue(validation["ok"])
        self.assertIn("PROJECT — Dinosauro amigurumi", result["pattern"])
        self.assertIn("Unisci", result["assembly"])

if __name__ == "__main__":
    unittest.main()
