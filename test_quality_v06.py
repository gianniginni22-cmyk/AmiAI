from app.crochet_engine import Gauge, dinosaur_shape_graph
from app.crochet_engine.quality import assess_graph

def test_quality_dinosaur():
    g=dinosaur_shape_graph()
    p=g.compile(Gauge(30,32), include_details=True)
    q=assess_graph(g,p,15)
    assert q.gates['graph_valid']
    assert q.gates['stitch_counts']
    assert q.gates['joints_resolvable']
    assert q.score>50

def test_all_parts_rounds_are_count_valid():
    g=dinosaur_shape_graph(); p=g.compile(Gauge(30,32), include_details=True)
    for part in p.parts.values():
        for r in part.shape.rounds:
            assert r.after==r.before+r.increases-r.decreases


def test_quality_has_percentage_components():
    g=dinosaur_shape_graph(); p=g.compile(Gauge(30,32), include_details=True)
    q=assess_graph(g,p,15).to_dict()
    c=q['metrics']['component_scores']
    assert set(c)=={'visione','struttura_grafo','geometria','conteggi_maglie','giunzioni','scala_target'}
    assert all(0 <= v <= 100 for v in c.values())
    assert 0 <= q['score'] <= 100
