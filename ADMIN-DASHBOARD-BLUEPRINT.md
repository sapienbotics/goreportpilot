# GoReportPilot — Admin Dashboard Blueprint

**Created:** April 6, 2026
**Author:** Saurabh Singh / SapienBotics
**Purpose:** Complete specification for the internal admin dashboard — every screen, every feature, every GDPR requirement. Claude Code should read this document before building the admin dashboard.

---

## 1. OVERVIEW & GOALS

### Why We Need This
GoReportPilot is a live B2B SaaS product. As the founder/operator, I need full visibility into:
- Who's using the product, what plans they're on, and their engagement
- Subscription health: revenue, churn, failed payments
- Platform health: OAuth connection status, report generation errors
- GDPR compliance: ability to export or delete any user's data on request
- Debugging: when a user reports an issue, I need to see their account state without touching the database directly

### Design Principles
1. **Read-heavy, write-light** — 95% of admin usage is viewing data. Write actions are limited to user management (disable/delete) and GDPR operations.
2. **GDPR-first** — Every piece of user data shown must have a justification. Data export and deletion must be one-click operations.
3. **No sensitive data exposure** — NEVER show decrypted OAuth tokens, user passwords, or report narrative content (which is the user's intellectual property).
4. **Same auth system** — No separate login. Same Supabase auth, gated by `is_admin` boolean flag in profiles table.
5. **Minimal UI** — Clean data tables with filters. No fancy charts or dashboards for MVP. Function over form.

---

## 2. ACCESS CONTROL

### Database Change
```sql
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;

-- Set admin for the operator account
UPDATE profiles SET is_admin = true WHERE email = 'sapienbotics@gmail.com';
```

### Authentication Flow
1. User logs in normally via `/login`
2. Frontend fetches profile (which now includes `is_admin`)
3. If `is_admin = true` → redirect to `/dashboard/admin` instead of `/dashboard`
4. Admin sidebar replaces the regular sidebar
5. Non-admin users trying to access `/dashboard/admin/*` get redirected to `/dashboard`

### Backend Security
- ALL admin API endpoints live under `/api/admin/*`
- Every admin endpoint checks `is_admin` flag from the JWT/profile
- Admin endpoints use `supabase_admin` client (service role key) to bypass RLS
- All admin write actions (delete user, disable account) are logged with timestamp and admin user ID

### What Admin CAN See
- User profiles (email, name, plan, agency name, signup date, last login)
- Subscription status and payment history
- Client metadata (name, industry, platform connections — NOT client business data)
- Report metadata (count, dates, template used, status — NOT AI narrative content)
- Connection health (platform, status, expiry — NOT decrypted tokens)
- System health metrics

### What Admin CANNOT See
- Decrypted OAuth tokens (access_token, refresh_token)
- Report AI narrative content (executive summary, key wins, etc.)
- User passwords or password hashes
- Client goals_context or notes (user's private strategic data)
- Report user_edits (user's manual text modifications)
- Client contact_emails (user's client relationships)

---

## 3. ROUTE STRUCTURE

```
/dashboard/admin                → Overview (stats + activity)
/dashboard/admin/users          → User management table
/dashboard/admin/users/[id]     → User detail view
/dashboard/admin/subscriptions  → Subscription & revenue
/dashboard/admin/connections    → OAuth connection health
/dashboard/admin/reports        → Report generation overview
/dashboard/admin/system         → System health & logs
/dashboard/admin/gdpr           → GDPR compliance center
```

---

## 4. SCREEN-BY-SCREEN SPECIFICATION

### Screen 1: Overview (`/dashboard/admin`)

**Purpose:** At-a-glance platform health. The first thing the admin sees.

**Stats Cards (top row):**
| Card | Data Source | Query |
|------|-----------|-------|
| Total Users | profiles | `SELECT COUNT(*) FROM profiles` |
| Active Users (30d) | auth.users | `SELECT COUNT(*) FROM auth.users WHERE last_sign_in_at > NOW() - INTERVAL '30 days'` |
| Total Clients | clients | `SELECT COUNT(*) FROM clients WHERE is_active = true` |
| Reports This Month | reports | `SELECT COUNT(*) FROM reports WHERE created_at > date_trunc('month', NOW())` |
| Active Subscriptions | subscriptions | `SELECT COUNT(*) FROM subscriptions WHERE status = 'active'` |
| MRR (₹) | subscriptions + plans | Count of active subs × plan price |
| Failed Payments (30d) | payment_history | `SELECT COUNT(*) FROM payment_history WHERE status = 'failed' AND created_at > NOW() - INTERVAL '30 days'` |
| Trial Expiring (7d) | subscriptions | `SELECT COUNT(*) FROM subscriptions WHERE status = 'trialing' AND trial_ends_at < NOW() + INTERVAL '7 days'` |

**Recent Activity Feed (below cards):**
Last 20 events, each showing: timestamp, event type, user email, details.

Events to track:
- New user signup
- Report generated (user email + client name)
- Subscription created/upgraded/cancelled
- Payment captured/failed
- OAuth connection created/expired/errored
- User account deleted (GDPR)

**Implementation:** Create an `admin_activity_log` table or query across existing tables with UNION ordered by timestamp.

---

### Screen 2: Users Management (`/dashboard/admin/users`)

**Purpose:** Browse and manage all registered users.

**Table Columns:**
| Column | Source | Sortable | Filterable |
|--------|--------|----------|------------|
| Email | profiles.email | ✓ | Search |
| Name | profiles.name | ✓ | Search |
| Agency | profiles.agency_name | ✓ | - |
| Plan | subscriptions.plan | ✓ | Dropdown (trial/starter/pro/agency) |
| Status | subscriptions.status | ✓ | Dropdown (trialing/active/past_due/cancelled/expired) |
| Clients | COUNT(clients) | ✓ | - |
| Reports | COUNT(reports) | ✓ | - |
| Signed Up | profiles.created_at | ✓ | Date range |
| Last Login | auth.users.last_sign_in_at | ✓ | - |
| Actions | - | - | - |

**Actions column:**
- View (→ user detail page)
- Disable/Enable toggle
- Delete (with confirmation)

**Filters bar:** Plan dropdown, Status dropdown, Date range picker, Search box (email/name).

**Pagination:** 25 per page with page controls.

---

### Screen 3: User Detail (`/dashboard/admin/users/[id]`)

**Purpose:** Everything about one user, organized in tabs.

#### Tab 1: Profile
| Field | Value |
|-------|-------|
| Email | profiles.email |
| Name | profiles.name |
| Agency Name | profiles.agency_name |
| Agency Email | profiles.agency_email |
| Agency Website | profiles.agency_website |
| Brand Color | profiles.brand_color (show color swatch) |
| Agency Logo | profiles.agency_logo_url (show thumbnail or "None") |
| Timezone | profiles.timezone |
| Default AI Tone | profiles.default_ai_tone |
| Report Language | profiles.report_language |
| Signed Up | profiles.created_at |
| Last Login | auth.users.last_sign_in_at |
| Email Confirmed | auth.users.email_confirmed_at |
| Admin | profiles.is_admin |

#### Tab 2: Subscription & Payments
**Subscription Card:**
| Field | Value |
|-------|-------|
| Plan | subscriptions.plan |
| Billing Cycle | subscriptions.billing_cycle |
| Status | subscriptions.status (color-coded badge) |
| Trial Ends | subscriptions.trial_ends_at |
| Current Period | subscriptions.current_period_start → current_period_end |
| Razorpay Customer ID | subscriptions.razorpay_customer_id |
| Razorpay Subscription ID | subscriptions.razorpay_subscription_id |
| Last Payment | subscriptions.last_payment_at |
| Failed Count | subscriptions.payment_failed_count |
| Cancel at Period End | subscriptions.cancel_at_period_end |

**Payment History Table:**
| Date | Amount | Currency | Status | Razorpay Payment ID |
|------|--------|----------|--------|---------------------|
| (from payment_history table, sorted desc) |

#### Tab 3: Clients
Table of all clients belonging to this user:
| Client Name | Industry | Platforms Connected | Reports Generated | Language | Active |
|-------------|----------|--------------------|--------------------|----------|--------|
| (from clients + connections + reports counts) |

Click client name → expand inline to show:
- Connected platforms (ga4/meta/google_ads/search_console) with status
- Last report date
- Scheduled reports (if any)
- Logo (thumbnail)

**DO NOT show:** goals_context, notes, contact_emails, report_config internals

#### Tab 4: Connections
All OAuth connections for this user's clients:
| Client | Platform | Account Name | Status | Token Expires | Last Sync |
|--------|----------|-------------|--------|--------------|-----------|
| (from connections joined with clients) |

Color-code status: green=active, yellow=expiring_soon, red=expired/error/revoked

**DO NOT show:** access_token_encrypted, refresh_token_encrypted, account_id

#### Tab 5: Reports
| Title | Client | Period | Template | Status | AI Model | Created |
|-------|--------|--------|----------|--------|----------|---------|
| (from reports joined with clients) |

**DO NOT show:** ai_narrative, user_edits, sections content

#### Tab 6: GDPR Actions
Three prominent action buttons:

**1. Export User Data**
- Button: "Export All Data (JSON)"
- Generates a JSON file containing:
  - Profile (all non-sensitive fields)
  - Subscription record
  - Payment history
  - Client list (name, industry, website, logo_url, created_at — NOT goals_context, notes, contact_emails)
  - Connections metadata (platform, account_name, status, created_at — NOT encrypted tokens)
  - Reports metadata (title, period, template, status, created_at — NOT ai_narrative, user_edits, sections)
  - Shared report links (share_hash, created_at, is_active, view count)
  - Scheduled reports (frequency, template, auto_send)
- Downloads as `goreportpilot_export_{user_email}_{date}.json`

**2. Delete User Account**
- Button: "Permanently Delete Account" (red, requires confirmation)
- Confirmation dialog: Type the user's email to confirm
- What gets deleted (CASCADE):
  - auth.users entry (triggers CASCADE to profiles)
  - All clients (CASCADE to connections, reports, shared_reports, scheduled_reports)
  - All connections (encrypted tokens destroyed)
  - All reports (files on Railway are ephemeral anyway)
  - All shared_reports and report_views
  - All scheduled_reports
  - subscription record
  - payment_history records
  - Logos in Supabase Storage (`logos/{user_id}/` folder)
- Sends confirmation email to the user: "Your GoReportPilot account and all associated data have been permanently deleted."
- Logs the action in admin_activity_log

**3. Disable Account**
- Button: "Disable Account" (amber)
- Sets a `is_disabled` flag (new column) on profiles
- Disabled users see "Account suspended. Contact support@goreportpilot.com" on login
- Does NOT delete data (reversible action)
- Admin can re-enable anytime

---

### Screen 4: Subscriptions & Revenue (`/dashboard/admin/subscriptions`)

**Purpose:** Revenue visibility and subscription health.

**Summary Cards:**
| Card | Calculation |
|------|-------------|
| MRR | Sum of all active monthly + (annual/12) subscriptions |
| Active Subs | COUNT where status = 'active' |
| Trialing | COUNT where status = 'trialing' |
| Past Due | COUNT where status = 'past_due' |
| Cancelled (30d) | COUNT where status = 'cancelled' AND cancelled_at > 30d ago |
| Trial→Paid Rate | active / (active + expired from trial) |
| Total Revenue | SUM(payment_history.amount) where status = 'captured' |

**Plan Distribution:**
Simple count per plan: Trial: X | Starter: X | Pro: X | Agency: X

**Subscriptions Table:**
| User Email | Plan | Cycle | Status | Started | Trial Ends | Last Payment | Razorpay Sub ID |
|-----------|------|-------|--------|---------|------------|-------------|-----------------|
| (sortable, filterable by plan/status) |

**Failed Payments Table (separate section):**
| Date | User Email | Amount | Razorpay Payment ID | Failed Count |
|------|-----------|--------|---------------------|-------------|
| (from payment_history WHERE status = 'failed', last 30 days) |

---

### Screen 5: Connections Health (`/dashboard/admin/connections`)

**Purpose:** Proactively identify broken/expiring OAuth connections across all users.

**Summary Cards:**
| Card | Count |
|------|-------|
| Total Active | status = 'active' |
| Expiring Soon | status = 'expiring_soon' OR token_expires_at < 7 days |
| Expired | status = 'expired' |
| Errored | status = 'error' |
| Revoked | status = 'revoked' |

**Connections Table:**
| User Email | Client | Platform | Account Name | Status | Token Expires | Updated At |
|-----------|--------|----------|-------------|--------|--------------|-----------|
| (sorted by token_expires_at ASC — soonest expiring first) |

**Filters:** Platform dropdown (ga4/meta_ads/google_ads/search_console), Status dropdown.

**Color coding:** Active=green, Expiring Soon=yellow, Expired/Error/Revoked=red.

---

### Screen 6: Reports Overview (`/dashboard/admin/reports`)

**Purpose:** Monitor report generation volume and errors.

**Summary Cards:**
| Card | Query |
|------|-------|
| Reports Today | created_at > today |
| Reports This Week | created_at > 7d ago |
| Reports This Month | created_at > 30d ago |
| Reports All Time | total count |
| Failed Reports | status = 'failed' |
| Most Used Template | GROUP BY template, ORDER BY count DESC, LIMIT 1 |

**Reports by Template (counts):**
modern_clean: X | dark_executive: X | colorful_agency: X | bold_geometric: X | minimal_elegant: X | gradient_modern: X

**Reports by Language (counts):**
en: X | hi: X | es: X | (etc.)

**Recent Reports Table:**
| User Email | Client | Period | Template | Language | Status | AI Model | Created |
|-----------|--------|--------|----------|----------|--------|----------|---------|
| (last 50 reports, sortable) |

**Failed Reports (separate section):**
| User Email | Client | Period | Error | Created |
|-----------|--------|--------|-------|---------|
| (status = 'failed', for debugging) |

**DO NOT show:** ai_narrative content, user_edits, sections data

---

### Screen 7: System Health (`/dashboard/admin/system`)

**Purpose:** Quick health check of all external dependencies.

**Service Status Cards:**
| Service | Check | Display |
|---------|-------|---------|
| Backend | `GET /health` | Online/Offline + response time |
| Supabase | health endpoint check | Connected/Error |
| OpenAI | health endpoint check | Connected/Error + model |
| LibreOffice | health endpoint check | Available/Missing |
| Resend | API key configured check | Configured/Missing |
| Razorpay | API key configured check | Configured/Missing |

**Environment Info:**
| Field | Value |
|-------|-------|
| Frontend URL | NEXT_PUBLIC_APP_URL |
| Backend URL | Railway URL |
| Supabase Project | Project URL |
| Node/Python versions | From health endpoint |
| Last Deploy | Git commit hash + timestamp |

**Recent Errors (if we add error logging):**
Last 20 errors from report generation, email sending, OAuth token refresh, webhook processing.

---

### Screen 8: GDPR Compliance Center (`/dashboard/admin/gdpr`)

**Purpose:** Centralized GDPR management and compliance tracking.

#### Section A: Data Request Tracker
A simple table to manually track GDPR requests:

| Date | User Email | Request Type | Status | Completed At | Notes |
|------|-----------|-------------|--------|-------------|-------|
| (manually maintained by admin) |

Request types: Access (Art 15), Portability (Art 20), Erasure (Art 17), Rectification (Art 16), Restriction (Art 18)

**Add Request button:** Opens form to log a new request with user email, type, and notes.

**Implementation:** New table `gdpr_requests` with columns: id, user_email, request_type, status (pending/in_progress/completed/rejected), admin_notes, created_at, completed_at.

#### Section B: Inactive Users
Table of users who haven't logged in for 12+ months:

| Email | Last Login | Plan | Clients | Reports |
|-------|-----------|------|---------|---------|
| (candidates for data retention notification) |

**Action:** "Send Retention Notice" — sends email asking if they want to keep their account or have data deleted. (Phase 2 — for MVP, just show the list)

#### Section C: Consent Records
All users with their consent timestamps:

| Email | Signed Up (= consent date) | Email Confirmed | Privacy Policy Version |
|-------|---------------------------|-----------------|----------------------|
| (signup timestamp serves as consent record per your Terms/Privacy) |

#### Section D: Data Processing Summary
Static information card showing:
- What data we collect (per Privacy Policy)
- Where data is stored (Supabase, Railway, Supabase Storage)
- Third-party processors (OpenAI, Resend, Razorpay)
- Data retention policy (kept while account active, deleted within 30 days of account deletion)
- Legal basis for processing (contract performance under GDPR Art 6(1)(b))

---

## 5. DATABASE ADDITIONS

### New Tables

```sql
-- Admin activity log
CREATE TABLE IF NOT EXISTS admin_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID REFERENCES auth.users(id),
    action TEXT NOT NULL, -- 'delete_user', 'disable_user', 'enable_user', 'export_data', 'view_user'
    target_user_id UUID,
    target_user_email TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- No RLS on admin tables — only accessed via service role
ALTER TABLE admin_activity_log ENABLE ROW LEVEL SECURITY;
-- No policies = only service role can access

-- GDPR request tracker
CREATE TABLE IF NOT EXISTS gdpr_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email TEXT NOT NULL,
    request_type TEXT NOT NULL CHECK (request_type IN ('access', 'portability', 'erasure', 'rectification', 'restriction')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'rejected')),
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

ALTER TABLE gdpr_requests ENABLE ROW LEVEL SECURITY;
-- No policies = only service role can access

-- Add is_admin and is_disabled to profiles
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_disabled BOOLEAN DEFAULT false;
```

### Profile Column Additions
- `is_admin BOOLEAN DEFAULT false` — gates admin access
- `is_disabled BOOLEAN DEFAULT false` — admin can suspend accounts

---

## 6. BACKEND API SPECIFICATION

### All endpoints under `/api/admin/`

All require `is_admin = true` on the requesting user's profile. Return 403 if not admin.

```
# Overview
GET /api/admin/stats                    → Summary stats for overview cards
GET /api/admin/activity                 → Recent activity feed (last 20)

# Users
GET /api/admin/users                    → Paginated user list (with filters)
GET /api/admin/users/{id}               → Full user detail (profile + sub + clients + connections + reports)
POST /api/admin/users/{id}/disable      → Set is_disabled = true
POST /api/admin/users/{id}/enable       → Set is_disabled = false
POST /api/admin/users/{id}/export       → Generate and return data export JSON
DELETE /api/admin/users/{id}            → Permanent deletion (GDPR erasure)

# Subscriptions
GET /api/admin/subscriptions            → All subscriptions (with filters)
GET /api/admin/payments                 → All payments (with filters)
GET /api/admin/revenue                  → MRR, total revenue, plan distribution

# Connections
GET /api/admin/connections              → All connections (with filters)

# Reports
GET /api/admin/reports                  → Recent reports (with filters)
GET /api/admin/reports/stats            → Report generation stats

# System
GET /api/admin/system/health            → Health check of all services

# GDPR
GET /api/admin/gdpr/requests            → All GDPR requests
POST /api/admin/gdpr/requests           → Log new GDPR request
PATCH /api/admin/gdpr/requests/{id}     → Update request status
GET /api/admin/gdpr/inactive-users      → Users inactive 12+ months
```

### Backend Router Structure
Create `backend/routers/admin.py` — single file with all admin endpoints.

Uses `supabase_admin` (service role) client for all queries to bypass RLS.

Every mutating action (delete, disable, enable) creates an entry in `admin_activity_log`.

---

## 7. FRONTEND ARCHITECTURE

### Admin Layout
- Separate sidebar for admin pages (not the user dashboard sidebar)
- Sidebar links: Overview, Users, Subscriptions, Connections, Reports, System, GDPR
- Top bar shows: "Admin Dashboard" badge + "Switch to User View" link (goes to /dashboard)
- Same color scheme as the app but with an admin indicator (e.g., red accent bar)

### Components to Build
| Component | Purpose |
|-----------|---------|
| AdminLayout | Sidebar + content wrapper |
| AdminSidebar | Navigation links |
| StatsCard | Reusable metric card (label, value, optional trend) |
| DataTable | Reusable sortable/filterable/paginated table |
| UserDetailPanel | Tabbed user detail view |
| ConfirmDeleteDialog | Type-email-to-confirm deletion modal |
| GDPRRequestForm | Form to log GDPR requests |
| StatusBadge | Color-coded status indicator |

### Data Fetching
- All admin API calls go through `adminApi` object in `api.ts`
- Use SWR or simple useEffect + useState (match existing patterns in codebase)
- Pagination: server-side with `?page=1&limit=25` params
- Filters: query params `?plan=starter&status=active&search=john`

---

## 8. IMPLEMENTATION PRIORITY

### Phase 1 — Core (Build Now)
1. Database changes (is_admin, is_disabled, admin_activity_log, gdpr_requests)
2. Admin middleware (frontend redirect + backend auth check)
3. Overview page with stats
4. Users list + detail view
5. GDPR: Export + Delete user
6. Admin activity logging

### Phase 2 — Extended (Build Next)
7. Subscriptions & revenue page
8. Connections health page
9. Reports overview page
10. GDPR request tracker

### Phase 3 — Polish (Later)
11. System health page
12. Inactive users list
13. Failed payments alerts
14. Disable/enable account flow
15. Admin activity log viewer

---

## 9. SECURITY CHECKLIST

- [ ] `is_admin` checked server-side on EVERY admin endpoint (not just frontend)
- [ ] Admin endpoints use `supabase_admin` (service role), not user JWT
- [ ] Decrypted tokens NEVER returned in admin API responses
- [ ] Report narrative content NEVER returned in admin API responses
- [ ] Client goals_context and notes NEVER returned in admin API responses
- [ ] All admin write actions logged in admin_activity_log
- [ ] User deletion sends confirmation email
- [ ] User deletion removes Supabase Storage logos
- [ ] Delete confirmation requires typing the user's email
- [ ] Non-admin users get 403 on all /api/admin/* endpoints
- [ ] Non-admin users redirected away from /dashboard/admin/* routes
- [ ] Data export JSON excludes all sensitive fields listed in Section 2

---

## 10. KEY RULES FOR CLAUDE CODE

- Claude Code NEVER modifies .env or .env.local files
- Claude Code NEVER starts dev servers
- Database migration SQL must be output separately for manual execution in Supabase SQL Editor
- Run `cd frontend && npx tsc --noEmit` after frontend changes
- Systemic implementation — handle ALL edge cases, not targeted patches
- Admin endpoints MUST use service role client, not user client
- Follow existing code patterns in the codebase (Axios API client, component structure, etc.)
- The admin user email is `sapienbotics@gmail.com` — hardcode this ONLY in the migration SQL, nowhere else

---

*This document is the complete specification for the GoReportPilot Admin Dashboard. Claude Code should read this document before building any admin features. Every screen, every endpoint, every GDPR requirement is specified here.*
