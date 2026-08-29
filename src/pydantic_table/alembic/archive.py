import json
import os
from pathlib import Path
from typing import Type

import inspect

from pydantic_table.logger import logg
from pydantic_table.table_model.model import TableModel


def archive_column(table: Type[TableModel], column: str):
    """
    Archive column information.

    Extract path to the migration file (assumes drop_column is called from a migration)
    Create archive directory if does not exist.
    """

    frame = inspect.currentframe()
    assert frame is not None, "got null frame"
    opp_caller = frame.f_back
    assert opp_caller is not None, "no opp caller frame"
    revision_caller = opp_caller.f_back
    assert revision_caller is not None, "no revision caller frame"

    filepath = Path(revision_caller.f_code.co_filename)
    versions = filepath.parent

    archive = versions / ".archive"
    revision_filename = Path(filepath).stem
    archive_file = archive / f"{revision_filename}.json"
    logg.debug(f"archive file: {archive_file}")

    if archive_file.exists():
        logg.debug("-> already exists")
        return

    if not archive.exists():
        os.makedirs(archive)

    column_info = table.column_fields()[column]
    column_dict = column_info.as_dict()
    column_dict["annotation"] = str(column_dict["annotation"])
    archive_dict = {column: column_dict}
    logg.debug(f"archive dict: {archive_dict}")

    with open(archive_file, "w") as f:
        json.dump(archive_dict, f, indent=2)

    logg.debug(f"Column")
