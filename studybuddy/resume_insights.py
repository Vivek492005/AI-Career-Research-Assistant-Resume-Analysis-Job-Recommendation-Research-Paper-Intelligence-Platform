"""Bullet-level evidence and an honest fix checklist for resume results.

Everything here is derived from the resume text with the SAME rules as
``models/ats_scorer.py`` (same action-verb list, same metric pattern, same
tier table), so the checklist points can never promise more than the
scorer itself can award. Point estimates are capped per dimension at
that dimension's remaining headroom, and the projected score is capped
at 100. No external benchmark, percentile, or recruiter statistic is
claimed anywhere — the only comparison is this resume against its own
checklist math.
"""

import re

# Same 25 verbs as models/ats_scorer.py (kept in sync by test).
ACTION_VERBS = [
    'developed', 'designed', 'implemented', 'managed', 'created',
    'built', 'led', 'launched', 'improved', 'optimized', 'reduced',
    'increased', 'achieved', 'delivered', 'coordinated', 'analyzed',
    'established', 'maintained', 'automated', 'integrated', 'resolved',
    'collaborated', 'mentored', 'presented', 'published', 'engineered',
]

# Same metric pattern as models/ats_scorer.py.
METRIC_RE = re.compile(
    r'\d+[%+]|\$[\d,]+|\d+\s*(?:users|clients|projects|team|members)',
    re.IGNORECASE)

_BULLET_MARK = re.compile(r'^\s*(?:[•\-\*–—]\s+|\d+[.)]\s+)')
_WEAK_VERB_LEAD = re.compile(r'^(responsible for|worked on|helped with)\b',
                              re.IGNORECASE)

_MEASURES = {
    'sections': 'Whether the standard sections an ATS parser looks for are present.',
    'skills': 'How many distinct skills were found, and across how many categories.',
    'content': 'Length, action verbs, and quantified achievements in the text.',
    'contact': 'Email, phone, LinkedIn, and GitHub/portfolio links.',
    'experience': 'Years of experience detected — this comes from your history, not wording.',
    'formatting': 'Line count, section structure, and overall length.',
}


def _clean_bullet(line):
    line = _BULLET_MARK.sub('', line).strip()
    return re.sub(r'\s+', ' ', line)


_YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')


def _looks_like_header(line):
    """Job/role header lines, not achievement bullets: dated lines, or a
    short 'Role, Company' line."""
    words = line.split()
    if _YEAR_RE.search(line):
        return True
    if len(words) <= 6 and ',' in line:
        return True
    return False


def extract_bullets(resume_text, sections=None):
    """Bullet lines from experience/projects sections.

    The pipeline's clean_text() strips bullet glyphs (• is not in its
    allowed set), so marker lines alone find nothing on real cleaned
    resumes. Detection is therefore two-stage: explicit markers when
    present, plus substantive section lines (long enough, not a
    role/company header) as the fallback that actually fires.
    """
    sections = sections or {}
    bullets, seen = [], set()

    def _add(line):
        b = _clean_bullet(line)
        if len(b) >= 10 and b.lower() not in seen:
            seen.add(b.lower())
            bullets.append(b)

    for key in ('experience', 'projects'):
        for line in (sections.get(key) or '').split('\n'):
            if _BULLET_MARK.match(line):
                _add(line)
    for key in ('experience', 'projects'):
        for line in (sections.get(key) or '').split('\n'):
            s = line.strip()
            if len(s) >= 20 and not _looks_like_header(s):
                _add(s)
    if not bullets:
        for line in (resume_text or '').split('\n'):
            if _BULLET_MARK.match(line):
                _add(line)
    return bullets


def _bullet_reasons(bullet):
    reasons = []
    if not METRIC_RE.search(bullet):
        reasons.append('No number or metric — the impact is unproven')
    first_word = (bullet.split() or [''])[0].lower()
    if first_word not in ACTION_VERBS:
        reasons.append('Does not start with an action verb')
    if _WEAK_VERB_LEAD.match(bullet):
        reasons.append('Passive phrasing — lead with what you did')
    if len(bullet.split()) > 30:
        reasons.append('Too long — one bullet should carry one achievement')
    return reasons


def analyze_bullets(resume_text, sections=None):
    """Bullet-level evidence: quantified share + weakest bullets with reasons."""
    bullets = extract_bullets(resume_text, sections)
    quantified = [b for b in bullets if METRIC_RE.search(b)]
    unique_metrics = {m.strip().lower()
                      for m in METRIC_RE.findall(resume_text or '')}
    verbs_found = sum(
        1 for v in ACTION_VERBS
        if re.search(r'\b' + re.escape(v) + r'\b', (resume_text or '').lower()))
    weak = []
    for b in bullets:
        reasons = _bullet_reasons(b)
        if reasons:
            weak.append({'text': b[:180], 'reasons': reasons})
    weak.sort(key=lambda w: -len(w['reasons']))
    return {
        'total': len(bullets),
        'quantified': len(quantified),
        'quantified_pct': round(100 * len(quantified) / len(bullets))
        if bullets else 0,
        'unique_metrics': len(unique_metrics),
        'verbs_found': verbs_found,
        'weak': weak[:5],
        'strong_example': quantified[0][:180] if quantified else None,
    }


def _clamp_dimension(items, headroom):
    """Scale a dimension's items down so their points never exceed headroom."""
    total = sum(i['points'] for i in items)
    if total <= 0 or total <= headroom:
        return items
    factor = headroom / total
    for i in items:
        i['points'] = round(i['points'] * factor, 1)
    return items


