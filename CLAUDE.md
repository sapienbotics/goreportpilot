# CLAUDE.md — ReportPilot Project Instructions

## Project Overview
**ReportPilot** — AI-powered client reporting tool for digital marketing agencies and freelancers.
Automates the workflow of pulling data from Google Analytics, Meta Ads, and Google Ads, generating AI-written narrative insights, and exporting branded reports as PowerPoint and PDF.

**Founder:** Saurabh Singh / SapienBotics (New Delhi, India)
**Stage:** Building MVP (4-week timeline)

---

## Tech Stack (Exact Versions)

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | Next.js (App Router) | 14.x (latest stable) | Web app + marketing pages |
| Frontend Language | TypeScript | 5.x | Type safety |
| CSS Framework | Tailwind CSS | 3.x | Styling |
| UI Components | shadcn/ui | latest | Pre-built accessible components |
| Backend API | Python + FastAPI | Python 3.11+, FastAPI 0.110+ | OAuth, data pulls, AI, report gen |
| Database | Supabase (PostgreSQL) | latest | Data storage, RLS, auth |
| Auth | Supabase Auth | (included with Supabase) | User signup/login, Google SSO, JWT |
| AI | OpenAI API (GPT-4o) | latest | Narrative commentary generation |
| Report Gen | python-pptx 0.6.23+ | latest stable | PowerPoint generation |
| Report Gen | ReportLab 4.x | latest stable | PDF generation |
| Charts | matplotlib 3.8+ | latest stable | Static chart images for reports |
| Scheduling | n8n (self-hosted) | latest | Cron jobs, token checks, email scheduling |
| Email | Resend | latest | Branded report delivery emails |
| Frontend Hosting | Vercel | — | Next.js deployment |
| Backend Hosting | Railway | — | FastAPI deployment |
| File Storage | Supabase Storage | — | Generated PPT/PDF files |
| Payments | Stripe | latest API | Subscription billing |
| Token Encryption | cryptography (Python) | 42.x+ | AES-256-GCM for OAuth tokens |

---

## Project Directory Structure

```
reportpilot/
├── CLAUDE.md                    # THIS FILE — master instructions
├── README.md                    # Public readme
├── .env.example                 # Environment variable template
├── .gitignore
│
├── frontend/                    # Next.js app
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── public/
│   │   └── images/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   │   ├── layout.tsx       # Root layout (fonts, metadata, providers)
│   │   │   ├── page.tsx         # Landing page (marketing — public)
│   │   │   ├── pricing/
│   │   │   │   └── page.tsx
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── signup/
│   │   │   │   └── page.tsx
│   │   │   ├── dashboard/       # Authenticated app shell
│   │   │   │   ├── layout.tsx   # Dashboard layout (sidebar + header)
│   │   │   │   ├── page.tsx     # Dashboard home
│   │   │   │   ├── clients/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [clientId]/
│   │   │   │   │       ├── page.tsx
│   │   │   │   │       ├── reports/
│   │   │   │   │       │   └── page.tsx
│   │   │   │   │       └── connections/
│   │   │   │   │           └── page.tsx
│   │   │   │   ├── reports/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [reportId]/
│   │   │   │   │       ├── page.tsx
│   │   │   │   │       └── deliver/
│   │   │   │   │           └── page.tsx
│   │   │   │   ├── integrations/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── settings/
│   │   │   │       └── page.tsx
│   │   │   └── api/             # Next.js API routes (thin proxy/callbacks)
│   │   │       └── auth/
│   │   │           └── callback/
│   │   │               ├── route.ts   # Supabase auth callback
│   │   │               ├── google-analytics/
│   │   │               │   └── route.ts
│   │   │               └── meta-ads/
│   │   │                   └── route.ts
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui base components
│   │   │   ├── dashboard/       # Dashboard widgets, stat cards
│   │   │   ├── clients/         # Client cards, forms, detail views
│   │   │   ├── reports/         # Report preview, editor, delivery
│   │   │   └── layout/          # Sidebar, Header, Footer, Nav
│   │   ├── lib/
│   │   │   ├── supabase/
│   │   │   │   ├── client.ts    # Browser Supabase client
│   │   │   │   ├── server.ts    # Server-side Supabase client
│   │   │   │   └── middleware.ts # Supabase auth helper for middleware
│   │   │   ├── api.ts           # Axios/fetch wrapper for FastAPI backend
│   │   │   └── utils.ts         # General helpers (formatDate, formatCurrency, etc.)
│   │   ├── hooks/
│   │   │   ├── useAuth.ts       # Auth state hook
│   │   │   └── useClients.ts    # Client data hook (example)
│   │   ├── types/
│   │   │   └── index.ts         # Shared TypeScript interfaces
│   │   └── styles/
│   │       └── globals.css      # Tailwind directives + custom CSS vars
│   └── middleware.ts            # Next.js middleware — protect /dashboard/*
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app entry, CORS, router includes
│   ├── config.py                # Pydantic Settings — loads .env
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py              # OAuth callback endpoints (GA4, Meta, Google Ads)
│   │   ├── clients.py           # Client CRUD endpoints
│   │   ├── connections.py       # Connection management endpoints
│   │   ├── reports.py           # Report generation, list, detail
│   │   ├── data_pull.py         # Manual data pull trigger endpoint
│   │   └── webhooks.py          # Stripe + Resend webhooks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── google_analytics.py  # GA4 Data API client
│   │   ├── meta_ads.py          # Meta Marketing API client
│   │   ├── google_ads.py        # Google Ads API client (Phase 2)
│   │   ├── ai_narrative.py      # OpenAI GPT-4o prompt engine
│   │   ├── report_generator.py  # python-pptx + ReportLab orchestration
│   │   ├── chart_generator.py   # matplotlib chart rendering to PNG
│   │   ├── email_service.py     # Resend SDK wrapper
│   │   └── encryption.py        # AES-256-GCM encrypt/decrypt for tokens
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic request/response models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── token_manager.py     # Token refresh logic, health check
│   │   └── data_parser.py       # Normalize GA4/Meta/Ads API responses
│   └── templates/
│       ├── report_default.py    # Default report template configuration
│       └── email_templates/
│           └── report_delivery.html
│
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
│
├── n8n/
│   └── workflows/
│       ├── daily_data_pull.json
│       ├── token_health_check.json
│       ├── scheduled_report_delivery.json
│       └── stripe_webhook_handler.json
│
├── docs/
│   ├── reportpilot-deep-dive.md
│   ├── reportpilot-feature-design-blueprint.md
│   └── reportpilot-auth-integration-deepdive.md
│
└── scripts/
    ├── setup_supabase.sh
    └── seed_test_data.py
```

