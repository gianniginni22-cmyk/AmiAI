import unittest
from app.crochet_engine.pipeline import design_to_shape_graph, compile_design

class TestCorePipeline(unittest.TestCase):
    def design(self):
        return {
            "subject":"Orsetto di prova",
            "overall_confidence":0.9,
            "parts":[
                {"id":"body","label":"Corpo","role":"body","count":1,"parent_id":None,"symmetry_group":None,"estimated_height_cm":10,"estimated_width_cm":8,"estimated_depth_cm":6,"confidence":.95,"construction":"forma principale"},
                {"id":"head","label":"Testa","role":"head","count":1,"parent_id":"body","symmetry_group":None,"estimated_height_cm":6,"estimated_width_cm":6,"estimated_depth_cm":5,"confidence":.95,"construction":"forma ovale"},
                {"id":"arm","label":"Braccio","role":"arm","count":2,"parent_id":"body","symmetry_group":"arms","estimated_height_cm":4,"estimated_width_cm":2,"estimated_depth_cm":2,"confidence":.9,"construction":"tubo"},
                {"id":"eye","label":"Occhio","role":"eye","count":2,"parent_id":"head","symmetry_group":"eyes","estimated_height_cm":1,"estimated_width_cm":1,"estimated_depth_cm":.6,"confidence":.9,"construction":"ricamo"},
            ]
        }

    def test_design_compiles_without_ai_reinterpretation(self):
        out=compile_design(self.design(),15,2.5)
        self.assertTrue(out["graph_validation"]["ok"])
        self.assertIn("PROJECT", out["pattern"])
        self.assertGreaterEqual(len(out["shape_graph"]["nodes"]), 5)
        self.assertTrue(any("tubo_sc" in str(x) for x in out["techniques"]))

    def test_parent_and_symmetry_are_preserved(self):
        g=design_to_shape_graph(self.design(),15)
        self.assertEqual(len(g["edges"]), len(g["nodes"])-1)
        arm_nodes=[n for n in g["nodes"] if n.get("symmetry_group")=="arms"]
        self.assertEqual(len(arm_nodes),2)

if __name__ == '__main__': unittest.main()

class TestGeometryShapeCues(unittest.TestCase):
    def test_distinctive_shape_cues_change_primitive(self):
        from app.crochet_engine.pipeline import design_to_shape_graph
        base = {
            'subject':'test', 'overall_confidence':.9,
            'parts': [
                {'id':'body','label':'corpo','role':'body','count':1,'parent_id':None,'symmetry_group':None,
                 'estimated_height_cm':10,'estimated_width_cm':6,'estimated_depth_cm':4,
                 'center_front':{'x':.5,'y':.5},'center_side':{'x':.5,'y':.5},'depth_hint':'front',
                 'confidence':.9,'construction':'forma principale','notes':''},
                {'id':'tail','label':'coda lunga affusolata','role':'tail','count':1,'parent_id':'body','symmetry_group':None,
                 'estimated_height_cm':8,'estimated_width_cm':2,'estimated_depth_cm':1.5,
                 'center_front':{'x':.2,'y':.6},'center_side':{'x':.2,'y':.6},'depth_hint':'side',
                 'confidence':.9,'construction':'tubo affusolato','notes':'lunga e appuntita'}]}
        g=design_to_shape_graph(base,15)
        tail=next(n for n in g['nodes'] if n['id']=='tail')
        self.assertEqual(tail['primitive'],'tail')
        self.assertLess(tail['profile'][-1]['diameter_cm'], tail['profile'][0]['diameter_cm'])
