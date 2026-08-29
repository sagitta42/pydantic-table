import json
import os
from pathlib import Path
from typing import Type

import inspect

from alembic import op

from pydantic_table.logger import logg
from pydantic_table.table_model.model import TableModel
import pydantic_table.sqlalchemy as sap


# TODO: multiple columns
def archive_column(table: Type[TableModel], column: str):
    """
    Archive column information.

    Extract column field information from table (not table model, which does not have it anymore).
    Extract path to the migration file (assumes drop_column is called from a migration)
    Create archive directory if does not exist.
    Serialize field information to be saved in archive JSON.
    Get dict data from sa.Table to archive.
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

    engine = op.get_bind()

    tb = sap.Table(table, autoload_with=engine)
    sa_column = tb.c[column]
    column_info = sap.ColumnFieldInfo(sa_column)

    if not archive.exists():
        os.makedirs(archive)

    info_dict = column_info.as_dict()
    info_dict["annotation"] = str(info_dict["annotation"])

    result = engine.execute(tb.select())
    data_dict = [dict(row) for row in result.mappings()]

    archive_dict = {column: {"info": info_dict, "data": data_dict}}
    logg.debug(f"archive dict: {archive_dict}")

    with open(archive_file, "w") as f:
        json.dump(archive_dict, f, indent=2)

    logg.debug(f"Column")
