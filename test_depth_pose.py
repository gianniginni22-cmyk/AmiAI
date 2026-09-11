import unittest
import cv2
import numpy as np
from app.crochet_engine import dinosaur_shape_graph, estimate_depth_pose

class DepthPoseTests(unittest.TestCase):
    def test_estimator_updates_graph(self):
        img = cv2.imread('app/static/demo-dinosaur.png')
        graph = dinosaur_shape_graph(scale=1.0)
        report = estimate_depth_pose(graph, img, 15)
        self.assertGreaterEqual(len(report.estimates), 1)
        self.assertIn('depth_pose', graph.nodes['body'].metadata)
        self.assertTrue(-1 <= report.estimates['body'].relative_depth <= 1)

    def test_json_serializable(self):
        img = cv2.imread('app/static/demo-dinosaur.png')
        graph = dinosaur_shape_graph(scale=1.0)
        report = estimate_depth_pose(graph, img, 15)
        data = report.to_dict()
        self.assertIn('estimates', data)
        self.assertIn('body', data['estimates'])

if __name__ == '__main__':
    unittest.main()
