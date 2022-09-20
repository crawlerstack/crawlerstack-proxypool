import pytest

from crawlerstack_proxypool.common import KeywordChecker


class TestKeywordChecker:

    @pytest.fixture
    def checker(self, mocker):
        _checker = KeywordChecker.from_params(mocker.MagicMock(), keywords=['foo'])
        yield _checker

    @pytest.mark.parametrize(
        'text, expect_value',
        [
            ('foo, bar', True),
        ]
    )
    def test_check_keywords(self, checker, text: str, expect_value):
        res = checker.check_keywords(text)
        assert res == expect_value
