"""M33 first-party tests: synthetic fixtures are not conformance evidence."""
from __future__ import annotations

import pytest

from backend.evaluation import m28_historical_pagination_regression as m28
from backend.evaluation import m33_upstream_test_intent_replay as m33


def fixture_java() -> str:
    return """
    @ParameterizedTest
    @ArgumentsSource(RangeProvider.class)
    void should_return_offers_subset_when_across_multiple_contract_definitions(int from, int to) {
        var assets1 = range(0, 10).mapToObj(i -> i);
        var assets2 = range(10, 20).mapToObj(i -> i);
        var maximumRange = max(0, (assets1.size() + assets2.size()) - from);
        var requestedRange = to - from;
        assertThat(contractOfferResolver.queryContractOffers(query)).hasSize(min(requestedRange, maximumRange));
    }

    @Test
    void nextTest() {}
    static class RangeProvider implements ArgumentsProvider {
        public Stream<? extends Arguments> provideArguments(ExtensionContext context) {
            return Stream.of(
                Arguments.of(0, 12),
                Arguments.of(8, 14),
                Arguments.of(0, 999),
                Arguments.of(4, 888),
                Arguments.of(3, 20),
                Arguments.of(23, 25)
            );
        }
    }
    """


def test_extract_exact_six_upstream_cases():
    counts, ranges = m33.parse_test_intent(fixture_java())
    assert counts == (10, 10)
    assert ranges == m33.EXPECTED_RANGES


def test_conditional_model_vs_test_intent_not_gold():
    counts, ranges = m33.parse_test_intent(fixture_java())
    rows = m33.replay_test_intent(counts, ranges)
    assert len(rows) == 6
    assert [r["test_assertion_expected_not_gold"] for r in rows] == [12, 6, 20, 16, 17, 0]
    assert [r["before_conditional_model"] for r in rows] == [20, 8, 20, 16, 17, 0]
    assert [r["after_conditional_model"] for r in rows] == [12, 6, 20, 16, 17, 0]
    assert sum(not r["before_model_matches_test_intent"] for r in rows) == 2
    assert all(r["after_model_matches_test_intent"] for r in rows)
    assert all(r["runtime_before"] is None and r["independent_labels"] is None for r in rows)


@pytest.mark.parametrize("replacement", [
    "range(0, 9)", "hasSize(12)", "Arguments.of(0, 13)",
    "should_return_offers_subset_when_across_multiple_contract_definitionsX",
])
def test_parser_rejects_changed_upstream_test(replacement):
    source = fixture_java()
    original = {
        "range(0, 9)": "range(0, 10)",
        "hasSize(12)": "hasSize(min(requestedRange, maximumRange))",
        "Arguments.of(0, 13)": "Arguments.of(0, 12)",
        "should_return_offers_subset_when_across_multiple_contract_definitionsX":
            "should_return_offers_subset_when_across_multiple_contract_definitions",
    }[replacement]
    with pytest.raises(m28.EvidenceError):
        m33.parse_test_intent(source.replace(original, replacement, 1))


def test_invalid_range_rejected():
    with pytest.raises(m28.EvidenceError):
        m33.replay_test_intent((10, 10), ((5, 5),))
