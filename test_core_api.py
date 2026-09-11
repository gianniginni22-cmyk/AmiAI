import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestCoreAPI(unittest.TestCase):
    def test_generate_endpoint_exists(self):
        routes={r.path for r in app.routes}
        self.assertIn('/api/generate', routes)

if __name__ == '__main__': unittest.main()


class TestUIDataContract(unittest.TestCase):
    def test_compile_design_exposes_displayable_part_names(self):
        from app.crochet_engine.design_model import fallback_design
        from app.crochet_engine.pipeline import compile_design
        design = fallback_design('castoro antropomorfo', 15, 'fedele alla foto')
        out = compile_design(design, 15, 2.5)
        self.assertIsInstance(out.get('parts'), list)
        self.assertTrue(all(isinstance(x, str) for x in out['parts']))
        self.assertTrue(out.get('pattern', '').strip())
        self.assertTrue(out.get('assembly', '').strip())
