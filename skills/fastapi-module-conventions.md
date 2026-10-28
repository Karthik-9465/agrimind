# FastAPI Module Conventions — Agrimind Agentic

Each feature module under `app/modules/<module_name>` should adhere to the following file layout:

```
app/modules/<module_name>/
├── router.py     # FastAPI APIRouter endpoints
├── schemas.py    # Pydantic request/response models
├── service.py    # Core business logic
└── models.py     # (Optional module-specific DB models, or in app/db/models.py)
```

## Key Rules:
1. Routers handle HTTP request parsing, response codes, and dependency injection (`get_db`, `get_current_user`).
2. Services handle database queries and business logic.
3. Schemas use Pydantic `BaseModel` with `ConfigDict(from_attributes=True)`.
4. Password hashing and authentication tokens use `passlib` with `bcrypt` and `python-jose`.
