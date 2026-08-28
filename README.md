# pydantic-table

Use pydantic model as single source of truth for SQLAlchemy table definition and alembic migrations.

```python
pip install https://github.com/sagitta42/pydantic-table.git@v0.3.0
```

## `TableModel`

Example:

```python
from pydantic_table import ColumnField, TableModel

class ExampleTable(TableModel, table_name="examples"):
    id: int = ColumnField(description="ID", primary_key=True)
    name: str = ColumnField(description="Name")
    value: float = ColumnField(description="Value", nullable=True)
```

`TableModel` is a pydantic `BaseModel` that defines:

- Column information via `ColumnField()` definition:
  - name: field name
  - type: field annotation
  - other properties: `default` from standard `Field` (`FieldInfo`) property, `primary_key` and `nullable` properties from `ColumnField` (`ColumnFieldInfo`) additional properties
- **One source of truth**:
  - class defines **table schema**
  - instance represents a **data row**
  - **validation** via pydantic at earliest stage (e.g. before alembic migrations, in-app DB calls etc.)
  - defines **payload** for API
  - compatible with `Table` and `DeclarativeBase` from `sqlalchemy`  via adaptors in `pydantic_table.sqlalchemy` - see [sqlalchemy][#sqlalchemy] section
- **Schema changes backwards compatibility** via alembic adaptors in `pydantic_table.alembic`: `ExampleTable` can be updated directly by adding/removing column fields, followed by an add/drop column migration; previous migrations are not broken if adaptors are used - see [alembic][#alembic] section

## alembic

### create/delete table

```python
from alembic import op

from pydantic_table.alembic import op as opp # avoid conflict with op
from models import ExampleTable

def upgrade() -> None:
    """Upgrade schema."""
    # specify columns explicitly to account for potential future changes to ExampleTable schema
    opp.create_table(ExampleTable, columns=["id", "name", "value"])


def downgrade() -> None:
    """Downgrade schema."""
    opp.drop_table(ExampleTable)
```

Backwards compatibility:

- If new column fields are added to `ExampleTable` in the future, they will be ignored during table creation - it uses only specified columns.

- *If columns are removed, backwards compatibility currently not supported /does not have a solution, as column information such as nullability, primary key, default etc. is lost*

### insert/remove data

```python
from alembic import op

from pydantic_table.alembic import op as opp
from models import ExampleTable

data = ExampleTable(id=42, name="Alice", value=2.718)

def upgrade() -> None:
    """Upgrade schema."""
    opp.insert(data)

def downgrade() -> None:
    """Downgrade schema."""
    opp.delete_where(ExampleTable, id=data.get("id")
```

Backwards compatibility:

- If new column fields are added to `ExampleTable` in the future, they will be ignored as they are not provided in the migration's data, and are not present in the table at that revision
- If columnd fields are removed from `ExampleTable` in the future, this will not break the migration as `TableModel` will store the extra field values internally, and retrieve them by detecting those columns in database at that revision
- **IMPORTANT**: Make sure to use `data.get("id")` rather than `data.id` to avoid crash for that exact reason

## utils/validation

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
    opp.delete_where(ExampleTable, column1=value1, column2=value2, ...) # you need to know your condition
    # opp.deep_delete(rows) <- will delete where column=value for each column for each row
```

where calling `opp.delete()` will match every single field of each row to delete.

Otherwise use `opp.delete_by()` with the condition known to you based on the migrated data; or get table via `table = opp.read_table(ExampleModel)` (returns `sa.Table`), and fall back to standard `alembic` operations.

## sqlalchemy

The same `TableModel` can be recycled to use as `DeclarativeBase` for `sqlalchemy` (e.g. DB `Session`) - `sqlalchemy` module of `pydantic_table` will translate it for you:

```python
from sqlalchemy.orm import DeclarativeBase
from pydantic_table.sqlalchemy import BaseMeta

from models import ExampleTable

class Base(DeclarativeBase):
    pass

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