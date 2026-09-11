import unittest
from app.crochet_engine.pipeline import design_to_shape_graph, compile_design
from app.crochet_engine.engine import ProfilePoint, Gauge, diameter_to_stitches

class TestAnisotropicGeometry(unittest.TestCase):
    def test_width_depth_are_preserved(self):
        design={"subject":"fox","overall_confidence":.95,"parts":[
            {"id":"body","label":"corpo","role":"body","count":1,"estimated_height_cm":10,"estimated_width_cm":8,"estimated_depth_cm":4,"construction":"forma principale"},
            {"id":"head","label":"testa","role":"head","count":1,"parent_id":"body","estimated_height_cm":5,"estimated_width_cm":6,"estimated_depth_cm":3,"construction":"muso allungato"}
        ]}
        g=design_to_shape_graph(design,15)
        body=next(n for n in g['nodes'] if n['id']=='body')
        self.assertTrue(all('width_cm' in p and 'depth_cm' in p for p in body['profile']))
        self.assertNotEqual(body['profile'][0]['width_cm'], body['profile'][0]['depth_cm'])

    def test_anisotropic_profile_changes_stitch_equivalent(self):
        radial=ProfilePoint(0, 6)
        ellipse=ProfilePoint(0, 8, width_cm=10, depth_cm=6)
        self.assertNotEqual(radial.diameter_cm, ellipse.diameter_cm)

    def test_compilation_still_valid(self):
        design={"subject":"test","overall_confidence":.9,"parts":[
            {"id":"body","label":"corpo","role":"body","count":1,"estimated_height_cm":10,"estimated_width_cm":8,"estimated_depth_cm":5,"construction":"forma principale"},
            {"id":"tail","label":"coda","role":"tail","count":1,"parent_id":"body","estimated_height_cm":6,"estimated_width_cm":2,"estimated_depth_cm":1,"construction":"tubo affusolato"}]}
        out=compile_design(design,15,2.5)
        self.assertTrue(out['graph_validation']['ok'])
        self.assertIn('PROJECT',out['pattern'])

if __name__=='__main__': unittest.main()
