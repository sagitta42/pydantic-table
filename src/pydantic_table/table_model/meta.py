from typing import Any, Type

from pydantic import BaseModel, Field

from pydantic_table.table_model.internal_attr import AttrDescription, InternalAttr


def nested_merge(first: dict, second: dict) -> dict:
    for key, b_val in second.items():
        if key in first and isinstance(first[key], dict) and isinstance(b_val, dict):
            nested_merge(first[key], b_val)
        else:
            first[key] = b_val
    return first


class TableMeta(type(BaseModel)):
    """
    Metaclass for TableModel creation.

    Takes care of fields hidden to user.
    """

    def __new__(
        cls,
        name: str,
        bases: tuple[Type, ...],
        namespace: dict[str, Any],
        /,
        table_name: str = "",
        primary_keys: list[str] = [],
        **kwds: Any,
    ):
        namespace.setdefault("__annotations__", {})

        # TODO: figure out if better to use private attributes and how
        #  cls.__dict__.keys()
        # dict_keys(
        #     [
        #         "__private_attributes__",
        #         "__pydantic_fields__",
        #         "__pydantic_core_schema__",
        #     ]
        # )
        nested_merge(
            namespace,
            cls._get_field_namespace_info(InternalAttr.table_name, table_name),
        )
        nested_merge(
            namespace,
            cls._get_field_namespace_info(InternalAttr.primary_keys, primary_keys),
        )

        for field in [InternalAttr.missing, InternalAttr.extra]:
            nested_merge(namespace, cls._get_field_namespace_info(field, []))

        return super().__new__(cls, name, bases, namespace, **kwds)

    @classmethod
    def _get_field_namespace_info(
        cls, field_name: InternalAttr, parameter: Any
    ) -> dict:
        """
        Create information to add to namespace to create field.

        parameter: parameter to be added - defines annotation and default value.
        name: field name

        The default value is crucial to set fixed table model parameters once during
            child class definition (e.g. table name).
        """
        ret = {
            "__annotations__": {field_name.value: type(parameter)},
            field_name: Field(
                default=parameter,
                description=AttrDescription.from_attr(field_name),
                exclude=True,
            ),
        }
        return ret
