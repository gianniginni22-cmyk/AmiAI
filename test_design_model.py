import json
from app.crochet_engine.design_model import DESIGN_SCHEMA, fallback_design, build_design_prompt


def test_design_schema_is_strict_and_complete():
    assert DESIGN_SCHEMA['additionalProperties'] is False
    assert set(DESIGN_SCHEMA['required']) == set(DESIGN_SCHEMA['properties'])
    assert len(DESIGN_SCHEMA['properties']['views']['items']['required']) == 3


def test_fallback_design_has_four_views_and_parts():
    d = fallback_design('orsetto', 15, 'fedele alla foto', [
        {'id':'body','label':'corpo','role':'body','symmetry_group':None,'confidence':.8,'notes':''},
        {'id':'ear1','label':'orecchio 1','role':'ear','symmetry_group':'ears','confidence':.7,'notes':''},
    ])
    assert d['subject'] == 'orsetto'
    assert [v['orientation'] for v in d['views']] == ['frontale','posteriore','sinistra','destra']
    assert len(d['parts']) == 2
    assert d['parts'][1]['count'] == 2


def test_concept_prompt_protects_subject_identity():
    d = fallback_design('orsetto', 15, 'fedele alla foto')
    d['distinctive_features'] = ['muso nero', 'orecchie arrotondate']
    prompt = build_design_prompt('orsetto', 15, 'fedele alla foto', d)
    assert 'Non trasformare il soggetto in un altro animale' in prompt
    assert 'muso nero' in prompt
