"""Resume insights: bullet evidence, honest checklist, no fake benchmarks."""

from models.resume_feedback import get_overall_summary
from studybuddy.resume_insights import (
    analyze_bullets, build_fix_checklist, dimension_notes)

TEXT = """John Doe
john@example.com
Experience
• Built a payment API serving 20000 users and reduced latency by 40%.
• Responsible for various tasks and helped with stuff.
• Worked on the dashboard.
Projects
• Created a chatbot that increased engagement by 25%.
"""

SECTIONS = {
    'summary': 'Software engineer.',
    'experience': ('• Built a payment API serving 20000 users and reduced '
                   'latency by 40%.\n• Responsible for various tasks and '
                   'helped with stuff.\n• Worked on the dashboard.'),
    'projects': '• Created a chatbot that increased engagement by 25%.',
    'skills': 'Python, SQL, Docker',
}


def _ats(**over):
    base = {
        'percentage': 62.0,
        'breakdown': {
            'sections': {'score': 15, 'max': 20, 'label': 'Sections',
                         'details': '3/4 essential sections'},
            'skills': {'score': 10, 'max': 25, 'label': 'Skills',
                       'details': '3 skills found across 1 categories'},
            'content': {'score': 12, 'max': 20, 'label': 'Content',
                        'details': '60 words, 2 action verbs'},
            'contact': {'score': 3, 'max': 10, 'label': 'Contact',
                        'details': ('Email: ✓, Phone: ✗, LinkedIn: ✗, '
                                    'GitHub/Portfolio: ✗')},
            'experience': {'score': 5, 'max': 15, 'label': 'Experience',
                           'details': '~0 years'},
            'formatting': {'score': 5, 'max': 10, 'label': 'Formatting',
                           'details': '12 lines, 4 sections'},
        },
    }
    base['breakdown'].update(over)
    return base


def test_bullet_evidence_counts_and_reasons():
    bi = analyze_bullets(TEXT, SECTIONS)
    assert bi['total'] == 4
    assert bi['quantified'] == 2
    assert bi['quantified_pct'] == 50
    assert bi['strong_example'].startswith('Built a payment API')
    weak_texts = [w['text'] for w in bi['weak']]
    assert any('Responsible for various tasks' in t for t in weak_texts)
    weak = next(w for w in bi['weak'] if 'Responsible' in w['text'])
    assert len(weak['reasons']) >= 2


def test_no_bullets_is_not_an_error():
    bi = analyze_bullets('Just a paragraph, no bullets at all.', {})
    assert bi['total'] == 0
    assert bi['quantified_pct'] == 0
    assert bi['weak'] == []


def test_cleaned_text_without_glyphs_still_yields_bullets():
    # Regression: clean_text() strips •, so marker-only detection found
    # zero bullets on real cleaned resumes. Substantive section lines
    # must be detected, while the role/company header is skipped.
    cleaned_sections = {
        'experience': ('Backend Engineer, Acme Corp\n'
                       'Built a payment API serving 20000 users and '
                       'reduced latency by 40%.\n'
                       'Responsible for various tasks and helped with stuff.'),
        'projects': 'Created a chatbot that increased engagement by 25%.',
    }
    bi = analyze_bullets('cleaned text without markers', cleaned_sections)
    assert bi['total'] == 3
    assert bi['quantified'] == 2
    assert not any('Backend Engineer' in w['text'] for w in bi['weak'])


def test_checklist_points_never_exceed_headroom():
    bi = analyze_bullets(TEXT, SECTIONS)
    fc = build_fix_checklist(_ats(), bi, SECTIONS, TEXT, num_skills=3)
    ats = _ats()
    for dim in ('sections', 'skills', 'content', 'contact', 'formatting'):
        dim_points = sum(i['points'] for i in fc['items']
                         if i['dimension'] == dim)
        headroom = (ats['breakdown'][dim]['max']
                    - ats['breakdown'][dim]['score'])
        assert dim_points <= headroom + 1e-9, (dim, dim_points, headroom)
    assert fc['projected_pct'] <= 100
    assert fc['projected_pct'] == round(
        min(100, 62.0 + fc['total_points']), 1)


def test_checklist_skips_dimensions_with_no_headroom():
    ats = _ats()
    ats['breakdown']['contact'] = {'score': 10, 'max': 10, 'label': 'Contact',
                                   'details': ('Email: ✓, Phone: ✓, '
                                               'LinkedIn: ✓, GitHub/Portfolio: ✓')}
    bi = analyze_bullets(TEXT, SECTIONS)
    fc = build_fix_checklist(ats, bi, SECTIONS, TEXT, num_skills=3)
    assert not [i for i in fc['items'] if i['dimension'] == 'contact']


def test_dimension_notes_link_fixes():
    bi = analyze_bullets(TEXT, SECTIONS)
    fc = build_fix_checklist(_ats(), bi, SECTIONS, TEXT, num_skills=3)
    notes = dimension_notes(_ats(), bi, SECTIONS, fc)
    assert notes['contact']['lost'] == 7.0
    assert 'add-phone' in notes['contact']['fix_ids']
    assert notes['experience']['fix_ids'] == []


def test_summary_makes_no_percentile_claim():
    # Regression: the old "top 10% of applicants" template line.
    ats = {'percentage': 75.0, 'total_score': 75.0,
           'breakdown': _ats()['breakdown']}
    summary = get_overall_summary(ats, [], {'experience': 'x'})
    assert 'top 10%' not in summary
    assert 'percentile' not in summary.lower()
