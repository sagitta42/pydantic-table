# pydantic-table

Use pydantic model as single source of truth for SQLAlchemy table definition and alembic migrations.

```python
pip install https://github.com/sagitta42/pydantic-table.git@v0.3.0
```

## `TableModel`

Example:

```python
# tables.py
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

## sqlalchemy

### `sa.Column` and `sa.Table` adaptors

Get `sa.Table`  from your `TableModel`:

```python
import pydantic_table.sqlalchemy as sap
from tables import ExampleTable

table = sap.Table(ExampleTable, autoload_with=op.get_bind())
```

Get single `sa.Column`:

```python
sap.Column("id", ExampleTable, foreign_key="another_table.name")
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

Example:

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
from tables import ExampleTable

data = ExampleTable(id=42, name="Alice", value=2.718)

def upgrade() -> None:
    """Upgrade schema."""
    # table name is already stored in ExampleTable
    opp.insert(data)

def downgrade() -> None:
    """Downgrade schema."""
    opp.delete_where(ExampleTable, id=data.get("id"))
```

Backwards compatibility:

- If new column fields are added to `ExampleTable` in the future, they will be ignored as they are not provided in the migration's data, and are not present in the table at that revision
- If columnd fields are removed from `ExampleTable` in the future, this will not break the migration as `TableModel` will store the extra field values internally, and retrieve them by detecting those columns in database at that revision
- **IMPORTANT**: Make sure to use `data.get("id")` rather than `data.id` to avoid crash for that exact reason

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

### fallback to alembic op

Easy fallback to standard alembic op by using `sap.Column` and `sap.Table` adaptors described in the [sqlalchemy][#sqlalchemy] section, and performing standard `op` operations "manually".

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