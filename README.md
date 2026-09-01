# Recon Dashboard

A reconciliation dashboard that matches orders against payments, classifies
mismatches, and surfaces discrepancies for review.

## Architecture

```
├── backend/    FastAPI + SQLAlchemy async + PostgreSQL + Alembic
└── frontend/   React + TypeScript + Vite
```

## Backend

### Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Ensure PostgreSQL is running and the `recon` database exists.  The default
connection string is configured in `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/recon
```

### Run migrations

```bash
alembic upgrade head
```

### Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

### Run tests

```bash
pytest
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/signup` | Create account, returns JWT |
| POST | `/auth/login` | Log in, returns JWT |
| GET | `/users/me` | Current user profile |
| POST | `/uploads/orders` | Upload orders CSV |
| POST | `/uploads/payments` | Upload payments CSV |
| POST | `/reconcile/run` | Run reconciliation engine |
| GET | `/dashboard/summary` | High-level metrics |
| GET | `/dashboard/breakdown` | Discrepancy counts by type |
| GET | `/dashboard/discrepancies` | Paginated discrepancy rows |

## Frontend

### Setup

```bash
cd frontend
npm install
```

### Start the dev server

```bash
npm run dev
```

The dev server runs on port 5173 and proxies API requests to the backend on
port 8000 (see `vite.config.ts`).

## Authentication & JWT Storage

The frontend uses an **in-memory JWT** pattern:

- The token lives in React context state (`AuthContext.tsx`).
- It is **never** written to `localStorage`, `sessionStorage`, or a
  JavaScript-readable cookie.
- It is injected into API requests via the `Authorization: Bearer` header.

### Tradeoffs

| Approach | XSS risk | Persists on refresh | Persists across tabs |
|----------|----------|---------------------|----------------------|
| **In-memory (chosen)** | Immune | No | No |
| localStorage | Vulnerable | Yes | Yes |
| httpOnly cookie | Immune | Yes | Yes |

**Why in-memory:** For an internal reconciliation tool used in focused
sessions, the security benefit outweighs the convenience cost.  A token in
`localStorage` is readable by any JavaScript running on the page (including
third-party scripts and XSS payloads).  Keeping it in memory means there is
no persistent token to steal.

**Upgrade path:** If persistence is needed later, the most secure option is
an `httpOnly` + `SameSite=Strict` cookie set by the backend on the auth
response.  This keeps the token out of JavaScript entirely while surviving
refreshes and tabs.  The frontend would then send credentials with
`credentials: "include"` and never handle the token directly.

### Consequences

- **Page reload** → user must log in again.
- **Multiple tabs** → each tab is an independent session (must log in
  separately).

## Reconciliation Engine

The engine (`backend/app/reconcile.py`) is a **pure function**: given the
same orders and payments, it always produces the same discrepancies.  No LLM,
no side effects, no database access.

### Discrepancy Types

| Type | Meaning |
|------|---------|
| `missing_payment` | Order exists, no payment references it |
| `missing_order` | Payment references a non-existent order |
| `amount_mismatch` | Payments sum != order net_amount (outside tolerance) |
| `duplicate_payment` | Same transaction_ref appears more than once |
| `refund_unmatched` | Negative payment with no matching order |

### Tolerance

`$0.50` or `1%` of the order net_amount, whichever is greater.  This absorbs
rounding differences while scaling with order size.
