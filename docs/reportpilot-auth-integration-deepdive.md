# ReportPilot — Authentication & Integration Deep Dive
## Complete OAuth, Token Management, App Verification & Security Blueprint
**Date:** 2026-03-17
**Version:** 1.0
**Companion to:** reportpilot-deep-dive.md + reportpilot-feature-design-blueprint.md

---

## TABLE OF CONTENTS

1. Authentication Architecture Overview
2. User Authentication (Supabase Auth)
3. Google OAuth — Complete Setup & Flow
4. Meta (Facebook) OAuth — Complete Setup & Flow
5. Google Ads API — Complete Setup & Flow
6. Token Storage & Encryption Strategy
7. Token Lifecycle Management (The Hardest Part)
8. App Verification & Review Process (Calendar Plan)
9. Multi-Account & Multi-Property Selection
10. Connection Health Monitoring System
11. Error Recovery & Reconnection Flows
12. Security Architecture
13. Testing Strategy (Before You Go Live)
14. Phase-by-Phase Implementation Plan
15. Common Pitfalls & How To Avoid Them

---

## 1. AUTHENTICATION ARCHITECTURE OVERVIEW

ReportPilot has TWO separate auth systems that work together:

### System A: User Authentication
"How does the ReportPilot user (the marketer) log in to OUR app?"

- Handled by **Supabase Auth**
- Email/password signup + Google SSO (optional)
- JWT-based sessions
- This is standard, simple, well-documented

### System B: Platform OAuth Connections
"How does ReportPilot connect to the marketer's Google Analytics / Meta Ads / Google Ads?"

- Handled by **OAuth 2.0 flows** with each platform individually
- Each platform has its own OAuth implementation with different rules
- Tokens are stored encrypted in our database, tied to specific clients
- This is the complex part — the focus of this document

### How They Relate

```
┌──────────────────────────────────────────────────────────┐
│  REPORTPILOT USER (the marketer)                         │
│  Logged in via Supabase Auth (email/password or Google)  │
│                                                          │
│  Has multiple CLIENTS:                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Client: Acme │  │ Client: Beta │  │ Client: Gamma│  │
│  │              │  │              │  │              │  │
│  │ Connections: │  │ Connections: │  │ Connections: │  │
│  │ ✓ GA4       │  │ ✓ GA4       │  │ ✓ GA4       │  │
│  │ ✓ Meta Ads  │  │ ✓ Meta Ads  │  │ ○ Meta Ads  │  │
│  │ ○ Google Ads│  │ ✓ Google Ads│  │ ○ Google Ads│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  Each ✓ connection = stored OAuth tokens for that        │
│  specific platform + account                             │
└──────────────────────────────────────────────────────────┘
```

