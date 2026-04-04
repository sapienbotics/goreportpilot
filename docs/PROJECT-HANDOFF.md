# ReportPilot — Project Handoff & Setup Guide

## Quick Overview
ReportPilot is an AI-powered client reporting tool for digital marketing agencies. It pulls data from Google Analytics, Meta Ads, and Google Ads, generates AI narrative insights, and exports branded reports as PowerPoint and PDF.

---

## System Dependencies

### Node.js 20+
Required for the Next.js frontend.
- Download: https://nodejs.org/
- Verify: `node --version`

### Python 3.11+
Required for the FastAPI backend.
- Download: https://www.python.org/downloads/
- Verify: `python --version`

### LibreOffice (Required for PDF generation)
LibreOffice is used to convert PPTX reports to PDF with full Unicode/multilingual support (Hindi, Japanese, Chinese, Arabic, etc.). The backend tries it first before falling back to ReportLab. Without LibreOffice, PDFs for non-Latin languages will not be generated and users will see "PDF unavailable — download PPTX instead."

**Local development — Windows:**
```
winget install LibreOffice.LibreOffice
```

**Local development — macOS:**
```
brew install --cask libreoffice
```

**Local development — Linux (Debian/Ubuntu):**
```
sudo apt-get update
sudo apt-get install -y libreoffice-core libreoffice-impress
```

After installation, verify with:
```
soffice --version
# OR
libreoffice --version
```

**Docker / Railway:** LibreOffice is automatically included in the Docker image (`backend/Dockerfile`). No manual installation needed for deployed environments.

### Noto Fonts (Required for non-Latin PDF quality)
Google Noto fonts ensure all scripts render correctly in both LibreOffice-converted and ReportLab PDFs.

**Linux (included in Docker image):**
```
sudo apt-get install -y fonts-noto-core fonts-noto-cjk fonts-noto-extra
```

**macOS:**
```
brew install font-noto-sans font-noto-sans-cjk
```

**Windows:** Download from https://fonts.google.com/noto and install.

---

## Environment Variables

### Frontend (`frontend/.env.local`)
Copy `frontend/.env.local.example` and fill in:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Backend (`backend/.env`)
Copy `backend/.env.example` and fill in:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
META_APP_ID=...
META_APP_SECRET=...
OPENAI_API_KEY=...
TOKEN_ENCRYPTION_KEY=<base64-encoded 32-byte key>
RESEND_API_KEY=...
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development
```

Generate a TOKEN_ENCRYPTION_KEY with:
```
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

---

## Local Development (Without Docker)

### 1. Database setup
- Create a Supabase project at https://supabase.com
- Run `supabase/migrations/001_initial_schema.sql` in the Supabase SQL editor

### 2. Backend
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in secrets
uvicorn main:app --reload --port 8000
```
API runs at http://localhost:8000
Interactive docs at http://localhost:8000/docs

### 3. Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # Fill in Supabase URL + anon key
npm run dev
```
App runs at http://localhost:3000

---

## Local Development (With Docker)

```bash
# At project root
cp backend/.env.example backend/.env   # Fill in secrets
docker-compose up --build
```
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## Deployment

### Backend — Railway
1. Connect the GitHub repo to Railway
2. Railway detects `backend/railway.toml` and builds using `backend/Dockerfile`
3. Set all environment variables in the Railway dashboard (same as `backend/.env`)
4. The Docker image includes LibreOffice + Noto fonts automatically

### Frontend — Vercel
1. Connect the GitHub repo to Vercel
2. Set root directory to `frontend`
3. Add environment variables in Vercel dashboard
4. Vercel auto-detects Next.js and deploys

### Updating `FRONTEND_URL` and `BACKEND_URL`
After your first deploy, update these in the backend environment variables to the actual Railway and Vercel URLs.

---

## Tech Stack Summary

| Layer | Tech | Version |
|---|---|---|
| Frontend | Next.js (App Router) | 14.x |
| Frontend language | TypeScript | 5.x |
| CSS | Tailwind CSS | 3.x |
| UI components | shadcn/ui | latest |
| Backend | FastAPI | 0.110+ |
| Backend language | Python | 3.11+ |
| Database | Supabase (PostgreSQL) | latest |
| Auth | Supabase Auth | included |
| AI | OpenAI GPT-4o | latest |
| PPTX generation | python-pptx | 0.6.23+ |
| PDF generation | LibreOffice (primary) + ReportLab (fallback) | — |
| Charts | matplotlib | 3.8+ |
| Email | Resend | latest |
| Payments | Razorpay | latest |
| Token encryption | cryptography (AES-256-GCM) | 42.x+ |
| Frontend hosting | Vercel | — |
| Backend hosting | Railway | — |
| File storage | Supabase Storage | — |

---

## Key Architecture Notes

### PDF Generation Strategy
1. **LibreOffice** (primary): `soffice --headless --convert-to pdf report.pptx`
   - Handles ALL scripts including Devanagari, CJK, Arabic
   - Produces the highest-quality PDF (identical to what PowerPoint would produce)
   - Tried at `/usr/bin/soffice`, `soffice`, `libreoffice`, `/usr/bin/libreoffice`

2. **ReportLab** (fallback): Used when LibreOffice is unavailable
   - Supports Latin + Extended Latin scripts (DejaVu Sans font)
   - Supports Devanagari/CJK/Arabic IF Noto fonts are installed (auto-detected via matplotlib)
   - For non-Latin languages without Noto fonts: returns `None` and frontend shows "PDF unavailable"

### OAuth Token Security
All OAuth tokens (Google, Meta) are encrypted with AES-256-GCM before storage in Supabase. The encryption key lives only in the `TOKEN_ENCRYPTION_KEY` environment variable — never in the database.

### Multi-tenant Data Isolation
Row-Level Security (RLS) is enabled on every Supabase table. Users can only read/write their own data. This is enforced at the database level, not just in application code.
