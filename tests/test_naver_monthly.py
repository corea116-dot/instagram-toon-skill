"""Synthetic offline regression tests; these are not observed search counts."""
import pytest
from pydantic import ValidationError
from test_informational_keywords import informational_payload
from keyword_models import InformationalKeywordEvidence, InformationalKeywordResearch, keyword_research_adapter
from keyword_selection import select_topic


def payload():
    data = informational_payload()
    data["selection_policy"] = "naver_monthly"
    return data


def test_naver_only_and_raw_counts():
    data = payload()
    data["batches"] = data["batches"][:1]
    evidence = InformationalKeywordEvidence.model_validate(data)
    decision = select_topic(evidence, "evergreen")
    assert decision.selected_id == "0"
    assert [row.total for row in decision.scores] == [500, 400, 300, 200, 100]
    assert all(row.google is None for row in decision.scores)
    result = InformationalKeywordResearch(evidence=evidence, decision=decision)
    assert keyword_research_adapter.validate_json(result.model_dump_json()) == result


def test_google_cannot_outweigh_naver():
    data = payload()
    data["batches"][1]["values"][-1]["value"] = 1000000
    evidence = InformationalKeywordEvidence.model_validate(data)
    assert select_topic(evidence, "evergreen").selected_id == "0"


@pytest.mark.parametrize("case", ["missing", "partial", "relative"])
def test_no_proxy_fallback(case):
    data = payload()
    if case == "missing":
        data["batches"] = data["batches"][1:]
    elif case == "partial":
        data["batches"][0]["values"].pop()
    else:
        data["batches"][0]["method"] = "relative_index"
        for item in data["batches"][0]["values"]:
            item["value"] = 50
    decision = select_topic(InformationalKeywordEvidence.model_validate(data), "evergreen")
    assert decision.status == "hold"
    assert all(row.total is None for row in decision.scores)


@pytest.mark.parametrize("change", [{"pc_searches": None}, {"pc_searches": "<10"}, {"mobile_searches": 1}])
def test_missing_suppressed_or_wrong_sum_rejected(change):
    data = payload()
    data["batches"][0]["values"][0].update(change)
    with pytest.raises(ValidationError):
        InformationalKeywordEvidence.model_validate(data)


def test_failed_gate_excludes_highest_volume():
    data = payload()
    data["candidates"][0]["gate_results"]["source_relevance"] = False
    data["candidates"][0]["eligibility"] = False
    result = select_topic(InformationalKeywordEvidence.model_validate(data), "evergreen")
    assert result.selected_id == "1"
    assert result.scores[0].rank == 1


def provider_period_payload():
    data = payload()
    data["batches"] = data["batches"][:1]
    batch = data["batches"][0]
    batch.pop("window_start")
    batch.pop("window_end")
    batch["reporting_period"] = "최근 한달간 네이버 통합검색"
    batch["observed_at"] = data["sources"][0]["accessed_at"]
    return data


def test_provider_period_selects_without_invented_dates():
    evidence = InformationalKeywordEvidence.model_validate(provider_period_payload())
    decision = select_topic(evidence, "evergreen")
    assert decision.selected_id == "0"
    assert evidence.batches[0].window_start is None
    assert evidence.batches[0].window_end is None
    result = InformationalKeywordResearch(evidence=evidence, decision=decision)
    assert keyword_research_adapter.validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("change", [
    {"reporting_period": None}, {"reporting_period": " "},
    {"observed_at": None}, {"observed_at": "2026-09-01T10:00:00"},
    {"observed_at": "2020-01-01T10:00:00+09:00"},
    {"observed_at": "2099-01-01T10:00:00+09:00"},
    {"window_start": "2026-08-01"}, {"method": "relative_index"},
    {"previous_window_start": "2026-07-01", "previous_window_end": "2026-07-31"},
])
def test_invalid_provider_period_rejected(change):
    data = provider_period_payload()
    data["batches"][0].update(change)
    with pytest.raises(ValidationError):
        InformationalKeywordEvidence.model_validate(data)


def test_undated_counts_do_not_prove_growth():
    data = provider_period_payload()
    data["batches"][0]["values"][0]["previous_value"] = 1
    with pytest.raises(ValidationError):
        InformationalKeywordEvidence.model_validate(data)


def test_mixed_dated_and_provider_period_batches():
    data = provider_period_payload()
    data["batches"].append(payload()["batches"][0])
    assert select_topic(InformationalKeywordEvidence.model_validate(data), "evergreen").selected_id == "0"


def test_provider_period_requires_same_day_sources():
    from datetime import datetime, timedelta
    data = provider_period_payload()
    data["sources"][0]["accessed_at"] = (datetime.fromisoformat(data["sources"][0]["accessed_at"]) - timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError):
        InformationalKeywordEvidence.model_validate(data)
