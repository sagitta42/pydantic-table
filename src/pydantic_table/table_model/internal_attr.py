import enum


class InternalAttr(str, enum.Enum):
    table_name = "table_name__"
    primary_keys = "primary_keys__"
    missing = "missing_columns__"
    extra = "extra_columns__"

    @classmethod
    def values(cls) -> list[str]:
        return [c.value for c in cls]


class AttrDescription(str, enum.Enum):
    table_name = "Table name"
    primary_keys = "Primary keys"
    missing = "Missing columns"
    extra = "Extra columns"

    @classmethod
    def from_attr(cls, attr: InternalAttr) -> str:
        return cls[attr.name].value
