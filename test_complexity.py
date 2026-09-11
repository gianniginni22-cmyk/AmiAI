from app.crochet_engine.complexity import analyze_complexity

def test_text_complexity():
    r=analyze_complexity(None,'animale con quattro zampe, coda, orecchie, occhi e piccole macchie decorative')
    assert 0 <= r.score <= 100
    assert r.level in {'semplice','medio','complesso','molto complesso'}

def test_empty_input():
    r=analyze_complexity(None,'')
    assert r.confidence == 0.0
    assert r.score >= 0