---

## How to Run Locally

### Prerequisites
- Node.js 20+ and npm
- Python 3.11+
- Git
- A Supabase project (free tier)
- n8n (optional for Phase 1 — needed in Phase 4)

### Frontend (Next.js)
```bash
cd frontend
npm install
cp .env.local.example .env.local   # Fill in Supabase URL + anon key
npm run dev                         # Runs on http://localhost:3000
```

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # Fill in all secrets
uvicorn main:app --reload --port 8000   # Runs on http://localhost:8000
```

### Both Together (Development)
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Frontend calls backend via `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

## Environment Variables

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Backend (`backend/.env`)
```
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Google OAuth (GA4 + Google Ads)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google-analytics

# Meta OAuth
META_APP_ID=your-meta-app-id
META_APP_SECRET=your-meta-app-secret
META_REDIRECT_URI=http://localhost:3000/api/auth/callback/meta-ads

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Token Encryption
TOKEN_ENCRYPTION_KEY=base64-encoded-32-byte-key

# Stripe
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_AGENCY=price_xxx

# Resend
RESEND_API_KEY=your-resend-api-key

# App
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development
```

---

## Database (Supabase)

The full schema is defined in `supabase/migrations/001_initial_schema.sql`.

**7 core tables:** users (extends Supabase auth.users), clients, connections, data_snapshots, reports, report_templates, report_deliveries, scheduled_reports.

**Row-Level Security (RLS):** MUST be enabled on every table from Day 1. Every table with user data has a policy: `auth.uid() = user_id` (or joined through clients table). See the migration file for exact policies.

**Important:** Run migrations via Supabase Dashboard SQL editor or Supabase CLI. Never create tables manually through the Table Editor — always use SQL migrations for reproducibility.

---

## Key Architectural Decisions

### 1. Monorepo (frontend/ + backend/ in one repo)
**Why:** Solo developer. Simplifies version control, deployment coordination, and shared types. No need for separate repos until team grows.

### 2. Next.js App Router (not Pages Router)
**Why:** App Router is the current standard. Server Components reduce client JS. Layouts enable shared dashboard shell. Route groups organize public vs authenticated pages.

