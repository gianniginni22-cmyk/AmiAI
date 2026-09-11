import unittest
from app.crochet_engine.pipeline import design_to_shape_graph, compile_design
from app.crochet_engine.shape_graph import ShapeNode, Vec3, Euler, ConnectionPoint

class TestPose005(unittest.TestCase):
    def test_semantic_pose_is_preserved(self):
        d={"subject":"fox","overall_confidence":.9,"parts":[
            {"id":"body","label":"corpo","role":"body","count":1,"parent_id":None,"symmetry_group":None,"estimated_height_cm":10,"estimated_width_cm":8,"estimated_depth_cm":6,"center_front":{"x":.5,"y":.55},"center_side":{"x":.5,"y":.55},"depth_hint":"front","confidence":.9,"construction":"forma"},
            {"id":"tail","label":"coda","role":"tail","count":1,"parent_id":"body","symmetry_group":None,"estimated_height_cm":6,"estimated_width_cm":2,"estimated_depth_cm":1,"center_front":{"x":.25,"y":.6},"center_side":{"x":.8,"y":.6},"depth_hint":"dietro","confidence":.9,"construction":"tubo affusolato"}]}
        g=design_to_shape_graph(d,15); tail=next(n for n in g['nodes'] if n['id']=='tail')
        self.assertNotEqual(tail['rotation']['ry'],0); self.assertEqual(tail['metadata']['pose_source'],'semantic_anchors'); self.assertGreater(abs(tail['position']['y']),0)
    def test_world_connection_applies_rotation(self):
        n=ShapeNode('n','test',position=Vec3(0,0,0),rotation=Euler(0,90,0)); n.add_connection(ConnectionPoint('top',Vec3(0,0,10),1,'join')); p=n.world_connection('top')
        self.assertAlmostEqual(p.x,10,places=5); self.assertAlmostEqual(p.z,0,places=5)
    def test_compile_has_pose_and_assembly(self):
        d={"subject":"test","overall_confidence":.9,"parts":[
            {"id":"body","label":"corpo","role":"body","count":1,"parent_id":None,"symmetry_group":None,"estimated_height_cm":10,"estimated_width_cm":8,"estimated_depth_cm":6,"center_front":{"x":.5,"y":.5},"center_side":{"x":.5,"y":.5},"depth_hint":"front","confidence":.9,"construction":"forma"},
            {"id":"arm","label":"braccio","role":"arm","count":1,"parent_id":"body","symmetry_group":None,"estimated_height_cm":4,"estimated_width_cm":2,"estimated_depth_cm":2,"center_front":{"x":.25,"y":.55},"center_side":{"x":.5,"y":.55},"depth_hint":"front","confidence":.9,"construction":"tubo"}]}
        out=compile_design(d,15,2.5); self.assertEqual(out['pose']['status'],'semantic'); self.assertIn('braccio',out['assembly']); self.assertTrue(out['graph_validation']['ok'])
if __name__=='__main__': unittest.main()
