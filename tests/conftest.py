import json
from pathlib import Path
import pytest
import sys
import os

from dotenv import dotenv_values

from examples.models import ExampleTable

env_config = dotenv_values()
is_debug = env_config.get("DEBUG", "").lower() in ("true", "1")

if is_debug:
    path_current = os.path.dirname(__file__)
    # make src modules accessible in all test_* files without having to install the package
    path_to_src = os.path.join(path_current, "..", "src")
    path_to_src_absolute = os.path.abspath(path_to_src)
    sys.path.insert(0, path_to_src_absolute)

PATH_TO_ASSETS = Path(os.path.dirname(__file__))
PATH_TO_CONFIGS = PATH_TO_ASSETS / "configs"


def get_example_model(filename: str) -> ExampleTable:
    model_config_path = PATH_TO_CONFIGS / f"{filename}.json"
    with open(model_config_path) as f:
        dataset_info = ExampleTable(**json.load(f))
    return dataset_info


def get_example_test_case(filename: str = "test_model"):
    example_model = get_example_model(filename)
    ret = [pytest.param(example_model, id=filename)]
    return ret


@pytest.fixture(params=get_example_test_case())
def test_case_example(request) -> ExampleTable:
    return request.param