### 3. FastAPI backend (not Next.js API routes for everything)
**Why:** The backend does heavy work — OAuth token exchange, API data pulls, AI calls, PPT/PDF generation. Python is the right language for python-pptx, ReportLab, matplotlib, and the Google/Meta SDKs. Next.js API routes are only used as thin callback proxies for OAuth redirects.

### 4. Supabase (not Firebase, not raw PostgreSQL)
**Why:** Gives us PostgreSQL + Auth + Storage + RLS + REST API in one hosted service. Free tier is generous enough for MVP. RLS is critical for multi-tenant data isolation.

### 5. OAuth callbacks go through Next.js API routes, then forward to FastAPI
**Why:** Google and Meta redirect to your app domain. The Next.js API route receives the callback, then forwards the auth code to FastAPI for token exchange. This avoids CORS issues and keeps the backend URL private.

### 6. Token encryption at application level (AES-256-GCM)
**Why:** Supabase encrypts at rest, but if someone accesses the Supabase dashboard or gets a DB dump, tokens would be readable. Application-level encryption means tokens are unreadable without the encryption key (stored as env var, never in DB).

### 7. n8n for scheduling (not Celery or cron)
**Why:** Founder is an n8n expert with years of experience. n8n provides visual workflow management, easy debugging, webhook triggers, and built-in retry logic. Self-hosted = free.

### 8. shadcn/ui for UI components
**Why:** Copy-paste components (not a dependency). Accessible, customizable, works perfectly with Tailwind. Avoids vendor lock-in.

---

## Coding Conventions

### Frontend (TypeScript + React)
- **Language:** TypeScript everywhere. No `any` types unless absolutely unavoidable (comment why).
- **Components:** Functional components only. Use React hooks.
- **File naming:** `kebab-case` for files (`client-card.tsx`), `PascalCase` for component names (`ClientCard`).
- **Page files:** Always `page.tsx` (Next.js convention).
- **Imports:** Use `@/` path alias for `src/` directory (configured in tsconfig).
- **State management:** React Context + hooks for global state (auth, user). No Redux. Use SWR or React Query for server state.
- **Styling:** Tailwind utility classes. Use `cn()` helper (from shadcn/ui) for conditional classes. No CSS modules, no styled-components.
- **Forms:** Use React Hook Form + Zod for validation.
- **API calls:** Use a centralized `api.ts` client. Never call `fetch()` directly in components.

