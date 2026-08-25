import pydantibase.foo as foo
from pydantibase.logger import logg

from tests.conftest import PATH_TO_CONFIGS

def test_foo():
    input = 21
    output = foo.answer(input)
    the_answer = 42
    assert output == the_answer, f"Test failed because answer not {the_answer}"


def test_model(test_case_example):
    logg.debug("Example table")
    logg.debug(test_case_example)