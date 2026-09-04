# pydantic-table

Use pydantic model as single source of truth for payload definition, SQLAlchemy table schema, and alembic migrations.

```bash
pip install poetiq
```

or for most recent developments

```bash
pip install https://github.com/sagitta42/pydantic-table.git
```

## `TableModel` and `ColumnField`

```python
# tables.py
from pydantic_table import ColumnField, TableModel

class ExampleTable(TableModel, table_name="examples"):
    id: int = ColumnField(description="ID", primary_key=True)
    name: str = ColumnField(description="Name")
    value: float = ColumnField(description="Value", nullable=True)    
```

```python
>>> ExampleTable.column_fields()
{
 'id': ColumnFieldInfo(annotation=int, required=True, primary_key=True, nullable=False),
 'name': ColumnFieldInfo(annotation=str, required=True, primary_key=False, nullable=False),
 'value': ColumnFieldInfo(annotation=float, required=True, primary_key=False, nullable=True)
}
>>> row = ExampleTable(id=42, name="Alice", value=1.618)
>>> row.model_dump()
{'table_name__': 'examples', 'missing_columns__': [], 'extra_columns__': {'new_column': 'foo'}, 'id': 42, 'name': 'Alice', 'value': 1.618}
>>> row.column_dump()
{'id': 42, 'name': 'Alice', 'value': 1.618}
```

