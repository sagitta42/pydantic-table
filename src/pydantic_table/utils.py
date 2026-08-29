from typing import Iterable


def list_as_str(lst: Iterable) -> str:
    """
    Transform list into a list of command line arguments.

    Example:
    >>> list_as_args(["install", "--no-root"])
    "install --no-root"
    """
    return " ".join(str(element) for element in lst)


def dict_as_str(dct: dict) -> str:
    return " ".join(f"{key}={value}" for key, value in dct.items())
