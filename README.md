# pydantibase

Use pydantic model as single source of truth for SQLAlchemy table definition and alembic migrations.

## `TableModel`

`TableModel` is a pydantic `BaseModel` that defines:
- table name and primary keys in special `table_name_` and `primary_keys_` fields. When inheriting, make sure to set them as `exclude=True` and set `Literal` and `default`
- column names via its fields, column types via field types (`FieldInfo` annotation)
- column nullability via `default` (default=None means nullable)
- table model class defines table layout but also a row that can be used for migrations (see `alembdantic`)

## alembdantic

Set up your alembic migrations with alembic as you usually do.

Create a `models.py` utils class inside your alembic migrations folder, and define your table model there.

```python
from pydantibase import TableModel

class ExampleTable(TableModel):
    table_name_: Literal["examples"] = Field(
        default="examples", description="Table name", exclude=True
    )
    primary_keys_: list[str] = Field(
        default=["id"], description="Primary keys", exclude=True
    )
    id: int = Field(description="ID")
    name: str = Field(description="Name")
    value: float = Field(description="Value")
```

Now you can use `alembdantic` in your migrations since `ExampleModel` defines both the table layout and the row - convenient for validation, no need to specify table name since the row itself contains it, etc.

### create/delete table

```python

from pydantibase.alembdantic import opd
from models import ExampleTable


def upgrade() -> None:
    """Upgrade schema."""
    opd.create_table(ExampleTable)


def downgrade() -> None:
    """Downgrade schema."""
    opd.drop_table(ExampleTable)
```

### insert/remove data

Simple example:

```python

from pydantibase.alembdantic import opd
from models import ExampleTable

data = ExampleTable(id=42, name="Alice", value=2.718)

def upgrade() -> None:
    """Upgrade schema."""
    opd.insert(rows)


def downgrade() -> None:
    """Downgrade schema."""
    opd.delete_by(ExampleTable, "id", data.id)
```

Reading data for migration from a `.csv` file, `.json` or other? `TableModel` will auto-validate it for you. Example util based on `pydantibase`:

```python
def df2model(df: pd.DataFrame, model: Type[TableModel]) -> list[TableModel]:
    """
    Convert DataFrame to list of Model rows
    """
    records: list[dict[str, Any]] = df.to_dict(orient="records")
    ret = []

    for rec in records:
        ret.append(model(**rec))

    return ret
```

With this, you can migrate with

```python

from models import ExampleTable

from alembic_migrations.utils import df2model

rows = df2model(df, ExampleTable)

def upgrade() -> None:
    """Upgrade schema."""
    opd.insert(rows)


def downgrade() -> None:
    """Downgrade schema."""
    opd.delete(rows)
```

where calling `opd.delete()` will match every single field of each row to delete.

Otherwise use `opd.delete_by()` with the condition known to you based on the migrated data; or get table via `table = opd.read_table(ExampleModel)` (returns `sa.Table`), and fall back to standard `alembic` operations.

## sqlalchemic

The same `TableModel` can be recycled to use as `DeclarativeBase` for `sqlalchemy` (e.g. DB `Session`) - `sqlalchemic` module of `pydantibase` will translate it for you:

```python

from pydantibase.sqlalchemic import BaseMeta, Base

from models import ExampleTable

class ExampleTableBase(Base, metaclass=BaseMeta, model=ExampleTable):
    pass
```

Convenience: payload validation via pydantic + using `Session`

Example: add row

```python

@router.post("/add_data", response_model=MyResponseModel)
def add_project_cost_data(
    payload: ExampleTable, session: Session = Depends(get_db)
) -> MyResponseModel:

    db_row = ExampleTableBase(**payload.model_dump())
    session.add(db_row)
    session.commit()
```


-----
*Made with [poetic](https://github.com/sagitta42/poetic)*
