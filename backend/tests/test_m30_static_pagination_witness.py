"""M30 tests exercise only our Python abstraction, never upstream Java."""
from __future__ import annotations

import pytest

from backend.evaluation import m30_static_pagination_witness as m30


@pytest.mark.parametrize("offset,limit,pre,post", [
    (0, 52, 100, 52),
    (49, 2, 3, 2),
])
def test_historical_report_scenarios_as_conditional_model(offset, limit, pre, post):
    assert m30.simulate_before((50, 50), offset, limit)["model_returned_offers"] == pre
    assert m30.simulate_after((50, 50), offset, limit)["model_returned_offers"] == post


def test_model_no_assets_after_offset():
    for model in (m30.simulate_before, m30.simulate_after):
        assert model((50, 50), 200, 2)["model_returned_offers"] == 0


def test_model_within_first_definition():
    for model in (m30.simulate_before, m30.simulate_after):
        assert model((50, 50), 10, 10)["model_returned_offers"] == 10


@pytest.mark.parametrize("counts,offset,limit", [
    ((), 0, 1), ((-1, 50), 0, 1), ((50, 50), -1, 2),
    ((50, 50), 0, 0), ((50, 50), 0, -1), ((True, 50), 0, 1),
])
def test_invalid_inputs_fail_closed(counts, offset, limit):
    with pytest.raises(ValueError):
        m30.simulate_before(counts, offset, limit)
    with pytest.raises(ValueError):
        m30.simulate_after(counts, offset, limit)


def test_source_markers_cover_both_revisions():
    assert set(m30.SOURCE_MARKERS) == {"before", "after"}
    assert len(m30.SOURCE_MARKERS["before"]) >= 5
    assert len(m30.SOURCE_MARKERS["after"]) >= 5
    assert m30.MODEL.startswith("m30-")