- `TableModel` is a pydantic `BaseModel`
  - model field name = column name
  - model field annotation = column data type
  - `TableModel.column_fields()` returns `dict[str, ColumnFieldInfo]`
  - `ColumnFieldInfo` is `FieldInfo` with extra properties `primary_key` and `nullable`
  - `model_dump()` returns all fields including special internal fields - see [alembic](#alembic) section on the roles of `missing_columns__` and `extra_columns__`
  - `column_dump()` returns actual columns

- **One source of truth**:
  - class defines **table schema**

  - instance represents a **data row**

  - **validation** via pydantic at earliest stage (e.g. before alembic migrations, in-app DB calls etc.)

  - defines **payload** for API

  - **adaptors** for `sa.Column` and `sa.Table` from `sqlalchemy` in `pydantic_table.sqlalchemy`

    ```python
    sa_column: sa.Column = Column("id", column_field_info, foreign_key="another_table.name")
    sa_table: sa.Table = Table(ExampleTable, autoload_with=op.get_bind())
    ```

  - **adaptor** for `DeclarativeBase` from `sqlalchemy` via **BaseMeta** in `pydantic_table.sqlalchemy` - see [sqlalchemy](#sqlalchemy) section

    ```python
    class ExampleTableBase(Base, metaclass=BaseMeta, model=ExampleTable)
    ```

- **Schema changes** easily tracked

  - update to `TableModel` child class is auto-reflected in payload and DB Base **at the same time**
  - **backwards compatibility** via alembic adaptors in `pydantic_table.alembic.op`: `ExampleTable` can be updated directly by adding/removing column fields, followed by an add/drop column migration; previous migrations are not broken if `op.drop_column()` and `op.drop_table()` adaptors are used - see [alembic](#alembic) section

## sqlalchemy

### `sa.Column` and `sa.Table` adaptors

Get `sa.Table`  from your `TableModel`:

```python
import pydantic_table.sqlalchemy as sap
from tables import ExampleTable

table = sap.Table(ExampleTable, autoload_with=op.get_bind())
```

Get single `sa.Column` from your `ColumnFieldInfo`:

```python
column_info = ExampleTable.column_fields()["id"]
sap.Column("id", column_info, foreign_key="another_table.name")
```

### `Base` adaptor

Translate `TableModel` into `DeclarativeBase` :

```python
# models.py
from sqlalchemy.orm import DeclarativeBase
from pydantic_table.sqlalchemy import BaseMeta

from tables import ExampleTable

class Base(DeclarativeBase):
    pass

class ExampleTableBase(Base, metaclass=BaseMeta, model=ExampleTable):
    pass
```

Convenience: **shared definition** between **db models** and **payload schemas**

```python
# schemas.py
from tables import ExampleTable

class MyPayload(BaseModel):
    row: ExampleTable
    other_stuff: 42
```

```python
# db.py
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = create_engine(<get_url()>, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# routes/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from schemas import MyPayload

router = APIRouter()

@router.post("/add_data", response_model=MyResponseModel)
def add_data(
    payload: MyPayload, session: Session = Depends(get_db)
) -> MyResponseModel:

    db_row = ExampleTableBase(**payload.row.model_dump())
    session.add(db_row)
    session.commit()
```

Once model under **tables** is updated, there is no need to update either **schemas** or **models** - seamless update to router endpoint payload and DB interaction.

## alembic

### create/delete table

```python
from alembic import op

from pydantic_table.alembic import op as opp # avoid conflict with op
from tables import ExampleTable

def upgrade() -> None:
    """Upgrade schema."""
    opp.create_table(ExampleTable)


def downgrade() -> None:
    """Downgrade schema."""
    opp.drop_table(ExampleTable)
```

Backwards compatibility:

- If **new column fields** are added to or **old column fields are dropped** from `ExampleTable` at the future point, the old revision above **is not broken**,

- If this revision is "re-migrated" via downgrade followed by upgrade, `opp` will detect said schema change comparing it to the table schema at drop moment, and **archive a snapshot of table model** in this revision under `versions/.archive`.

- The re-upgrade will re-create table based on archived `TableModel` rather than the changed one
- **Make sure** to **NOT DELETE** the archive `*.json` revision files - keep track of them the same way the `*.py` revision files are managed

### insert/remove data

```python
from alembic import op

from pydantic_table.alembic import op as opp
from tables import ExampleTable

data = ExampleTable(id=42, name="Alice", value=2.718)
def upgrade() -> None:
    """Upgrade schema."""
	# id will be stored under extra columns even if dropped from ExampleTable in the future
    opp.insert(data) # table name is already stored in ExampleTable

def downgrade() -> None:
    """Downgrade schema."""
    # getter will extract "id" from extra columns data even if column is removed in the future
    opp.delete_where(ExampleTable, id=data.get("id"))
```

Backwards compatibility:

- If new column fields are added to `ExampleTable` in the future, they will be ignored as they are not provided in the migration's data, and are not present in the table at that revision
- If column fields are removed from `ExampleTable` in the future, this will not break the migration as `TableModel` will store the extra field values internally, and retrieve them by detecting those columns in database at that revision
- The getter `data.get("id")` extracts "id" value from extra columns even if "id" is eventually removed from `ExampleTable` in a future schema update. Alternatively, use `id=42`, `ExampleTable(id=id, ...)` and `opp.delete_where(..., id=id)`

### add column

Update `ExampleTable` schema:

```python
# tables.py
class ExampleTable(TableModel, table_name="examples"):
    id: int = ColumnField(description="ID", primary_key=True)
    name: str = ColumnField(description="Name")
    value: float = ColumnField(description="Value")
    new_column: str = ColumnField(default="", description="new_column") # NEW
```

Column has default or is nullable:

```python
def upgrade() -> None:
    """Upgrade schema."""
    # column has default or is nullable, so can be added without data
    opp.add_column(ExampleTable, "new_column")
    # column is not nullable and does not have a default so cannot be added without data
    # row or list of rows with values for new column
    # and values for other columns for where condition as column=value
    data = ExampleTable(id=42, new_column="foo")
    opp.add_column(ExampleTable, "new_column", data=data)

def downgrade() -> None:
    """Downgrade schema."""
    opp.drop_column(ExampleTable, "new_column")
```

### remove column

Update `ExampleTable` schema:

```python
# tables.py
class ExampleTable(TableModel, table_name="examples"):
    id: int = ColumnField(description="ID", primary_key=True)
    name: str = ColumnField(description="Name")
#    value: float = ColumnField(description="Value") <-- remove column
```

Same as in adding a column, re-add column with data if not nullable and does not have default:

```python
def upgrade() -> None:
    """Upgrade schema."""
    # pydantic_table.alembic.op will detect column present in table but not in TableModel
    # will archive field information to be able to re-add column in downgrade
    opp.drop_column(ExampleTable, "value")


def downgrade() -> None:
    """Downgrade schema."""
    # TODO: auto-read field info and data from archive
    opp.add_column(ExampleTable, "value") 
    # if column does not have default, so must be added with data
    # data = ExampleTable(id=42, value=2.718)
    # opp.add_column(ExampleTable, "value", data=data)
```

Backwards compatibility:

Here downgrade is possible even though information on properties of `"value"` column such as primary key, nullable etc. are not present in `ExampleTable` anymore because at `drop_column()` its absence will be detected by `opp`, and an archive of column field info will be saved in the revision archive, similar to deleting table.

### fallback to alembic op

Easy fallback to standard alembic op by using `sap.Column` and `sap.Table` adaptors described in the [sqlalchemy](#sqlalchemy) section, and performing standard `op` operations "manually".

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

def upgrade() -> None:
    """Upgrade schema."""
    rows = df2model(df, ExampleTable)    
    opp.insert(rows)


def downgrade() -> None:
    """Downgrade schema."""
    opp.delete_where(ExampleTable, column1=value1, column2=value2, ...) # you need to know your condition
    # opp.deep_delete(rows) <- will delete where column=value for each column for each row
```




-----
*Made with [poetic](https://github.com/sagitta42/poetic)*