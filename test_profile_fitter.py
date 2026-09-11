import cv2
from pathlib import Path
from app.crochet_engine import dinosaur_shape_graph, fit_graph_to_image

p = Path(__file__).resolve().parent / 'app' / 'static' / 'demo-dinosaur.png'
img = cv2.imread(str(p))
assert img is not None

g = dinosaur_shape_graph(scale=1.0)
r = fit_graph_to_image(g, img, 15)
assert r.foreground_area > 100000
assert r.px_per_cm > 10
assert r.mean_confidence > 0.2
assert len(r.nodes) == len(g.nodes)
print('profile fitter OK', round(r.mean_confidence, 3), 'px/cm', round(r.px_per_cm, 2))
