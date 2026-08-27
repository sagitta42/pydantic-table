import enum


class InternalAttr(str, enum.Enum):
    table_name = "table_name_"
    primary_keys = "primary_keys_"
    missing = "missing_columns_"

    @classmethod
    def values(cls) -> list[str]:
        return [c.value for c in cls]
