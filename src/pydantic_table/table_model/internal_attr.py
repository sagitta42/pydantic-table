import enum


class InternalAttr(str, enum.Enum):
    table_name = "table_name__"
    primary_keys = "primary_keys__"
    missing = "missing_columns__"

    @classmethod
    def values(cls) -> list[str]:
        return [c.value for c in cls]
