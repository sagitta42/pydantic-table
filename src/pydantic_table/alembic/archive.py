import json
import os
from pathlib import Path
from typing import Any, Type

import inspect

from alembic import op

from pydantic_table.alembic.exceptions import ArchiveException
from pydantic_table.logger import logg
from pydantic_table.table_model.field import ColumnFieldInfo
from pydantic_table.table_model.model import TableModel

import sqlalchemy as sa
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
    def file_exists(self) -> bool:
        return self._archive_file.exists()

    def archive_table_model(self, sa_table: sa.Table):
        """
        Archive table schema.
        """
        if self.file_exists:
            logg.debug("-> already exists")
            return

        table_dict = {}
        for name, column in sa_table.c.items():
            table_dict[name] = self._build_column_info_dict(column)

        archive_dict = {sa_table.name: table_dict}
        self._save_archive_dict(archive_dict)

    # TODO: multiple columns
    def archive_column_info(self, column_name: str):
        """
        Archive column information.

        Extract column field information from table (not table model, which does not have it anymore).
        Extract path to the migration file (assumes drop_column is called from a migration)
        Create archive directory if does not exist.
        Serialize field information to be saved in archive JSON.
        Get dict data from sa.Table to archive.
        """

        if self.file_exists:
            logg.debug("-> already exists")
            return

        engine = op.get_bind()

        tb = sap.Table(self.table, autoload_with=engine)
        sa_column = tb.c[column_name]
        archive_dict: dict[str, dict[str, Any]] = {
            column_name: {"info": self._build_column_info_dict(sa_column)}
        }

        if SAVE_DATA:
            result = engine.execute(tb.select())
            data_dict = [dict(row) for row in result.mappings()]
            archive_dict[column_name]["data"] = data_dict

        self._save_archive_dict(archive_dict)

    def read_column_info(self, column: str) -> ColumnFieldInfo:
        """
        Get column schema from archive
        """
        if not self._archive_file.exists():
            raise ArchiveException(f"Archive file {self._archive_file} not found!")

        with open(self._archive_file) as f:
            file_dict = json.load(f)

        if not column in file_dict:
            raise ArchiveException(
                f"Column {column} does not exist in archive file {self._archive_file}!"
            )

        column_dict = file_dict[column]

        if not "info" in column_dict:
            raise ArchiveException(
                f"Field 'info' not found for column {column} in archive file {self._archive_file}!"
            )

        info_dict = column_dict["info"]
        info_dict["annotation"] = eval(info_dict["annotation"])
        ret = ColumnFieldInfo(**info_dict)
        return ret

    def _build_column_info_dict(self, column: sa.Column) -> dict[str, Any]:
        """
        Build column field info dict based on sqlalchemy column.
        """
        column_info = sap.ColumnFieldInfo(column)
        ret = column_info.as_dict()
        ret["annotation"] = ret["annotation"].__name__
        return ret

    def _save_archive_dict(self, dct: dict[str, Any]):
        logg.debug(f"archive dict: {dct}")

        with open(self._archive_file, "w") as f:
            json.dump(dct, f, indent=2)

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
