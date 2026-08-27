from pydantic_table.logger import logg


def test_model(test_case_example):
    logg.debug("Example table")
    logg.debug(test_case_example)
