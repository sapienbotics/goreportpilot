# ReportPilot Deployment Guide

## Prerequisites
- GitHub repo with the ReportPilot monorepo pushed
- Domain purchased (e.g., goreportpilot.com)
- Accounts created on: Vercel, Railway, Razorpay, Resend

---

## Step 1: Deploy Backend to Railway

1. Go to https://railway.app -> New Project -> Deploy from GitHub Repo
2. Select the reportpilot repository
3. Railway should auto-detect `backend/railway.toml` and use the Dockerfile
4. If it doesn't, manually set:
   - Root Directory: `/` (railway.toml points to backend/Dockerfile)
   - Builder: Dockerfile
5. Add environment variables in Railway dashboard (Settings -> Variables):

| Variable | Value |
|----------|-------|
| SUPABASE_URL | https://kbytzqviqzcvfdepjyby.supabase.co |
| SUPABASE_SERVICE_ROLE_KEY | (copy from Supabase dashboard -> Settings -> API) |
| GOOGLE_CLIENT_ID | (from Google Cloud Console) |
| GOOGLE_CLIENT_SECRET | (from Google Cloud Console) |
| META_APP_ID | (from Meta Developer Portal) |
| META_APP_SECRET | (from Meta Developer Portal) |
| OPENAI_API_KEY | (from OpenAI dashboard) |
| TOKEN_ENCRYPTION_KEY | (the existing key from local .env) |
| FRONTEND_URL | https://goreportpilot.com |
| BACKEND_URL | https://api.goreportpilot.com (or Railway's generated URL) |
| ENVIRONMENT | production |
| RAZORPAY_KEY_ID | (from Razorpay dashboard -- add later) |
| RAZORPAY_KEY_SECRET | (from Razorpay dashboard -- add later) |
| RAZORPAY_WEBHOOK_SECRET | (from Razorpay dashboard -- add later) |
| RESEND_API_KEY | (from Resend dashboard -- add later) |
| EMAIL_FROM_DOMAIN | goreportpilot.com |
| GOOGLE_ADS_DEVELOPER_TOKEN | (from Google Ads API Center -- add later) |
| GOOGLE_ADS_LOGIN_CUSTOMER_ID | 8152475096 |

6. Railway will build the Docker image and deploy. Check the /health endpoint.
7. Note down the Railway URL (e.g., `https://reportpilot-api-production.up.railway.app`)
8. Optional: Add custom domain `api.goreportpilot.com` in Railway settings -> Domains

---

## Step 2: Deploy Frontend to Vercel

1. Go to https://vercel.com -> New Project -> Import from GitHub
2. Select the reportpilot repository
3. Configure:
   - Framework Preset: Next.js
   - Root Directory: `frontend`
4. Add environment variables:

| Variable | Value |
|----------|-------|
| NEXT_PUBLIC_SUPABASE_URL | https://kbytzqviqzcvfdepjyby.supabase.co |
| NEXT_PUBLIC_SUPABASE_ANON_KEY | (from Supabase dashboard -> Settings -> API -> anon/public key) |
| NEXT_PUBLIC_API_URL | https://api.goreportpilot.com (or Railway URL from Step 1) |
| NEXT_PUBLIC_APP_URL | https://goreportpilot.com |

5. Deploy. Vercel will build and deploy the Next.js app.
6. Add custom domain `goreportpilot.com` in Vercel Settings -> Domains
7. Configure DNS at your domain registrar:
   - `goreportpilot.com` -> CNAME to `cname.vercel-dns.com`
   - `api.goreportpilot.com` -> CNAME to Railway's domain (if using custom domain on Railway)

---

## Step 3: Update OAuth Redirect URIs

### Google Cloud Console (console.cloud.google.com)
1. APIs & Services -> Credentials -> Edit your OAuth client
2. Under "Authorized redirect URIs", ADD:
   - `https://goreportpilot.com/api/auth/callback/google-analytics`
   - `https://goreportpilot.com/api/auth/callback/google-ads`
   - `https://goreportpilot.com/api/auth/callback/search-console`
3. Keep the localhost URIs for local development
4. Under "Authorized JavaScript origins", ADD:
   - `https://goreportpilot.com`

### Meta Developer Portal (developers.facebook.com)
1. Your App -> Facebook Login -> Settings
2. Under "Valid OAuth Redirect URIs", ADD:
   - `https://goreportpilot.com/api/auth/callback/meta-ads`
3. Keep the localhost URI for local development

---

## Step 4: Post-Deployment Verification

1. Visit `https://api.goreportpilot.com/health` -- should return healthy status with supabase connected
2. Visit `https://goreportpilot.com` -- landing page should load
3. Sign up with a new account -- verify Supabase auth works
4. Try connecting GA4 -- verify OAuth redirect goes to Google, comes back to production URL
5. Generate a test report -- verify PPTX and PDF download work

---

## Step 5: Submit OAuth for Production (Do After Step 4 Works)

### Google OAuth Verification
1. Google Cloud Console -> OAuth consent screen
2. Change publishing status from "Testing" to "In Production"
3. Google will request:
   - Privacy policy URL: https://goreportpilot.com/privacy
   - Terms of service URL: https://goreportpilot.com/terms
   - App logo
   - Explanation of how you use the `analytics.readonly` scope
4. Review takes 2-6 weeks. During this time, only test users can OAuth.

### Meta App Review
1. Meta Developer Portal -> Your App -> App Review
2. Request `ads_read` permission
3. Provide:
   - Screen recording demo showing how the integration works
   - Privacy policy URL
   - Description of how you use the data
4. Review takes 1-4 weeks.

---

## Step 6: Razorpay Setup (Can Do Anytime)

1. Create Razorpay account at https://razorpay.com
2. Get API keys from Dashboard -> Settings -> API Keys
3. Create 6 subscription plans in Razorpay Dashboard -> Subscriptions -> Plans:
   - Starter Monthly: INR 1,599/month
   - Starter Annual: INR 15,350/year
   - Pro Monthly: INR 3,299/month
   - Pro Annual: INR 31,670/year
   - Agency Monthly: INR 5,799/month
   - Agency Annual: INR 55,670/year
4. Note the Plan IDs and update backend config/plans if needed
5. Add API keys to Railway environment variables
6. Set up webhook: Razorpay Dashboard -> Webhooks -> Add:
   - URL: https://api.goreportpilot.com/api/webhooks/razorpay
   - Events: subscription.activated, subscription.charged, subscription.cancelled, payment.failed

---

## Step 7: Resend Email Setup (Can Do Anytime)

1. Create Resend account at https://resend.com
2. Add and verify domain `goreportpilot.com` (add DNS records as instructed by Resend)
3. Get API key from Resend dashboard
4. Add `RESEND_API_KEY` to Railway environment variables

---

## Ongoing: Making Changes After Deployment

1. Make changes locally, test with dev servers
2. `git add . && git commit -m "description" && git push`
3. Both Vercel and Railway auto-detect the push and redeploy
4. Vercel: ~30-60 seconds
5. Railway: ~2-5 minutes (Docker rebuild)
6. Both support instant rollback in their dashboards if something breaks
