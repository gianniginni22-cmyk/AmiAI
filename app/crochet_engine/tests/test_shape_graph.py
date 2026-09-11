import unittest
from crochet_engine import (
    Gauge, ShapeGraph, ShapeNode, ConnectionPoint, Vec3,
    ProfilePoint, ShapeEdge, dinosaur_shape_graph,
)


class TestShapeGraph(unittest.TestCase):
    def test_basic_graph_validation(self):
        g = ShapeGraph("test")
        a = ShapeNode("a", "A", profile=[ProfilePoint(0, 2), ProfilePoint(1, 2)])
        b = ShapeNode("b", "B", profile=[ProfilePoint(0, 1.5), ProfilePoint(1, 1)])
        a.add_connection(ConnectionPoint("out", Vec3(0, 0, 1), 1.0))
        b.add_connection(ConnectionPoint("in", Vec3(0, 0, 0), 1.0))
        g.add_node(a).add_node(b).connect("ab", "a", "out", "b", "in")
        v = g.validate()
        self.assertTrue(v.ok, v.errors)
        self.assertEqual(g.roots(), ["a"])
        self.assertEqual(g.children("a"), ["b"])

    def test_serialization_roundtrip(self):
        original = dinosaur_shape_graph()
        restored = ShapeGraph.from_json(original.to_json())
        self.assertEqual(set(original.nodes), set(restored.nodes))
        self.assertEqual(set(original.edges), set(restored.edges))
        self.assertEqual(restored.nodes["body"].connections["neck"].radius_cm,
                         original.nodes["body"].connections["neck"].radius_cm)

    def test_dinosaur_graph_compiles(self):
        g = dinosaur_shape_graph()
        v = g.validate()
        self.assertTrue(v.ok, v.errors)
        project = g.compile(Gauge(30, 32), include_details=True)
        self.assertEqual(len(project.parts), 9)  # body, neck, head, muzzle, tail, 4 legs
        self.assertEqual(len(g.nodes), 16)
        self.assertEqual(len(g.edges), 15)
        self.assertTrue(any("giunzioni" in c for c in project.checks))

    def test_cycle_is_rejected(self):
        g = ShapeGraph("cycle")
        for node_id in ("a", "b"):
            n = ShapeNode(node_id, node_id)
            n.add_connection(ConnectionPoint("p", Vec3()))
            g.add_node(n)
        g.connect("ab", "a", "p", "b", "p")
        g.connect("ba", "b", "p", "a", "p")
        v = g.validate()
        self.assertFalse(v.ok)
        self.assertTrue(any("Ciclo" in e for e in v.errors))


if __name__ == "__main__":
    unittest.main()