def build_fix_checklist(ats_result, bullet_insights, sections, resume_text,
                        num_skills=0):
    """Checklist items with honest point estimates, capped at headroom.

    Each item's points come from the scorer's own weights, and the sum
    per dimension is clamped to (max - current score) for that dimension.
    """
    breakdown = (ats_result or {}).get('breakdown') or {}
    sections = sections or {}
    text = resume_text or ''
    word_count = len(text.split())
    items = []

    def add(item_id, dimension, title, fix, points):
        items.append({'id': item_id, 'dimension': dimension, 'title': title,
                      'fix': fix, 'points': round(points, 1)})

    # Sections: 15 points across 4 essentials -> 3.75 per missing section.
    for name in ('summary', 'education', 'experience', 'skills'):
        if name not in sections:
            article = 'an' if name[0] in 'aeiou' else 'a'
            add('add-section-' + name, 'sections',
                'Add %s %s section' % (article, name.title()),
                'ATS parsers look for this standard heading; without it '
                'the content underneath may not be parsed as %s.' % name,
                3.75)
    # Skills: next tier of the scorer's tier table (0->5, 1->10, 4->15,
    # 7->20, 10->25 points; each step is worth 5).
    if num_skills < 15:
        if num_skills >= 10:
            nxt = 15
        elif num_skills >= 7:
            nxt = 10
        elif num_skills >= 4:
            nxt = 7
        elif num_skills >= 1:
            nxt = 4
        else:
            nxt = 1
        add('add-skills', 'skills',
            'List %d+ distinct skills' % nxt,
            'The scorer awards 5 more points at the next skills tier; '
            'list only skills you genuinely hold.',
            5.0)
    # Content: metrics headroom (1.5 per new unique metric, max 5 total)
    # and verb headroom (1.5 per new distinct verb, max 7 total).
    metrics_headroom = max(0.0, 5.0 - min(
        bullet_insights.get('unique_metrics', 0) * 1.5, 5.0))
    if bullet_insights.get('weak') and metrics_headroom > 0:
        add('quantify-bullets', 'content',
            'Add a metric to your weakest bullets',
            'Numbers prove impact: %% change, users reached, time saved, '
            'or money moved. Two new unique metrics are worth up to 3 points.',
            min(3.0, metrics_headroom))
    verbs_headroom = max(0.0, 7.0 - min(
        bullet_insights.get('verbs_found', 0) * 1.5, 7.0))
    if verbs_headroom > 0 and bullet_insights.get('total', 0) > 0:
        add('verb-led-bullets', 'content',
            'Start bullets with action verbs',
            'Lead each bullet with a verb like built, led, or shipped '
            'instead of "responsible for".',
            min(1.5, verbs_headroom))
    # Contact: exact scorer weights for whatever is missing.
    contact = breakdown.get('contact') or {}
    details = contact.get('details') or ''
    if 'Email: ✗' in details:
        add('add-email', 'contact', 'Add an email address',
            'The single highest-weight contact item (3 points).', 3.0)
    if 'Phone: ✗' in details:
        add('add-phone', 'contact', 'Add a phone number',
            'Worth 3 points in the contact dimension.', 3.0)
    if 'LinkedIn: ✗' in details:
        add('add-linkedin', 'contact', 'Add your LinkedIn URL',
            'Worth 2 points in the contact dimension.', 2.0)
    if 'GitHub/Portfolio: ✗' in details:
        add('add-portfolio', 'contact', 'Add GitHub or a portfolio link',
            'Worth 2 points in the contact dimension.', 2.0)
    # Formatting: only when length is outside the scorer's sweet spot.
    if not (400 <= word_count <= 1000) and word_count >= 50:
        add('trim-length', 'formatting', 'Aim for 400–1000 words',
            'Your resume is %d words; the scorer awards its length points '
            'inside the 400–1000 band.' % word_count, 2.0)

    # Clamp per dimension to remaining headroom, then project.
    by_dim = {}
    for i in items:
        by_dim.setdefault(i['dimension'], []).append(i)
    clamped = []
    for dim, dim_items in by_dim.items():
        headroom = max(0.0, _dim_max(breakdown, dim) - _dim_score(breakdown, dim))
        clamped.extend(_clamp_dimension(dim_items, headroom))
    total_points = round(sum(i['points'] for i in clamped), 1)
    current = (ats_result or {}).get('percentage') or 0
    return {
        'items': clamped,
        'total_points': total_points,
        'projected_pct': round(min(100.0, current + total_points), 1),
        'current_pct': current,
    }


def _dim_score(breakdown, key):
    try:
        return float((breakdown.get(key) or {}).get('score') or 0)
    except (TypeError, ValueError):
        return 0.0


def _dim_max(breakdown, key):
    try:
        return float((breakdown.get(key) or {}).get('max') or 0)
    except (TypeError, ValueError):
        return 0.0


def dimension_notes(ats_result, bullet_insights, sections, fix_checklist):
    """Per-dimension explainer: what it measures, exact evidence, fixes."""
    breakdown = (ats_result or {}).get('breakdown') or {}
    fix_by_dim = {}
    for item in (fix_checklist or {}).get('items', []):
        fix_by_dim.setdefault(item['dimension'], []).append(item['id'])
    notes = {}
    for key, item in breakdown.items():
        score = _dim_score(breakdown, key)
        notes[key] = {
            'label': item.get('label') or key,
            'measures': _MEASURES.get(key, ''),
            'evidence': item.get('details') or '',
            'lost': round(_dim_max(breakdown, key) - score, 1),
            'fix_ids': fix_by_dim.get(key, []),
        }
    if bullet_insights.get('total'):
        notes.setdefault('content', {}).update({
            'bullet_total': bullet_insights['total'],
            'bullet_quantified_pct': bullet_insights['quantified_pct'],
        })
    return notes