**Key insight:** The marketer authenticates ONCE with Google (using their own Google account that has access to all their clients' GA4 properties). They don't authenticate separately per client. Instead, after OAuth, we let them SELECT which GA4 property to assign to which client.

Same for Meta — one OAuth login gives access to all ad accounts they manage. They then assign each ad account to the correct client in ReportPilot.

---

## 2. USER AUTHENTICATION (Supabase Auth)

This is the straightforward part. Your users log into ReportPilot itself.

### Implementation

**Option A: Email + Password (Primary)**
```javascript
// Signup
const { data, error } = await supabase.auth.signUp({
  email: 'marketer@agency.com',
  password: 'securepassword123'
})

// Login
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'marketer@agency.com',
  password: 'securepassword123'
})
```

**Option B: Google SSO (Convenience)**
```javascript
// Login with Google
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google'
})
```

**IMPORTANT:** This Google SSO login is for logging into ReportPilot itself. It is COMPLETELY SEPARATE from the Google Analytics OAuth connection. They use different scopes, different purposes, and different tokens. Don't confuse them.

### Session Management
- Supabase uses JWT tokens with 1-hour expiry + automatic refresh
- Store session in httpOnly cookie (not localStorage — more secure)
- On every page load, check `supabase.auth.getSession()`
- If expired, Supabase auto-refreshes using the refresh token

### Row-Level Security (RLS)
Supabase RLS ensures that User A can NEVER see User B's data, even if there's a bug in your code:

```sql
-- Users can only see their own clients
CREATE POLICY "Users see own clients" ON clients
  FOR SELECT USING (auth.uid() = user_id);

-- Users can only see connections for their own clients
CREATE POLICY "Users see own connections" ON connections
  FOR SELECT USING (
    client_id IN (SELECT id FROM clients WHERE user_id = auth.uid())
  );

-- Users can only see their own reports
CREATE POLICY "Users see own reports" ON reports
  FOR SELECT USING (auth.uid() = user_id);
```

This is your security foundation. Even if someone discovers another user's client_id, the database itself blocks access.

---

## 3. GOOGLE ANALYTICS 4 — COMPLETE OAuth SETUP & FLOW

### 3A. One-Time Setup (You Do This Once, Before Launch)

**Step 1: Create a Google Cloud Project**
- Go to: https://console.cloud.google.com
- Click "New Project" → Name it "ReportPilot" → Create
- This project is the container for all your Google API credentials
- Cost: FREE (Google Cloud projects are free; you only pay for services you use, and the Analytics API is free)

**Step 2: Enable the Google Analytics Data API**
- In your project, go to: APIs & Services → Library
- Search "Google Analytics Data API"
- Click → Enable
- This is the v1 API specifically for GA4 (not the old Universal Analytics API)

**Step 3: Configure the OAuth Consent Screen**
- Go to: APIs & Services → OAuth Consent Screen
- User Type: **External** (since your users aren't part of your Google Workspace)
- Fill in:
  - App name: "ReportPilot"
  - User support email: your email
  - App logo: upload ReportPilot logo (recommended, shows on consent popup)
  - App domain: https://reportpilot.co
  - Authorized domains: reportpilot.co
  - Developer contact: your email
  - Privacy policy URL: https://reportpilot.co/privacy (REQUIRED — create this page before submitting)
  - Terms of service URL: https://reportpilot.co/terms (REQUIRED)

**Step 4: Add Scopes**
- Click "Add or Remove Scopes"
- Add: `https://www.googleapis.com/auth/analytics.readonly`
- This is a **SENSITIVE scope** (not restricted, not basic — sensitive)
- Sensitive scopes require OAuth verification by Google (more on this in Section 8)

**Step 5: Create OAuth 2.0 Credentials**
- Go to: APIs & Services → Credentials
- Click "Create Credentials" → "OAuth client ID"
- Application type: **Web application**
- Name: "ReportPilot Web"
- Authorized redirect URIs: `https://reportpilot.co/api/auth/callback/google-analytics`
- Click Create → Download the JSON file (contains `client_id` and `client_secret`)
- **NEVER commit this file to Git. Store as environment variables.**

**Step 6: Add Test Users (For Development)**
- Back in OAuth Consent Screen → Under "Test users" → Add your email and any beta tester emails
- While in "Testing" publishing status, only these users can complete the OAuth flow
- You can have up to **100 test users** before needing verification
- This is enough for your entire beta phase

### 3B. The OAuth Flow (What Happens When User Clicks "Connect GA4")

**Complete flow, step by step:**

```
1. USER clicks "Connect Google Analytics" button in ReportPilot

2. YOUR FRONTEND generates the authorization URL:
   https://accounts.google.com/o/oauth2/v2/auth?
     client_id=YOUR_CLIENT_ID
     &redirect_uri=https://reportpilot.co/api/auth/callback/google-analytics
     &scope=https://www.googleapis.com/auth/analytics.readonly
     &response_type=code
     &access_type=offline        ← THIS IS CRITICAL — means "give me a refresh token"
     &prompt=consent              ← Forces consent screen every time — ensures refresh token
     &state=random_csrf_token     ← Security: prevents CSRF attacks

3. BROWSER opens a new window/popup with Google's consent screen:
   ┌─────────────────────────────────────────┐
   │  Google                                  │
   │                                          │
   │  ReportPilot wants to access your        │
   │  Google Account                          │
   │                                          │
   │  This will allow ReportPilot to:         │
   │  • View your Google Analytics data       │
   │                                          │
   │  [Cancel]              [Allow]           │
   └─────────────────────────────────────────┘

4. USER clicks "Allow"

5. GOOGLE redirects to your callback URL:
   https://reportpilot.co/api/auth/callback/google-analytics
     ?code=4/0AX4XfWh...long_code...
     &state=random_csrf_token

6. YOUR BACKEND receives this code and exchanges it for tokens:

   POST https://oauth2.googleapis.com/token
   Body:
     code=4/0AX4XfWh...
     client_id=YOUR_CLIENT_ID
     client_secret=YOUR_CLIENT_SECRET
     redirect_uri=https://reportpilot.co/api/auth/callback/google-analytics
     grant_type=authorization_code

7. GOOGLE responds with tokens:
   {
     "access_token": "ya29.a0AfH6SM...",       ← Use this to make API calls (expires in 1 hour)
     "refresh_token": "1//0eXx5....",           ← Use this to get new access tokens (lasts indefinitely)
     "expires_in": 3600,                         ← Seconds until access_token expires
     "token_type": "Bearer",
     "scope": "https://www.googleapis.com/auth/analytics.readonly"
   }

8. YOUR BACKEND:
   a. Validates the state parameter (CSRF check)
   b. Encrypts both tokens with AES-256-GCM
   c. Stores encrypted tokens in your database
   d. Calls GA4 API to list available properties for this user
   e. Returns the list of properties to the frontend

9. FRONTEND shows property selector:
   ┌─────────────────────────────────────────┐
   │  Select a GA4 Property                   │
   │                                          │
   │  ○ Acme Corp Website (Property: 12345)  │
   │  ○ Beta Inc Blog (Property: 67890)      │
   │  ○ Gamma LLC Store (Property: 11111)    │
   │                                          │
   │  [Connect Selected Property]             │
   └─────────────────────────────────────────┘

10. USER selects "Acme Corp Website" → YOUR APP stores:
    - connection.platform = "ga4"
    - connection.client_id = [current client being set up]
    - connection.account_id = "12345" (the GA4 property ID)
    - connection.account_name = "Acme Corp Website"
    - connection.access_token = [encrypted]
    - connection.refresh_token = [encrypted]
    - connection.status = "active"
```

### 3C. Python Backend Implementation

```python
# /api/auth/callback/google-analytics

from fastapi import APIRouter, Request, HTTPException
from google.oauth2.credentials import Credentials
from google.analytics.admin import AnalyticsAdminServiceClient
import httpx
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]

@router.get("/api/auth/callback/google-analytics")
async def google_analytics_callback(code: str, state: str, request: Request):
    # 1. Validate CSRF state token
    expected_state = request.session.get("oauth_state")
    if state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # 2. Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
    
    tokens = token_response.json()
    
    if "error" in tokens:
        raise HTTPException(status_code=400, detail=tokens["error_description"])
    
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")  # Only present on first auth or with prompt=consent
    
    if not refresh_token:
        raise HTTPException(
            status_code=400, 
            detail="No refresh token received. Please disconnect and reconnect."
        )
    
    # 3. List available GA4 properties
    creds = Credentials(token=access_token)
    admin_client = AnalyticsAdminServiceClient(credentials=creds)
    
    accounts = admin_client.list_account_summaries()
    properties = []
    for account in accounts:
        for prop in account.property_summaries:
            properties.append({
                "property_id": prop.property.split("/")[-1],
                "display_name": prop.display_name,
                "account_name": account.display_name
            })
    
    # 4. Encrypt and temporarily store tokens (user hasn't selected property yet)
    temp_token_id = store_temp_tokens(
        user_id=request.state.user_id,
        access_token=encrypt(access_token),
        refresh_token=encrypt(refresh_token),
        platform="ga4"
    )
    
    # 5. Return properties list to frontend
    return {
        "temp_token_id": temp_token_id,
        "properties": properties
    }


@router.post("/api/connections/ga4/finalize")
async def finalize_ga4_connection(
    temp_token_id: str, 
    property_id: str, 
    client_id: str,
    request: Request
):
    # User selected a property — create the permanent connection
    temp_tokens = get_temp_tokens(temp_token_id)
    
    connection = create_connection(
        client_id=client_id,
        platform="ga4",
        account_id=property_id,
        account_name=get_property_name(property_id, temp_tokens),
        access_token=temp_tokens.access_token,  # already encrypted
        refresh_token=temp_tokens.refresh_token,
        status="active"
    )
    
    # Delete temp tokens
    delete_temp_tokens(temp_token_id)
    
    # Trigger initial data pull
    await trigger_data_pull(connection.id)
    
    return {"connection_id": connection.id, "status": "active"}
```

### 3D. Pulling Data From GA4 (After Connection Is Established)

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.oauth2.credentials import Credentials

def pull_ga4_data(connection):
    """Pull analytics data for a connected GA4 property."""
    
    # Decrypt stored tokens
    access_token = decrypt(connection.access_token)
    refresh_token = decrypt(connection.refresh_token)
    
    # Create credentials with auto-refresh capability
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    
    client = BetaAnalyticsDataClient(credentials=creds)
    
    # Pull current period data
    current_response = client.run_report(request={
        "property": f"properties/{connection.account_id}",
        "date_ranges": [
            {"start_date": "2026-03-01", "end_date": "2026-03-31"}
        ],
        "metrics": [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "newUsers"},
            {"name": "screenPageViews"},
            {"name": "bounceRate"},
            {"name": "averageSessionDuration"},
            {"name": "conversions"},
            {"name": "eventCount"}
        ],
        "dimensions": [
            {"name": "date"}
        ]
    })
    
    # Pull traffic source breakdown
    source_response = client.run_report(request={
        "property": f"properties/{connection.account_id}",
        "date_ranges": [
            {"start_date": "2026-03-01", "end_date": "2026-03-31"}
        ],
        "metrics": [
            {"name": "sessions"},
            {"name": "conversions"}
        ],
        "dimensions": [
            {"name": "sessionDefaultChannelGroup"}
        ]
    })
    
    # Pull top landing pages
    pages_response = client.run_report(request={
        "property": f"properties/{connection.account_id}",
        "date_ranges": [
            {"start_date": "2026-03-01", "end_date": "2026-03-31"}
        ],
        "metrics": [
            {"name": "sessions"},
            {"name": "bounceRate"}
        ],
        "dimensions": [
            {"name": "landingPage"}
        ],
        "limit": 10,
        "order_bys": [
            {"metric": {"metric_name": "sessions"}, "desc": True}
        ]
    })
    
    # If credentials were refreshed, update stored token
    if creds.token != access_token:
        update_connection_token(connection.id, encrypt(creds.token))
    
    # Parse and return structured data
    return parse_ga4_response(current_response, source_response, pages_response)
```

**KEY POINT:** Notice `creds` is created with BOTH `token` (access token) and `refresh_token`. The Google Python SDK **automatically refreshes** the access token when it expires. You don't need to write refresh logic yourself — the SDK handles it. After the call, check if `creds.token` changed; if it did, update your stored access token.

---

## 4. META (FACEBOOK) ADS — COMPLETE OAuth SETUP & FLOW

Meta is more complex than Google. Here's the complete picture.

### 4A. One-Time Setup

**Step 1: Create a Meta Developer Account**
- Go to: https://developers.facebook.com
- Log in with your personal Facebook account (or create one)
- Register as a developer (accept terms, ~2 minutes)

**Step 2: Create a Business App**
- Click "My Apps" → "Create App"
- Choose: **"Other"** → then **"Business"** as app type
- App name: "ReportPilot"
- Contact email: your business email
- Link to a Business Manager account (create one at business.facebook.com if needed)

**Step 3: Add Marketing API Product**
- In your app dashboard → "Add Product"
- Find "Marketing API" → Click "Set Up"
- This enables the Ads Insights endpoints

**Step 4: Configure Basic Settings**
- Settings → Basic:
  - App Domains: reportpilot.co
  - Privacy Policy URL: https://reportpilot.co/privacy (REQUIRED)
  - Terms of Service URL: https://reportpilot.co/terms
  - App Icon: upload logo
- Settings → Advanced:
  - Note your App ID and App Secret (equivalent to Google's client_id and client_secret)

**Step 5: Configure Facebook Login Product**
- Add Product → "Facebook Login for Business" → Set Up
- Settings:
  - Valid OAuth Redirect URIs: `https://reportpilot.co/api/auth/callback/meta-ads`
  - Enforce HTTPS: Yes
  - Use Strict Mode for redirect URIs: Yes

**Step 6: Request Required Permissions**
For reading ad data (which is all we need), you need:
- `ads_read` — Read ad account data, insights, campaigns (REQUIRES APP REVIEW)
- `read_insights` — Read page and ad insights
- `business_management` — Access Business Manager assets

These permissions are NOT available by default. You must submit for App Review (Section 8).

### 4B. The OAuth Flow (What Happens When User Clicks "Connect Meta Ads")

```
1. USER clicks "Connect Meta Ads" button

2. YOUR FRONTEND generates the authorization URL:
   https://www.facebook.com/v19.0/dialog/oauth?
     client_id=YOUR_META_APP_ID
     &redirect_uri=https://reportpilot.co/api/auth/callback/meta-ads
     &scope=ads_read,read_insights,business_management
     &response_type=code
     &state=random_csrf_token

3. BROWSER opens Facebook consent screen:
   ┌─────────────────────────────────────────┐
   │  Facebook                                │
   │                                          │
   │  Log in to continue to ReportPilot       │
   │                                          │
   │  ReportPilot will receive:               │
   │  • Your public profile                   │
   │  • Access to read your ad accounts       │
   │                                          │
   │  [Cancel]              [Continue]        │
   └─────────────────────────────────────────┘

4. USER clicks "Continue" (and selects which ad accounts to share)

5. FACEBOOK redirects to your callback:
   https://reportpilot.co/api/auth/callback/meta-ads
     ?code=AQB_long_code...
     &state=random_csrf_token

6. YOUR BACKEND exchanges code for SHORT-LIVED token:

   GET https://graph.facebook.com/v19.0/oauth/access_token?
     client_id=YOUR_META_APP_ID
     &client_secret=YOUR_META_APP_SECRET
     &redirect_uri=https://reportpilot.co/api/auth/callback/meta-ads
     &code=AQB_long_code...

   Response:
   {
     "access_token": "EAAGx...",          ← SHORT-LIVED (expires in ~1 hour)
     "token_type": "bearer",
     "expires_in": 5183999
   }

7. YOUR BACKEND immediately exchanges for LONG-LIVED token:

   GET https://graph.facebook.com/v19.0/oauth/access_token?
     grant_type=fb_exchange_token
     &client_id=YOUR_META_APP_ID
     &client_secret=YOUR_META_APP_SECRET
     &fb_exchange_token=EAAGx...short_lived_token...

   Response:
   {
     "access_token": "EAAGx...different_long_token...",   ← LONG-LIVED (60 days)
     "token_type": "bearer",
     "expires_in": 5184000                                 ← ~60 days in seconds
   }

8. YOUR BACKEND lists available ad accounts:

   GET https://graph.facebook.com/v19.0/me/adaccounts?
     fields=id,name,account_status,currency
     &access_token=LONG_LIVED_TOKEN

   Response:
   {
     "data": [
       {"id": "act_123456", "name": "Acme Corp Ads", "currency": "USD"},
       {"id": "act_789012", "name": "Beta Inc Ads", "currency": "USD"},
       {"id": "act_345678", "name": "Gamma LLC Ads", "currency": "GBP"}
     ]
   }

9. FRONTEND shows ad account selector (same as GA4 property selector)

10. USER selects account → permanent connection stored (encrypted)
```

### 4C. Token Types — The Meta Token Maze (CRITICAL TO UNDERSTAND)

Meta has FOUR types of tokens. You need to understand all of them:

| Token Type | Lifetime | How to Get | Use Case | For ReportPilot? |
|---|---|---|---|---|
| **Short-lived User Token** | ~1-2 hours | OAuth code exchange | Testing only | NO — too short |
| **Long-lived User Token** | 60 days | Exchange short-lived via API | MVP — simplest approach | YES for MVP |
| **Page Token** | Same as user token that created it | From user token + page ID | Reading page insights | Maybe later |
| **System User Token** | Never expires | Created in Business Manager | Production automated access | YES for production |

### MVP Strategy: Long-Lived User Tokens (60 Days)

For the MVP, use long-lived user tokens. They're the simplest to implement:

1. OAuth flow returns short-lived token
2. Immediately exchange for long-lived token (60 days)
3. Store the long-lived token
4. Set up a cron job that checks token expiry daily
5. 7 days before expiry → email the user: "Your Meta Ads connection expires soon. [Click to reconnect]"
6. User clicks → goes through OAuth flow again → new 60-day token

**Why not start with System User tokens?**
System User tokens require the user to go into their Business Manager, create a System User, assign it to their ad accounts, and generate a token manually. This is a TERRIBLE user experience for a new product. Long-lived tokens with a reconnection reminder are much smoother for beta/early users.

### Production Strategy: System User Tokens (Phase 2)

Once you have paying users who trust the product, add a "Permanent Connection" option:

1. Guide the user through creating a System User in their Business Manager
2. They assign the System User to their ad accounts
3. They generate a token for the System User and paste it into ReportPilot
4. This token NEVER expires
5. No more reconnection reminders

Build a step-by-step wizard with screenshots to guide them through this process.

### 4D. Pulling Data From Meta Ads

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

def pull_meta_ads_data(connection):
    """Pull ad performance data for a connected Meta ad account."""
    
    access_token = decrypt(connection.access_token)
    
    # Initialize the Meta API
    FacebookAdsApi.init(access_token=access_token)
    
    account = AdAccount(connection.account_id)  # e.g., "act_123456"
    
    # Pull account-level insights (summary)
    account_insights = account.get_insights(params={
        'time_range': {
            'since': '2026-03-01',
            'until': '2026-03-31'
        },
        'fields': [
            'spend',
            'impressions',
            'clicks',
            'ctr',
            'cpc',
            'cpm',
            'actions',                    # Includes purchases, leads, etc.
            'cost_per_action_type',
            'action_values',              # Revenue/value per action
            'purchase_roas',              # Return on ad spend
        ],
        'time_increment': 1  # Daily breakdown
    })
    
    # Pull campaign-level data (top campaigns)
    campaigns = account.get_insights(params={
        'time_range': {
            'since': '2026-03-01',
            'until': '2026-03-31'
        },
        'fields': [
            'campaign_name',
            'spend',
            'impressions',
            'clicks',
            'actions',
            'cost_per_action_type',
            'purchase_roas',
        ],
        'level': 'campaign',
        'sort': ['spend_descending'],
        'limit': 10
    })
    
    return parse_meta_response(account_insights, campaigns)
```

### 4E. Meta API Versioning — IMPORTANT

Meta updates their API approximately every quarter. Each version is supported for at least 2 years.

**Your strategy:**
- Pin your code to a specific version (e.g., `v19.0`)
- Check Meta's changelog monthly: https://developers.facebook.com/docs/graph-api/changelog
- When your version approaches end-of-life, update and test
- Currently (March 2026), Meta removed 7-day and 28-day view-through attribution windows — this is already factored in

In your API URLs, always specify the version:
```
https://graph.facebook.com/v19.0/...
```
Never use unversioned URLs (they default to the oldest supported version).

---

## 5. GOOGLE ADS — COMPLETE SETUP & FLOW

### 5A. One-Time Setup

Google Ads uses the same Google Cloud Project as GA4, but needs an additional credential:

**Step 1: Enable Google Ads API**
- Same Google Cloud Project → APIs & Services → Library
- Search "Google Ads API" → Enable

**Step 2: Apply for a Google Ads API Developer Token**
- Go to: https://ads.google.com → Tools & Settings → API Center
- You need a Google Ads Manager account (MCC — My Client Center) to apply
- If you don't have one, create a free Manager account at https://ads.google.com/home/tools/manager-accounts/
- Apply for Developer Token → Start with "Test Account" access (no approval needed)
- Later, apply for "Basic Access" for production (approval takes a few days — auto-approved for read-only)

**Step 3: OAuth is the same as GA4**
- Same OAuth client credentials (client_id, client_secret)
- Same flow, but add the Google Ads scope:
  - `https://www.googleapis.com/auth/adwords` (gives read access to Google Ads)
- In practice, you can request both GA4 and Google Ads scopes in a SINGLE OAuth flow

### 5B. Combined Google OAuth (GA4 + Google Ads in One Click)

Instead of making the user authenticate twice, request both scopes together:

```
scope=https://www.googleapis.com/auth/analytics.readonly
      https://www.googleapis.com/auth/adwords
```

One popup, one "Allow" click, and you get tokens that work for BOTH GA4 and Google Ads. Then in the property/account selection screen, show both GA4 properties and Google Ads accounts.

This is a much better UX than two separate connection buttons for Google products.

### 5C. The Developer Token Gotcha

Every Google Ads API request must include a `developer-token` header, in addition to the OAuth token. This is unique to Google Ads (GA4 doesn't need it).

```python
from google.ads.googleads.client import GoogleAdsClient

# Configuration
credentials = {
    "developer_token": "YOUR_DEV_TOKEN",
    "client_id": GOOGLE_CLIENT_ID,
    "client_secret": GOOGLE_CLIENT_SECRET,
    "refresh_token": stored_refresh_token,
    "login_customer_id": "1234567890"  # MCC account ID
}

client = GoogleAdsClient.load_from_dict(credentials)

# Pull campaign performance
ga_service = client.get_service("GoogleAdsService")
query = """
    SELECT
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.cost_per_conversion
    FROM campaign
    WHERE segments.date BETWEEN '2026-03-01' AND '2026-03-31'
    ORDER BY metrics.cost_micros DESC
    LIMIT 10
"""
response = ga_service.search(customer_id="1234567890", query=query)
```

---

## 6. TOKEN STORAGE & ENCRYPTION STRATEGY

Tokens are the keys to your users' data. They MUST be encrypted.

### Encryption Approach: Application-Level Encryption (AES-256-GCM)

**Why not just rely on Supabase's at-rest encryption?**
Supabase encrypts the entire database at rest, but if someone gets access to your Supabase dashboard or a database dump, they can read all tokens in plaintext. Application-level encryption means tokens are encrypted BEFORE they enter the database, and only your backend can decrypt them.

```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

# Generate a 256-bit encryption key (store in environment variables, NEVER in code)
# Run once: AESGCM.generate_key(bit_length=256)
ENCRYPTION_KEY = os.environ["TOKEN_ENCRYPTION_KEY"]  # 32 bytes, base64 encoded

def encrypt_token(plaintext: str) -> str:
    """Encrypt a token using AES-256-GCM."""
    key = base64.b64decode(ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce (unique per encryption)
    
    ciphertext = aesgcm.encrypt(
        nonce, 
        plaintext.encode('utf-8'), 
        None  # No additional authenticated data
    )
    
    # Store nonce + ciphertext together (both needed for decryption)
    return base64.b64encode(nonce + ciphertext).decode('utf-8')

def decrypt_token(encrypted: str) -> str:
    """Decrypt a token using AES-256-GCM."""
    key = base64.b64decode(ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')
```

### Database Schema for Token Storage

```sql
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- 'ga4', 'meta_ads', 'google_ads'
    account_id TEXT NOT NULL,  -- Platform-specific ID
    account_name TEXT,
    
    -- Encrypted tokens (application-level AES-256-GCM)
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,  -- Nullable (Meta System User tokens don't have refresh)
    
    -- Token metadata (NOT encrypted — needed for lifecycle management)
    token_expires_at TIMESTAMPTZ,  -- When the access token expires
    token_type TEXT DEFAULT 'user',  -- 'user', 'long_lived', 'system_user'
    
    -- Connection health
    status TEXT DEFAULT 'active',  -- 'active', 'expiring_soon', 'expired', 'error', 'revoked'
    last_successful_pull TIMESTAMPTZ,
    last_error_message TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for quick lookups
CREATE INDEX idx_connections_client ON connections(client_id);
CREATE INDEX idx_connections_status ON connections(status);
CREATE INDEX idx_connections_expiry ON connections(token_expires_at) WHERE status = 'active';
```

### Key Design Rules

1. **NEVER log tokens** — not in application logs, not in error logs, not in debug output
2. **NEVER return tokens to the frontend** — the frontend only knows "connected" or "not connected"
3. **NEVER store the encryption key in the database** — it lives in environment variables only
4. **Rotate encryption key periodically** — build a key rotation mechanism that re-encrypts all tokens with a new key (Phase 2)
5. **Delete tokens on disconnection** — when a user disconnects an account, delete the encrypted tokens immediately (not soft-delete)

---

## 7. TOKEN LIFECYCLE MANAGEMENT (The Hardest Part)

This is where most reporting tools struggle. Here's the production-grade approach:

### Daily Health Check Job (Runs at 2:00 AM UTC)

```python
async def daily_token_health_check():
    """Check all active connections for token health."""
    
    connections = get_all_active_connections()
    
    for conn in connections:
        try:
            if conn.platform == "ga4" or conn.platform == "google_ads":
                await check_google_token(conn)
            elif conn.platform == "meta_ads":
                await check_meta_token(conn)
        except Exception as e:
            log_error(f"Token check failed for connection {conn.id}: {e}")


async def check_google_token(conn):
    """Google tokens: refresh token lasts forever, access token auto-refreshes."""
    
    # Try to use the token to make a simple API call
    try:
        creds = build_google_credentials(conn)
        # Simple test: list account summaries (cheap API call)
        test_api_call(creds, conn.platform)
        
        # Success — update last successful pull timestamp
        update_connection(conn.id, status="active", last_successful_pull=now())
        
    except google.auth.exceptions.RefreshError:
        # Refresh token has been revoked by user
        update_connection(conn.id, status="revoked", 
                         last_error_message="Google access has been revoked. Please reconnect.")
        notify_user(conn, "google_revoked")
        
    except Exception as e:
        # Some other error — might be transient
        conn.consecutive_failures += 1
        if conn.consecutive_failures >= 3:
            update_connection(conn.id, status="error",
                             last_error_message=str(e))
            notify_user(conn, "connection_error")
        else:
            update_connection(conn.id, consecutive_failures=conn.consecutive_failures)


async def check_meta_token(conn):
    """Meta tokens: long-lived tokens expire after 60 days."""
    
    # Check if token is expiring within 7 days
    if conn.token_expires_at and conn.token_expires_at < now() + timedelta(days=7):
        update_connection(conn.id, status="expiring_soon")
        notify_user(conn, "meta_expiring_soon")
        return
    
    # Check if token has already expired
    if conn.token_expires_at and conn.token_expires_at < now():
        update_connection(conn.id, status="expired",
                         last_error_message="Meta Ads token has expired. Please reconnect.")
        notify_user(conn, "meta_expired")
        return
    
    # Token looks valid — try a test API call
    try:
        test_meta_api_call(conn)
        update_connection(conn.id, status="active", last_successful_pull=now())
    except FacebookRequestError as e:
        if e.api_error_code() == 190:  # Invalid/expired token
            update_connection(conn.id, status="expired",
                             last_error_message="Meta Ads token is no longer valid.")
            notify_user(conn, "meta_expired")
        else:
            conn.consecutive_failures += 1
            if conn.consecutive_failures >= 3:
                update_connection(conn.id, status="error",
                                 last_error_message=str(e))
                notify_user(conn, "connection_error")
```

### User Notification Logic

| Connection Status | User Sees | Email Sent? | Report Impact |
|---|---|---|---|
| `active` | Green checkmark "✓ Connected" | No | Reports generate normally |
| `expiring_soon` | Yellow badge "⚠ Expires in X days" + "[Reconnect]" button | Yes — "Your Meta Ads connection for [Client] expires on [date]. Click to reconnect." | Reports still generate but warning shown on report |
| `expired` | Red badge "✗ Expired" + "[Reconnect]" button | Yes — "Your Meta Ads connection for [Client] has expired. Reports can't include Meta data until you reconnect." | Reports generate WITHOUT this data source. AI narrative notes: "Meta Ads data unavailable — connection expired." |
| `error` | Red badge "✗ Error" + "[Reconnect]" button + error details | Yes (after 3 consecutive failures) | Same as expired — reports skip this source |
| `revoked` | Red badge "✗ Access Revoked" + "[Reconnect]" button | Yes — "Your Google Analytics access was revoked. This usually means the account permissions changed." | Reports skip this source |

---

## 8. APP VERIFICATION & REVIEW PROCESS (Calendar Plan)

### Google OAuth Verification

**Why it's needed:** Your app requests `analytics.readonly` (a "sensitive" scope). Google requires verification for sensitive scopes before you can let the general public use your app.

**What Google checks:**
1. Your app has a real website (not just a domain — actual content)
2. Privacy policy is accessible and mentions Google data usage
3. Terms of service exist
4. Your app only requests scopes it actually uses
5. Your app shows what it does with the data

**Timeline:**
- Submit → initial review: 1-2 weeks
- If issues → fix and resubmit: additional 1-2 weeks
- Total realistic timeline: **2-4 weeks**

**Before submitting, you need:**
- [ ] Landing page live at reportpilot.co (even if basic)
- [ ] Privacy Policy page (MUST mention Google Analytics data, how you store it, that you don't sell it)
- [ ] Terms of Service page
- [ ] Working OAuth flow (they'll test it)
- [ ] A video recording showing the OAuth flow and what your app does with the data (optional but speeds up review)
- [ ] App homepage that explains what ReportPilot does

**During review, you can still develop with 100 test users.** Add your own email + beta testers. This is enough for the entire MVP build + beta phase.

### Meta App Review

**Why it's needed:** `ads_read` is a special permission that requires Meta to verify your app is legitimate.

**What Meta checks:**
1. Your app has a legitimate business purpose
2. You explain why you need ads_read access
3. You show a screencast of your app using the permission
4. Your privacy policy mentions Facebook/Meta data
5. Your app complies with Meta Platform Terms

**Timeline:**
- Submit → review: 1-3 weeks (varies greatly)
- If rejected → fix and resubmit: additional 1-2 weeks
- Total realistic timeline: **2-5 weeks**

**What you submit:**
- Detailed description of your app and how it uses ads_read
- A screencast video (1-3 minutes) showing:
  - User logs into ReportPilot
  - Clicks "Connect Meta Ads"
  - OAuth popup appears
  - After connecting, the app shows ad performance data
  - Data is used to generate a client report
- Your privacy policy URL
- App verification details (business registration, etc.)

**Meta-specific gotcha:** Your app must be in "Live" mode (not "Development") before you can use approved permissions with non-team members. But you can only go Live after the review passes. So:
1. Build everything in Development mode (works with your own accounts + app admins)
2. Record the screencast
3. Submit for review
4. Continue building while waiting
5. Once approved, switch to Live mode

### Combined Calendar Plan

```
DAY 1-3:   Start building MVP. Create Google Cloud Project. Set up OAuth.
            Add yourself as test user. Test with your own GA4/Meta accounts.

DAY 7:     Landing page live (basic). Privacy policy + Terms of Service pages live.

DAY 10:    Submit Google OAuth Verification. 
            (Continue building — 100 test users available)

DAY 14:    Record Meta App Review screencast (show working OAuth + data pull).
            Submit Meta App Review.

DAY 14-28: Continue building MVP. Test with 5-10 beta users (added as test users).

DAY 21-35: Google verification approved (hopefully). 
            Open GA4 connections to all users.

DAY 28-42: Meta review approved (hopefully).
            Open Meta Ads connections to all users.

DAY 30:    MVP launch — open beta.
```

**KEY INSIGHT:** Start verification submissions AS EARLY AS POSSIBLE. Don't wait until the product is "done." Submit on Day 10-14 while you're still building. The review runs in parallel with your development.

---

## 9. MULTI-ACCOUNT & MULTI-PROPERTY SELECTION

### The Real-World Scenario

A freelancer named Priya manages 8 clients. She has:
- ONE personal Google account (priya@gmail.com) that has been added as a "Viewer" to all her clients' GA4 properties
- ONE Facebook Business Manager that contains all her clients' ad accounts
- ONE Google Ads Manager account (MCC) that manages all her clients' Google Ads accounts

When she connects to ReportPilot:
- She authenticates with Google ONCE → sees ALL 8 GA4 properties
- She authenticates with Meta ONCE → sees ALL 8 ad accounts
- She then ASSIGNS each property/account to the correct client

### The Assignment Flow

```
STEP 1: Priya clicks "Connect Google Analytics" (one time)
         → Authenticates with Google → tokens stored

STEP 2: She goes to Client "Acme Corp" → Connections tab
         → Clicks "Link GA4 Property"
         → Dropdown shows all properties her Google account has access to:
           - Acme Corp Website
           - Beta Inc Blog
           - Gamma LLC Store
           - ... etc
         → Selects "Acme Corp Website" → Linked

STEP 3: She goes to Client "Beta Inc" → Connections tab
         → Clicks "Link GA4 Property"  
         → Same dropdown (she doesn't need to re-authenticate)
         → Selects "Beta Inc Blog" → Linked

STEP 4: Repeat for each client
```

### Implementation: "Platform Accounts" vs "Client Connections"

```
PLATFORM_ACCOUNTS (one per OAuth authentication)
├── id
├── user_id (the ReportPilot user)
├── platform ("google" or "meta")
├── access_token_encrypted
├── refresh_token_encrypted
├── token_expires_at
├── authenticated_email ("priya@gmail.com")
├── status
└── created_at

CLIENT_CONNECTIONS (one per client per platform per property)
├── id
├── client_id
├── platform_account_id (FK → platform_accounts)
├── platform_specific_id ("properties/12345" or "act_123456")
├── platform_specific_name ("Acme Corp Website")
├── status
└── created_at
```

**This separation means:**
- One OAuth flow → one platform_account record
- Multiple clients can use the SAME platform_account (same tokens, different properties)
- If the token expires, you fix it in ONE place, and all client connections using it are restored
- If the user has multiple Google accounts (one for some clients, another for others), they can add multiple platform_accounts

---

## 10. CONNECTION HEALTH MONITORING SYSTEM

### Dashboard Connection Status Widget

Every user sees this at the top of their dashboard:

```
CONNECTION HEALTH
┌────────────────────────────────────────────┐
│ ✅ Google (8 clients)     All healthy      │
│ ⚠️ Meta Ads (7 clients)   1 expiring soon │
│ ❌ Google Ads (3 clients)  1 error         │
└────────────────────────────────────────────┘
```

Clicking any row shows details:

```
META ADS CONNECTIONS
┌─────────────┬──────────────────┬────────────┬──────────┐
│ Client      │ Ad Account       │ Status     │ Action   │
├─────────────┼──────────────────┼────────────┼──────────┤
│ Acme Corp   │ Acme Corp Ads    │ ✅ Active  │          │
│ Beta Inc    │ Beta Ads         │ ✅ Active  │          │
│ Gamma LLC   │ Gamma Ads        │ ⚠️ Exp 7d │[Reconnect]│
│ Delta Co    │ Delta Ads        │ ✅ Active  │          │
└─────────────┴──────────────────┴────────────┴──────────┘
```

### Automated Health Checks Schedule

| Check | Frequency | What It Does |
|---|---|---|
| Token expiry check | Every 6 hours | Compares `token_expires_at` against current time for all Meta connections |
| API validity check | Daily (2 AM UTC) | Makes a lightweight API call per platform_account to verify tokens still work |
| Rate limit monitoring | Per API call | Logs rate limit headers from API responses. Alert if approaching limits. |
| Data freshness check | Daily (after data pull) | Checks if pulled data is complete. Flags if a property returns zero sessions (possible tracking issue vs real zero). |

---

## 11. ERROR RECOVERY & RECONNECTION FLOWS

### Reconnection Flow (When Token Expires or Is Revoked)

```
1. User sees alert: "⚠️ Meta Ads connection for Acme Corp expired. [Reconnect]"
2. User clicks [Reconnect]
3. Same OAuth popup as initial connection
4. User re-authenticates with Meta
5. New long-lived token obtained
6. Backend updates the platform_account with new tokens
7. ALL client connections using this platform_account are restored automatically
8. Status changes from "expired" to "active" across all affected clients
9. User sees: "✅ Reconnected. 3 client connections restored."
```

**Key UX detail:** One reconnection fixes ALL clients using that same platform account. The user doesn't need to reconnect per-client.

### What Happens to Scheduled Reports When Connections Break

| Scenario | Report Behavior |
|---|---|
| GA4 connected + Meta expired | Report generates with GA4 data. Meta section shows: "Meta Ads data unavailable — connection expired. [Reconnect to include Meta data]" |
| All connections expired | Report cannot generate. User notified: "Cannot generate report for Acme Corp — all data source connections are expired." |
| Data pull returns zero | Report generates with a note: "Google Analytics returned zero sessions for this period. This may indicate a tracking code issue or a genuinely quiet period." |
| API error during pull | Retry 3 times with exponential backoff. If all fail, generate report with cached data from last successful pull + note: "Data is from [date of last pull]. Current data temporarily unavailable." |

---

## 12. SECURITY ARCHITECTURE

### Threat Model & Mitigations

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Database breach exposes tokens | Low | CRITICAL | Application-level AES-256-GCM encryption. Even with DB dump, tokens are unreadable without the encryption key. |
| Encryption key compromised | Very Low | CRITICAL | Key stored in environment variables (Railway/Vercel secrets). Not in code, not in DB. Key rotation capability built-in. |
| CSRF attack during OAuth | Medium | HIGH | State parameter validation on every callback. Reject requests with mismatched state. |
| Token interception in transit | Low | HIGH | All traffic over HTTPS (TLS 1.3). Tokens never sent to frontend. |
| Unauthorized data access between users | Low | HIGH | Supabase Row-Level Security. Database-level enforcement, not just application-level. |
| OAuth redirect hijacking | Low | HIGH | Strict redirect URI validation. Only exact URI matches accepted. No wildcard redirects. |
| Stored XSS accessing tokens | Low | MEDIUM | Tokens never exposed to frontend JavaScript. httpOnly cookies for session. |
| Brute force on user accounts | Medium | MEDIUM | Rate limiting on login (5 attempts/minute). Supabase built-in protection. |

### Security Checklist (Before Launch)

- [ ] All OAuth tokens encrypted with AES-256-GCM before database storage
- [ ] Encryption key stored as environment variable, NOT in codebase
- [ ] State parameter validated on every OAuth callback
- [ ] Redirect URIs are exact matches (no wildcards)
- [ ] HTTPS enforced everywhere (HSTS headers set)
- [ ] Supabase RLS policies active on ALL tables containing user data
- [ ] No tokens logged in application logs
- [ ] No tokens returned in API responses to frontend
- [ ] Rate limiting on login endpoint
- [ ] Rate limiting on report generation endpoint
- [ ] CORS configured to allow only reportpilot.co origin
- [ ] Environment variables used for ALL secrets (client_id, client_secret, encryption key)
- [ ] Privacy policy mentions Google and Meta data usage
- [ ] Data deletion endpoint: user can delete all their data + tokens on account cancellation

---

## 13. TESTING STRATEGY (Before You Go Live)

### Phase 1: Your Own Accounts (Day 1-7)

- Create a test GA4 property on a real website (even a simple one-page site with Google Analytics tag)
- Create a test Meta Ads account with a small ($5/day) test campaign
- Run the full flow: connect → pull data → generate AI report → download PPT
- Verify numbers match what you see in GA4/Meta Ads dashboards

### Phase 2: Beta Testers' Accounts (Day 8-21)

- Add 5-10 beta testers as Google OAuth test users
- Add them as app testers in Meta Developer Dashboard
- They connect THEIR real accounts with THEIR real data
- You verify the flow works with different account structures (single vs multiple properties, different currencies, etc.)

### Phase 3: Edge Case Testing

| Test Case | What You're Testing |
|---|---|
| User has 0 GA4 properties | Does the app show a helpful message instead of crashing? |
| User has 50+ GA4 properties | Does the property selector handle long lists? (Search/filter needed) |
| Meta token expires mid-report-generation | Does the report gracefully skip Meta data with a note? |
| User revokes Google access externally | Does the next health check catch it and notify the user? |
| User authenticates with Google, then disconnects internet | Does the callback handle the timeout? |
| Two clients share the same GA4 property | Does the system handle this correctly? (It should — same tokens, different report configs) |
| API returns rate limit error (429) | Does exponential backoff work? Does the report queue properly? |
| Report generation takes >60 seconds | Does the user see a loading state? Does it move to background? |
| User's Google account has both GA4 and Universal Analytics | Does the property selector only show GA4 properties? |

---

## 14. PHASE-BY-PHASE IMPLEMENTATION PLAN

### Week 1: Foundation

| Day | Task | Details |
|---|---|---|
| 1 | Project setup | Next.js frontend + FastAPI backend + Supabase project. Environment variables configured. |
| 2 | Supabase Auth | Email/password signup + login. Session management. RLS policies on all tables. |
| 3 | Database schema | Create all tables (users, clients, platform_accounts, connections, data_snapshots, reports). |
| 4 | Google Cloud setup | Create project, enable GA4 API, create OAuth credentials, configure consent screen. |
| 5 | GA4 OAuth flow | Build the complete flow: button → popup → callback → token exchange → property list → store. |
| 6 | GA4 data pull | Build the data pull function. Test with your own GA4 property. Verify numbers match. |
| 7 | Token encryption | Implement AES-256-GCM encrypt/decrypt. Store encrypted tokens. Test decryption works. |

### Week 2: Meta + Data Pipeline

| Day | Task | Details |
|---|---|---|
| 8 | Meta Developer setup | Create app, add Marketing API, configure Facebook Login. |
| 9 | Meta OAuth flow | Build complete flow: button → popup → callback → short→long token exchange → account list → store. |
| 10 | Meta data pull | Build data pull function. Test with your own (even small) ad account. |
| 11 | Submit verifications | Submit Google OAuth verification + Meta App Review. Record screencasts. |
| 12 | Client management UI | Build client list, client detail page, connection management. |
| 13 | Property/account assignment | Build the "Link GA4 Property" / "Link Meta Ad Account" dropdown flows. |
| 14 | Background data pull job | Build the scheduled job that pulls data for all connected clients daily. |

### Week 3: AI + Reports

| Day | Task | Details |
|---|---|---|
| 15-16 | AI narrative engine | Build the prompt system, GPT-4o integration, tone presets, number validation. |
| 17-18 | Report generation | PDF (ReportLab) + PowerPoint (python-pptx) generation with data + AI narrative + charts. |
| 19 | Report editor UI | Build the report preview + inline editing + section toggle interface. |
| 20-21 | Token health check | Build the daily health check job. Build notification system for expiring/broken connections. |

### Week 4: Polish + Launch

| Day | Task | Details |
|---|---|---|
| 22-23 | Report delivery | Email sending (Resend). Shareable links. Scheduled delivery. |
| 24-25 | White-label + branding | Logo upload, color picker, branded email sender. |
| 26-27 | Landing page + Stripe | Marketing page, pricing page, Stripe Checkout integration. |
| 28 | Testing | Full end-to-end test. Fix bugs. Test with 2-3 beta testers. |
| 29-30 | Launch prep | Deploy to production. Final checks. Open beta. First Reddit/LinkedIn posts. |

---

## 15. COMMON PITFALLS & HOW TO AVOID THEM

### Pitfall 1: "I didn't get a refresh token from Google"
**Why:** Google only returns a refresh_token on the FIRST authorization, or if you include `prompt=consent` in the OAuth URL.
**Fix:** ALWAYS include `prompt=consent&access_type=offline` in your Google OAuth URL. This forces the consent screen every time and guarantees a refresh token.

### Pitfall 2: "Meta token expired and I didn't notice"
**Why:** Long-lived Meta tokens expire silently after 60 days. No notification from Meta.
**Fix:** Store `token_expires_at` when you create the long-lived token (current time + 60 days). Run daily checks. Alert users 7 days before expiry.

### Pitfall 3: "Numbers in my report don't match Google Analytics dashboard"
**Why:** GA4 API returns data based on the date range and timezone of the property. If your API call uses UTC dates but the GA4 property is set to EST, you'll get slightly different numbers for boundary dates.
**Fix:** When pulling data, use the PROPERTY's timezone, not UTC. The GA4 API lets you specify this. Or, always pull date ranges with 1-day buffer and trim in your code.

### Pitfall 4: "Meta API returns different conversion numbers than Ads Manager"
**Why:** Attribution windows, delayed conversions, and privacy-driven modeling. Meta's API and dashboard can show different numbers for the same campaign.
**Fix:** Accept this reality. Add a disclaimer in the report footer: "Numbers may differ slightly from platform dashboards due to attribution windows and data processing timing." This is what AgencyAnalytics and every competitor does too.

### Pitfall 5: "User connected Google but I can't pull data for a specific property"
**Why:** The user's Google account has access to some properties but not others. Or the property is a Universal Analytics property (not GA4).
**Fix:** When listing properties, filter to only show GA4 properties (they start with "properties/" in the API). If a property returns a permissions error, show a helpful message: "You don't have access to this property. Ask the property owner to add your Google account as a Viewer."

### Pitfall 6: "My Google OAuth verification was rejected"
**Why:** Common reasons — privacy policy doesn't mention Google data, app homepage is missing, OAuth flow has issues.
**Fix:** Before submitting, verify:
- Privacy policy explicitly mentions Google Analytics data
- Privacy policy states you don't sell user data
- App homepage clearly explains what ReportPilot does
- OAuth flow works correctly on mobile AND desktop
- You request ONLY the scopes you actually use

### Pitfall 7: "Meta App Review was rejected"
**Why:** Common reasons — screencast doesn't clearly show the permission being used, app description is vague, missing privacy policy details.
**Fix:** In your screencast, EXPLICITLY show:
- The OAuth login flow
- The ads_read data being displayed in your app (show actual campaign names, spend numbers)
- The purpose: "This data is used to generate automated client reports"
- In your app description, be VERY specific: "ReportPilot reads ad performance data (spend, impressions, clicks, conversions) to generate automated performance reports for marketing agencies."

### Pitfall 8: "I stored tokens in localStorage/cookies accessible to frontend JavaScript"
**Why:** XSS vulnerability. If any JavaScript injection occurs, tokens are exposed.
**Fix:** OAuth tokens should NEVER touch the frontend. The entire token exchange happens server-side. The frontend only knows "this connection is active" (a boolean), never the actual token value. All API calls to Google/Meta happen from your BACKEND, not from the user's browser.

---

*This document covers every authentication and integration scenario for ReportPilot. Combined with the Feature Blueprint and Business Deep Dive, these three documents form the complete specification needed to build the product.*

*Total documents in the ReportPilot spec:*
1. *reportpilot-deep-dive.md — Business case, competitors, pricing, GTM, revenue projections*
2. *reportpilot-feature-design-blueprint.md — Features, screens, AI prompts, data model, design system*
3. *reportpilot-auth-integration-deepdive.md — OAuth flows, token management, security, verification process*