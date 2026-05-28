# Frontend Setup

The frontend requires Node.js 18+.

```bash
cd frontend
npm install
npm run dev
```

The backend now lives in `backend/`:

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/api/v1/health
```