### Backend (Python)
- **Language:** Python 3.11+. Use type hints everywhere.
- **Framework:** FastAPI with async endpoints where possible.
- **File naming:** `snake_case` for all Python files.
- **Models:** Pydantic v2 models for all request/response schemas.
- **Config:** Use `pydantic-settings` for environment variable loading (config.py).
- **Error handling:** Use FastAPI HTTPException with meaningful status codes and messages.
- **Logging:** Use Python `logging` module. Log INFO for normal operations, WARNING for token issues, ERROR for failures. NEVER log tokens or secrets.
- **Async:** Use `async/await` for I/O operations (API calls, DB queries). Use `httpx` for HTTP requests (not `requests` library — it's sync-only).
- **Security:** All token operations go through `services/encryption.py`. No plaintext tokens anywhere.

### General
- **Git commits:** Commit after every working feature. Use conventional commit messages: `feat: add client CRUD`, `fix: handle empty GA4 response`, `chore: update env template`.
- **No console.log in production code.** Use a proper logger.
- **No hardcoded values.** All configuration through environment variables.
- **No secrets in code.** Ever. Use .env files (gitignored) and environment variables.

---

## Design System (For UI Implementation)

- **Primary color:** Deep Indigo `#4338CA` (Tailwind: `indigo-700`)
- **Accent/Success:** Emerald `#059669` (Tailwind: `emerald-600`)
- **Danger:** Rose `#E11D48` (Tailwind: `rose-600`)
- **Warning:** Amber `#D97706` (Tailwind: `amber-600`)
- **Background:** White `#FFFFFF` + Slate-50 `#F8FAFC` for sections
- **Primary text:** Slate-900 `#0F172A`
- **Secondary text:** Slate-500 `#64748B`
- **Heading font:** Plus Jakarta Sans (Google Fonts)
- **Body font:** Inter (Google Fonts)
- **Border radius:** `rounded-lg` (8px) for cards, `rounded-md` (6px) for buttons/inputs
- **Shadows:** `shadow-sm` for cards, `shadow-md` on hover

---

## What NOT To Do (Critical Pitfalls)

1. **DO NOT expose OAuth tokens to the frontend.** Tokens live in the backend only. The frontend knows "connected" or "not connected" — never the token value.

2. **DO NOT use `localStorage` for auth tokens.** Use `httpOnly` cookies via Supabase Auth. Supabase handles this automatically.

3. **DO NOT skip Row-Level Security.** Every table with user data MUST have RLS policies before any data is inserted. Test that User A cannot see User B's data.

4. **DO NOT confuse Google SSO login with Google Analytics OAuth.** They are completely separate flows with different scopes, different tokens, different purposes. Google SSO = logging into ReportPilot. GA4 OAuth = connecting a client's analytics property.

5. **DO NOT use the `requests` library in FastAPI.** Use `httpx` with async. The `requests` library is synchronous and will block the event loop.

6. **DO NOT store the encryption key in the database.** It lives in environment variables only.

7. **DO NOT create database tables through the Supabase Table Editor.** Always use SQL migrations in `supabase/migrations/`. This ensures reproducibility.

8. **DO NOT build the frontend before the backend endpoint exists.** Build API → test with curl → build UI → connect.

9. **DO NOT include `prompt=consent` only sometimes for Google OAuth.** ALWAYS include `prompt=consent&access_type=offline` to guarantee a refresh token.

10. **DO NOT assume Meta tokens last forever.** Long-lived user tokens expire after 60 days. Store `token_expires_at` and build health check logic from Day 1.

11. **DO NOT log OAuth tokens or encryption keys.** Not in application logs, not in error output, not in debug messages. Log connection IDs and status only.

12. **DO NOT import from relative paths in frontend.** Always use the `@/` alias (e.g., `import { Button } from '@/components/ui/button'`).

13. **DO NOT skip error handling on API responses.** Every fetch call must handle network errors, 4xx, and 5xx responses gracefully with user-friendly messages.

---

## Spec Documents (Reference Before Implementing)

These three documents contain the complete product specification. **Read the relevant section BEFORE implementing any feature.**

1. **`docs/reportpilot-deep-dive.md`**
   Business case, competitor pricing, market analysis, pricing strategy ($19/$39/$69), go-to-market plan, revenue projections, risk register, 30-day launch plan.

2. **`docs/reportpilot-feature-design-blueprint.md`**
   Every screen wireframed, all user flows, AI prompt architecture (4 tone presets), report template structure (10 slides), database schema (7 tables with exact fields), integration architecture, notification system, white-label system, billing/plan details, error handling matrix, design system, phased roadmap.

3. **`docs/reportpilot-auth-integration-deepdive.md`**
   Complete OAuth flows (Google + Meta + Google Ads) with code examples, token storage encryption (AES-256-GCM), token lifecycle management, Google OAuth verification process, Meta App Review process, multi-account/property selection, connection health monitoring, security architecture, testing strategy, common pitfalls.

---

## Phased Build Plan

### Phase 1: Foundation (Week 1)
- Project scaffolding (this directory structure)
- Next.js + TypeScript + Tailwind + shadcn/ui setup
- Supabase project + database schema + RLS policies
- Supabase Auth (signup, login, Google SSO, protected routes)
- Landing page (marketing: hero, features, pricing, footer)
- Dashboard layout (sidebar, header, empty state)

### Phase 2: Integrations (Week 2)
- Google Cloud Project + OAuth credentials setup
- GA4 OAuth flow (complete: button → callback → tokens → property list → store)
- Meta Ads OAuth flow (complete: button → callback → short→long token → account list → store)
- Token encryption (AES-256-GCM) from Day 1
- Client CRUD (create, list, view, edit, delete)
- Connection management (link GA4/Meta accounts to clients)

### Phase 3: Data + AI + Reports (Week 3)
- GA4 data pull service
- Meta Ads data pull service
- Data normalization + storage in data_snapshots
- AI narrative engine (GPT-4o with prompt templates + tone presets)
- Report generation (python-pptx + ReportLab + matplotlib charts)
- Report preview UI in browser

### Phase 4: Delivery + Polish (Week 4)
- Report editor (inline editing, section toggle/reorder)
- Email delivery (Resend with branded templates + attachments)
- Scheduled reports (n8n workflows)
- White-label (logo, colors, branded sender)
- Stripe billing (checkout, plan management, webhooks)
- Token health checks (n8n workflow + user alerts)
- Testing, bug fixes, deploy to Vercel + Railway
