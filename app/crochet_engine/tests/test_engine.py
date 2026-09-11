import unittest
from crochet_engine import Gauge, ProfilePoint, compile_project, sphere_profile, tapered_profile, distribute_delta

class TestGeometryEngine(unittest.TestCase):
    def test_increase_count(self):
        r = distribute_delta(24, 30)
        self.assertEqual(r.increases, 6)
        self.assertEqual(r.after, 30)
        self.assertTrue(r.stitch_count_ok)

    def test_decrease_count(self):
        r = distribute_delta(30, 24)
        self.assertEqual(r.decreases, 6)
        self.assertEqual(r.after, 24)
        self.assertTrue(r.stitch_count_ok)

    def test_profile_compiles(self):
        g = Gauge(30, 32)
        p = sphere_profile(8, 8, .32)
        project = compile_project("Sfera", p, g)
        self.assertTrue(all("ERRORE:" not in x for x in project.checks))
        self.assertGreater(project.shape.max_stitches, 0)

    def test_taper(self):
        g = Gauge(30, 32)
        p = tapered_profile(6, 1.5, 10, .32)
        project = compile_project("Coda", p, g)
        self.assertTrue(project.shape.max_stitches >= 3)
        self.assertTrue(any("conteggi" in x.lower() for x in project.checks))

if __name__ == "__main__":
    unittest.main()
