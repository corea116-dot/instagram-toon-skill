from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from test_informational_keywords import editorial_payload, informational_payload
from keyword_models import InformationalKeywordEvidence, InformationalKeywordResearch, keyword_research_adapter
from keyword_selection import select_topic
from topic_editorial import DiscoveryPool
from topic_performance import PerformanceInput, summarize_performance
from topic_search import app


def decide(payload=None, requested='evergreen'):
    return select_topic(InformationalKeywordEvidence.model_validate(payload or editorial_payload()), requested)


def test_editorial_order_and_reproducible_decision():
    payload = editorial_payload()
    d = decide(payload)
    assert d.selected_id == '1'
    assert d.scores[0].rank == 1 and d.scores[0].final_rank == 2
    assert d.scores[1].editorial_total == 6 and d.scores[1].final_rank == 1
    assert 'demand rank 1: 0: lower editorial total' in d.reason
    result = InformationalKeywordResearch(evidence=InformationalKeywordEvidence.model_validate(payload), decision=d)
    saved = result.model_dump(mode='json')
    assert keyword_research_adapter.validate_python(saved) == result
    saved['decision']['scores'][1]['final_rank'] = 3
    with pytest.raises(ValidationError, match='recomputed'):
        keyword_research_adapter.validate_python(saved)


def test_ties_use_demand_then_stable_id():
    p = editorial_payload()
    p['candidates'][0]['editorial'] = {**p['candidates'][1]['editorial'], 'opening_question': p['candidates'][0]['reader_question']}
    assert decide(p).selected_id == '0'
    p['batches'][0]['values'][0].update(value=400, pc_searches=400)
    assert decide(p).selected_id == '0'
    p['candidates'].reverse()
    assert decide(p).selected_id == '0'


@pytest.mark.parametrize('gate', ['audience_fit', 'source_relevance', 'safety', 'duplicate'])
def test_high_editorial_score_cannot_rescue_gate(gate):
    p = editorial_payload()
    p['candidates'][1]['eligibility'] = False
    p['candidates'][1]['gate_results'][gate] = False
    d = decide(p)
    assert d.selected_id == '0'
    assert d.scores[1].final_rank is None
    assert 'gate failed' in d.scores[1].rejection_reason


def test_type_fallback_and_missing_demand():
    p = editorial_payload()
    assert decide(p, 'trending').effective_type == 'evergreen'
    p['candidates'][0].update(keyword_type='trending', event_kind='deadline', event_date='2026-09-20')
    assert decide(p, 'trending').selected_id == '0'
    p['batches'][0]['values'].pop()
    d = decide(p)
    assert d.status == 'hold' and all(r.naver is None and r.final_rank is None for r in d.scores)
    p = editorial_payload()
    for v in p['batches'][0]['values']:
        v.update(value=0, pc_searches=0, mobile_searches=0)
    assert decide(p).status == 'hold'


@pytest.mark.parametrize('mutation', ['missing_direction', 'missing_pool', 'keyword', 'shortlist', 'question', 'future', 'coverage', 'components'])
def test_provenance_and_inputs_cannot_be_omitted(mutation):
    p = editorial_payload()
    if mutation == 'missing_direction': del p['candidates'][0]['editorial']
    if mutation == 'missing_pool': del p['discovery']
    if mutation == 'keyword': p['discovery']['candidates'][0]['keyword'] = '다른 말'
    if mutation == 'shortlist': p['discovery']['candidates'][0]['shortlist'] = False
    if mutation == 'question': p['candidates'][0]['reader_question'] = '방향 변경'
    if mutation == 'future': p['discovery']['candidates'][0]['observed_on'] = '2099-01-01'
    if mutation == 'coverage': del p['discovery']['coverage']['housing']
    if mutation == 'components': p['batches'][0]['values'][0]['pc_searches'] = None
    with pytest.raises(ValidationError): InformationalKeywordEvidence.model_validate(p)


def test_pool_dedup_preserves_reasons_and_diversity_exception(tmp_path):
    p = editorial_payload()['discovery']
    duplicate = {**p['candidates'][0], 'id': 'duplicate', 'keyword': ' 테스트키워드0 ', 'shortlist': False, 'decision_reason': '중복 제외'}
    p['candidates'].append(duplicate)
    report = DiscoveryPool.model_validate(p).normalized()
    assert report['status'] == 'ready' and report['unique_candidate_count'] == 5
    assert report['duplicates'] == [{'id': 'duplicate', 'representative_id': '0'}]
    assert report['pool']['candidates'][-1]['decision_reason'] == '중복 제외'
    for c in p['candidates']: c['domain'] = 'housing'
    assert DiscoveryPool.model_validate(p).normalized()['status'] == 'hold'
    p['diversity_exception'] = '사용자가 주거 분야로 제한'
    assert DiscoveryPool.model_validate(p).normalized()['status'] == 'ready'
    path = tmp_path / 'pool.json'; path.write_text(json.dumps(p))
    output = tmp_path / 'report.json'
    assert CliRunner().invoke(app, ['pool', '--input', str(path), '--output', str(output)]).exit_code == 0
    assert json.loads(output.read_text())['status'] == 'ready'


