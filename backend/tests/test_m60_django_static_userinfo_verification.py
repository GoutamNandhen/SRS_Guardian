"""Synthetic, offline first-party tests; these are NOT real-world accuracy evidence."""
import pytest
from backend.evaluation import m60_django_static_userinfo_verification as m60


def fake_source(fragment):
    return ("class URLValidator(RegexValidator):\n"
            "    regex = _lazy_re_compile(\n"
            "        r'^(?:[a-z0-9]*)://'\n"
            f"        r'{fragment}'  # user:pass authentication\n"
            "        r'(?:' + host_re + ')'\n"
            "    )\n")


def test_static_violation_on_old_literal():
    fragment, line = m60.extract_userinfo(fake_source(r'(?:\S+(?::\S*)?@)?'))
    assert line == 4
    assert m60.check_fragment(fragment)['static_result'] == 'static_rule_violated'


def test_static_satisfaction_on_new_literal():
    fragment, _ = m60.extract_userinfo(fake_source(r'(?:[^\s:@/]+(?::[^\s:@/]*)?@)?'))
    result = m60.check_fragment(fragment)
    assert result['static_result'] == 'static_rule_satisfied'
    assert result['user_and_password_character_classes']['user']['permitted_prohibited_delimiters'] == []


def test_partial_exclusion_still_violates():
    result = m60.check_fragment(r'(?:[^\s@/]+(?::[^\s@/]*)?@)?')
    assert result['static_result'] == 'static_rule_violated'
    assert result['user_and_password_character_classes']['user']['permitted_prohibited_delimiters'] == [':']


def test_unsupported_regex_abstains_not_passes():
    assert m60.check_fragment(r'(?:.*@)?')['static_result'].startswith('abstain')
    assert m60.check_fragment(r'(?:[^a-z]+(?::[^a-z]*)?@)?')['static_result'].startswith('abstain')


def test_no_dynamic_source_evaluation():
    evil = fake_source(r'(?:\S+(?::\S*)?@)?') + '\nraise RuntimeError("must not run")\n'
    assert m60.extract_userinfo(evil)[0].startswith('(?:')


def test_reject_ambiguous_class_and_missing_assignment():
    with pytest.raises(ValueError, match='not unique'):
        m60.extract_userinfo(fake_source(r'(?:\S+(?::\S*)?@)?') * 2)
    with pytest.raises(ValueError, match='not unique'):
        m60.extract_userinfo('class SomethingElse:\n    pass\n')


def test_pinned_blob_mismatch_is_rejected():
    with pytest.raises(ValueError, match='Git blob mismatch'):
        m60.verify_snapshot(b'not pinned', b'not pinned', 'before')
    with pytest.raises(ValueError, match='Unknown revision'):
        m60.verify_snapshot(b'', b'', 'unknown')


def test_download_only_pinned_paths():
    with pytest.raises(ValueError, match='pinned'):
        m60.download_pinned('0'*40, m60.PATH)
    with pytest.raises(ValueError, match='pinned'):
        m60.download_pinned(m60.REVISIONS['before']['commit'], '../other.py')


def test_explicit_no_gold_and_no_metrics():
    assert m60.PROHIBITED == (':', '@', '/')
    assert m60.REVISIONS['before']['blob'] != m60.REVISIONS['after']['blob']
