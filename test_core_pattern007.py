import unittest
from app.crochet_engine.pipeline import compile_design

class TestPattern007(unittest.TestCase):
    def test_pattern_is_buildable_document(self):
        d={"subject":"test","overall_confidence":.9,"parts":[
            {"id":"body","label":"Corpo","role":"body","count":1,"parent_id":None,"symmetry_group":None,
             "estimated_height_cm":10,"estimated_width_cm":8,"estimated_depth_cm":6,"center_front":{"x":.5,"y":.5},"center_side":{"x":.5,"y":.5},"depth_hint":"front","confidence":.9,"construction":"forma principale","notes":""},
            {"id":"arm","label":"Braccio","role":"arm","count":1,"parent_id":"body","symmetry_group":None,
             "estimated_height_cm":4,"estimated_width_cm":2,"estimated_depth_cm":2,"center_front":{"x":.3,"y":.5},"center_side":{"x":.5,"y":.5},"depth_hint":"front","confidence":.9,"construction":"tubo","notes":""} ]}
        out=compile_design(d,15,2.5)
        p=out['pattern']
        self.assertIn('MATERIALI:',p); self.assertIn('FINITURA DEL PEZZO:',p)
        self.assertIn('Tecnica:',p); self.assertIn('Costruzione:',p); self.assertIn('ASSEMBLY',p)
        self.assertIn('Imbottire progressivamente',p)

if __name__=='__main__': unittest.main()