def post(identifier='1', **changes):
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    p = dict(post_id=identifier, source_reference='local:supplied-insights.csv',
             published_at=start.isoformat(), window_end=(start+timedelta(days=7)).isoformat(),
             collected_at=(start+timedelta(days=8)).isoformat(), paid=False,
             domain='housing', story_approach='오해 해소형', views=1000, reach=500,
             nonfollower_reach=300, follows=10, shares=None, saves=0,
             missing_reasons={'shares': '사용자 제공 자료에 없음'})
    p.update(changes)
    return p


def test_performance_missing_zero_pairwise_rates_and_paid_separation():
    p2 = post('2', reach=None, follows=50, missing_reasons={'shares': '미제공', 'reach': '미제공'})
    p3 = post('3', paid=True)
    p4 = post('4', paid=None, missing_reasons={'shares':'미제공', 'paid':'미확인'})
    p5 = post('5', window_end='2026-09-07T00:00:00Z')
    summary = summarize_performance(PerformanceInput.model_validate({'posts': [post(), p2, p3, p4, p5]}))
    assert len(summary['groups']) == 3 and len(summary['excluded_observations']) == 1
    group = next(g for g in summary['groups'] if g['paid'] is False)
    assert group['metrics']['follows']['observed_total'] == 60
    assert group['metrics']['follows']['per_1000_reach'] == 20
    assert group['metrics']['follows']['rate_posts'] == 1
    assert group['metrics']['shares']['observed_total'] is None
    assert group['metrics']['saves']['observed_total'] == 0
    assert group['metrics']['saves']['per_1000_reach'] == 0
    assert summary['automatic_weights'] is False


def test_performance_refresh_only_when_input_changes(tmp_path):
    source = tmp_path/'input.json'; output = tmp_path/'summary.json'
    source.write_text(json.dumps({'posts': [post()]}))
    args = ['performance', '--input', str(source), '--output', str(output)]
    runner = CliRunner()
    assert runner.invoke(app, args).exit_code == 0
    before = output.stat().st_mtime_ns
    assert 'unchanged' in runner.invoke(app, args).output
    assert output.stat().st_mtime_ns == before
    source.write_text(json.dumps({'posts': [post(views=2000)]}))
    assert runner.invoke(app, args).exit_code == 0
    assert json.loads(output.read_text())['groups'][0]['metrics']['views']['observed_total'] == 2000


@pytest.mark.parametrize('changes', [dict(shares=0), dict(nonfollower_reach=501), dict(views=-1), dict(views=True), dict(window_end='2026-09-20T00:00:00Z')])
def test_invalid_performance_rejected(changes):
    with pytest.raises(ValidationError): PerformanceInput.model_validate({'posts':[post(**changes)]})


def test_historical_policy_cannot_silently_ignore_editorial_fields():
    p = editorial_payload(); p['selection_policy'] = 'naver_monthly'
    with pytest.raises(ValidationError): InformationalKeywordEvidence.model_validate(p)
    old = informational_payload()
    old['selection_policy'] = 'naver_monthly'
    assert decide(old).selected_id == '0'


def test_new_run_rejects_old_policy_and_exports_required_inputs(tmp_path):
    source = tmp_path/'old.json'; source.write_text(json.dumps(informational_payload()))
    history = tmp_path/'history.json'; history.write_text('{"schema_version":"1.1","episodes":[]}')
    result = CliRunner().invoke(app, ['select', '--evidence', str(source), '--output', str(tmp_path/'out.json'), '--history', str(history)])
    assert result.exit_code == 1 and 'requires editorial_v1' in result.output
    schema = json.loads(CliRunner().invoke(app, ['schema']).output)
    assert schema['properties']['selection_policy']['const'] == 'editorial_v1'
    assert 'discovery' in schema['required']
    assert 'editorial' in schema['$defs']['InformationalKeywordCandidate']['required']


def test_pool_limits_and_missing_candidates_are_holds():
    p = editorial_payload()['discovery']
    p['candidates'] = p['candidates'][:3]
    assert DiscoveryPool.model_validate(p).normalized()['status'] == 'hold'
    p['candidates'] = [{**p['candidates'][0], 'id': str(i)} for i in range(16)]
    with pytest.raises(ValidationError): DiscoveryPool.model_validate(p)


def test_performance_no_samples_does_not_invent_zero_totals():
    report = summarize_performance(PerformanceInput(posts=()))
    assert report['groups'] == [] and report['automatic_weights'] is False
    blank = post(views=None, reach=None, nonfollower_reach=None, follows=None, shares=None, saves=None,
                 missing_reasons={m:'미제공' for m in ('views','reach','nonfollower_reach','follows','shares','saves')})
    metrics = summarize_performance(PerformanceInput.model_validate({'posts':[blank]}))['groups'][0]['metrics']
    assert all(m['observed_total'] is None and m['per_1000_reach'] is None for m in metrics.values())


def test_new_monthly_batch_requires_same_observation_day():
    p = editorial_payload()
    other = {**p['sources'][0], 'id':'naver-other-day', 'accessed_at':'2026-09-13T09:00:00+09:00'}
    p['sources'].append(other)
    p['batches'][0]['values'][0]['source_id'] = other['id']
    with pytest.raises(ValidationError, match='same observation day'): InformationalKeywordEvidence.model_validate(p)
