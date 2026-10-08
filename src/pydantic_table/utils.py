from typing import Any, Iterable
import uuid

from sqlalchemy import Connection


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


def handle_data_uuid(data: dict[str, Any], engine: Connection) -> dict[str, Any]:
    ret = {}

    if engine.dialect.name == "sqlite":
        for col, val in data.items():
            ret[col] = str(val) if isinstance(val, uuid.UUID) else val

    return ret
