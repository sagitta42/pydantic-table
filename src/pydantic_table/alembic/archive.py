import json
import os
from pathlib import Path
from typing import Any, Type

import inspect

from alembic import op

from pydantic_table.logger import logg
from pydantic_table.table_model.field import ColumnFieldInfo
from pydantic_table.table_model.model import TableModel
import pydantic_table.sqlalchemy as sap

SAVE_DATA = False


class Archive:
    def __init__(self, table: Type[TableModel]) -> None:
        self.table = table

        self._revision_filepath = self._get_revision_filepath()

        versions = self._revision_filepath.parent
        self._dir = versions / ".archive"

        if not self._dir.exists():
            os.makedirs(self._dir)

        revision_filename = Path(self._revision_filepath).stem
        self._archive_file = self._dir / f"{revision_filename}.json"
        logg.debug(f"archive file: {self._archive_file}")

    @property
    def exists(self) -> bool:
        return self._archive_file.exists()

    def _get_revision_filepath(self) -> Path:
        frame = inspect.currentframe()
        assert frame is not None, "got null frame"
        archive_caller = frame.f_back
        assert archive_caller is not None, "no archive caller frame"
        opp_caller = archive_caller.f_back
        assert opp_caller is not None, "no opp caller frame"
        revision_caller = opp_caller.f_back
        assert revision_caller is not None, "no revision caller frame"

        ret = Path(revision_caller.f_code.co_filename)
        return ret

    # TODO: multiple columns
    def archive_column_info(self, column: str):
        """
        Archive column information.

        Extract column field information from table (not table model, which does not have it anymore).
        Extract path to the migration file (assumes drop_column is called from a migration)
        Create archive directory if does not exist.
        Serialize field information to be saved in archive JSON.
        Get dict data from sa.Table to archive.
        """

        if self.exists:
            logg.debug("-> already exists")
            return

        engine = op.get_bind()

        tb = sap.Table(self.table, autoload_with=engine)
        sa_column = tb.c[column]
        column_info = sap.ColumnFieldInfo(sa_column)

        info_dict = column_info.as_dict()
        info_dict["annotation"] = str(info_dict["annotation"])
        archive_dict: dict[str, dict[str, Any]] = {column: {"info": info_dict}}

        if SAVE_DATA:
            result = engine.execute(tb.select())
            data_dict = [dict(row) for row in result.mappings()]
            archive_dict[column]["data"] = data_dict

        logg.debug(f"archive dict: {archive_dict}")

        with open(self._archive_file, "w") as f:
            json.dump(archive_dict, f, indent=2)

        logg.debug(f"Column")

    def get_column_info(self, column: str) -> ColumnFieldInfo:
        """
        Get column schema from archive
        """
        pass
