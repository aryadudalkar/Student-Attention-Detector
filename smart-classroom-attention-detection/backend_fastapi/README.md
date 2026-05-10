# FastAPI Backend

This backend replaces the Django API and keeps the same /api routes used by the frontend and scripts.

## Run

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend_fastapi.main:app --reload --port 8000
```

The API will be available at http://127.0.0.1:8000/api
The interactive docs will be at http://127.0.0.1:8000/docs
