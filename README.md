# pydantic-table

Use pydantic model as single source of truth for SQLAlchemy table definition and alembic migrations.

## `TableModel`

`TableModel` is a pydantic `BaseModel` that defines:
- table name and primary keys in special `table_name_` and `primary_keys_` fields
- column names via its fields, column types via field types (`FieldInfo` annotation)
- column nullability via `default` (default=None means nullable)
- table model class defines table layout but also a row that can be used for migrations (see `pydantic_table.alembic`)

## alembic

Set up your alembic migrations with alembic as you usually do.

Create a `models.py` utils class inside your alembic migrations folder, and define your table model there.

```python
from pydantic_table import TableModel

class ExampleTable(TableModel, table_name="examples", primary_keys=["id"]):
    id: int = Field(description="ID")
    name: str = Field(description="Name")
    value: float = Field(description="Value")
```

Now you can use `pydantic_table` alembic adapter in your migrations since `ExampleModel` defines both the table layout and the row - convenient for validation, no need to specify table name since the row itself contains it, etc.

### create/delete table

```python
from pydantic_table.alembic import op as opp
from models import ExampleTable


def upgrade() -> None:
    """Upgrade schema."""
    opp.create_table(ExampleTable, columns=["id", "name", "value"])


def downgrade() -> None:
    """Downgrade schema."""
    opp.drop_table(ExampleTable)
```

Note that you need to specify the columns explicitly for backwards compatibility with schema changes: in later migrations, you may update `ExampleTable` schema e.g. add a new field representing a new column; this won't break older migrations since columns are specified explicitly. Specified columns still do have to correspond to the ones defined in the model.

### insert/remove data

Simple example:

```python
from pydantic_table.alembic import op as opp
from models import ExampleTable

data = ExampleTable(id=42, name="Alice", value=2.718)

def upgrade() -> None:
    """Upgrade schema."""
    opp.insert(data)


def downgrade() -> None:
    """Downgrade schema."""
    opp.delete_by(ExampleTable, "id", data.id)
```

Reading data for migration from a `.csv` file, `.json` or other? `TableModel` will auto-validate it for you. Example util based on `pydantic_table`:

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

# avoid placing here if large CSV or will take time during context run
rows = df2model(df, ExampleTable)

def upgrade() -> None:
    """Upgrade schema."""
    opp.insert(rows)


def downgrade() -> None:
    """Downgrade schema."""
    opp.delete(rows)
```

where calling `opp.delete()` will match every single field of each row to delete.

Otherwise use `opp.delete_by()` with the condition known to you based on the migrated data; or get table via `table = opp.read_table(ExampleModel)` (returns `sa.Table`), and fall back to standard `alembic` operations.

## sqlalchemy

The same `TableModel` can be recycled to use as `DeclarativeBase` for `sqlalchemy` (e.g. DB `Session`) - `sqlalchemy` module of `pydantic_table` will translate it for you:

```python
from pydantic_table.sqlalchemy import BaseMeta, Base

from models import ExampleTable

class ExampleTableBase(Base, metaclass=BaseMeta, model=ExampleTable):
    pass
```

Convenience: payload validation via pydantic + using `Session`

Example: add row

```python
class MyPayload(BaseModel):
    row: ExampleTable
    other_stuff: 42
```

```python
@router.post("/add_data", response_model=MyResponseModel)
def add_project_cost_data(
    payload: MyPayload, session: Session = Depends(get_db)
) -> MyResponseModel:

    db_row = ExampleTableBase(**payload.row.model_dump())
    session.add(db_row)
    session.commit()
```


-----
*Made with [poetic](https://github.com/sagitta42/poetic)*
