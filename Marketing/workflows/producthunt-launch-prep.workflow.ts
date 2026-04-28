// Canonical source for n8n workflow: GRP - Product Hunt Launch Prep (One-time)
// Workflow ID: Uemqcr6Puic67It4
//
// One-time, manually-triggered workflow. Generates a complete Product Hunt
// launch asset pack in a single Drive folder. Saurabh executes when ready
// to launch (or on a dry run a few days before).
//
// Output (11 files in ProductHunt-Launch/ folder):
//   1. tagline.txt              — 60-char PH tagline
//   2. product-description.txt  — 260-char PH description
//   3. first-comment.txt        — Founder's intro post (immediately after launch)
//   4. maker-replies.txt        — 3 sample replies for common questions
//   5. launch-email.txt         — Subject + body for personal-network outreach
//   6. twitter-thread.txt       — 5-7 tweet thread (numbered)
//   7. linkedin-post.txt        — 1200-1500 char LinkedIn announcement
//   8. hunter-dm.txt            — 50-word DM to a PH hunter
//   9. faqs.txt                 — 5 pre-emptive Q&As
//   10. checklist.txt           — 10-action launch-day timeline (T-7d → T+24h)
//   11. SUMMARY.md              — Overview + review checklist for Saurabh
//
// Architecture follows established patterns:
//   - Manual trigger (not scheduled)
//   - Brand voice + product facts hardcoded as consts
//   - Drive folder lookup: operation=search, searchMethod=query (WF7 lesson)
//   - .txt + .md files (no Google Docs conversion)
//   - Single big OpenAI call producing all 11 assets in structured JSON
//   - Defensive parse of output[].content[].text (WF7 lesson)
//   - Multi-item Drive upload — 11 items in, 11 files uploaded
//   - One log row per run
//
// Pre-launch: Saurabh creates ProductHunt-Launch-Log sheet, sends ID. Until then
// the Append Log Row step fails gracefully (onError continueRegularOutput).
//
// To deploy:
//   1. create_workflow_from_code(code=<this file>)
//   2. publish_workflow
//   3. execute_workflow (manual)

import { workflow, node, trigger, ifElse, newCredential, expr } from '@n8n/workflow-sdk';

// === Resource IDs ============================================================
const MARKETING_PARENT_ID = '1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj';
const COMPETITOR_CHANGELOG_ID = '10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM';
const COMPETITOR_CHANGELOG_TAB = 'Competitor-Changelog';
const PH_LAUNCH_FOLDER_NAME = 'ProductHunt-Launch';

// TODO: Saurabh creates the ProductHunt-Launch-Log sheet, sends ID. Until then
// the final append step fails gracefully — all 11 .txt files still save to Drive.
const PH_LAUNCH_LOG_SHEET_ID = '1XjxlYOHcilvu9iYo_aX2q_paxrdDOt8jO0z-MqMebdM';
const PH_LAUNCH_LOG_TAB = 'ProductHunt-Launch-Log';

// === Brand voice (synced from Marketing/context/brand-voice.md) ==============
const BRAND_VOICE = `# GoReportPilot — Brand Voice

## Tone

Confident, technical, direct, zero fluff. You sound like a founder who used to spend 6 hours a month making client reports manually and got fed up enough to build a tool. You speak from that lived experience — not as a marketer pitching a product.

## Banned phrases (never use)

- "leverage" / "leveraging"
- "synergy" / "synergistic"
- "in today's fast-paced world"
- "revolutionary"
- "AI-powered" (too generic — say what the AI actually does)
- "AI-driven" (same problem as AI-powered)
- "game-changer" / "game changing"
- "seamlessly"
- "best-in-class"
- "robust solution"
- "cutting-edge"
- "next-generation"
- "streamlined" / "streamline"
- "transform your"
- "elevate your"

## Always do

- Name competitors specifically (AgencyAnalytics, Whatagraph, Swydo, NinjaCat, Looker Studio) when context calls for it.
- Use specific numbers (6 hours/month, 59 dollars saved/client, 12 reports/week) — not vague claims like "save tons of time".
- Write like a person, not a brand. Contractions are fine. First-person singular when the founder is speaking.
- Lead with the prospect's situation, not the product.
- Acknowledge tradeoffs honestly. We have an opinion ("limited by client count, not by report volume — that's deliberate") not just a feature list.
- End with a specific, low-friction CTA.

## Founder context (one-line bio for any time we sign off)

Saurabh Singh, founder of GoReportPilot. Bareilly, India. Built it after spending too many late nights stitching together GA4 + Meta Ads + Google Ads exports for client reports.

## Differentiator we lean on

Most reporting tools (AgencyAnalytics, Whatagraph) charge by report volume — the more you report, the more you pay. We charge by client count: Starter 2 / Pro 10 / Agency 50 clients, unlimited reports per client. This matters most for agencies running weekly cadences — they're the ones the volume-based pricing punishes. Mention this only when it's actually relevant to the prospect, not as a boilerplate line.
`;

// === Product facts (the AI's source-of-truth for the launch) ================
// Hardcoded as a template-literal string. Saurabh edits this + republishes
// when product facts change (pricing, features, etc.). The SDK parser blocks
// Array.prototype.join() at module scope, so a simple template literal is
// the cleanest way to embed multi-line product context here.
const PRODUCT_FACTS_BLOCK = `== PRODUCT FACTS ==
Name: GoReportPilot
URL: https://goreportpilot.com
Current tagline (we are generating a NEW one — context only): AI-narrated client reporting for digital marketing agencies
Founder: Saurabh Singh
Category: Marketing automation / Reporting

Core features:
- GA4 + Meta Ads + Google Ads + Search Console integrations (one-click OAuth)
- AI-narrated PPTX/PDF reports (multi-paragraph commentary, not one-line summaries)
- White-label client reports with agency branding (logo, brand color, custom footer)
- Scheduled recurring reports (weekly / biweekly / monthly, auto-emailed to client)
- Editable PPTX export so agencies can customize per client before sending
- Client-count pricing — pay per client, not per report

Differentiator: Only affordable tool with multi-paragraph AI narrative + editable PPTX export, priced by client count not report volume — so weekly-cadence agencies don't get punished for showing up consistently.

Pricing: Starter $19 (2 clients) / Pro $39 (10) / Agency $69 (50). All plans: unlimited reports per client.

Competitors: AgencyAnalytics ($59-$259/mo, charges per report), Whatagraph ($249-$999/mo, charges per data source), Swydo ($39-$249/mo), NinjaCat ($295+ enterprise), Looker Studio (free but DIY data wiring eats hours).

Built by: Solo founder Saurabh Singh, Bareilly India. Built after spending 6 hours/month manually stitching GA4 + Meta + Google Ads exports into client decks during agency work.
Built with: Next.js, FastAPI, Supabase (Postgres + Auth), OpenAI GPT-4.1, python-pptx, LibreOffice for PDF, Razorpay billing.
Ideal user: Digital marketing agencies and freelancers managing 2-50 clients with monthly or weekly reporting cadence.
Proof points: Trial: 14 days, no credit card. Production-ready (live on goreportpilot.com). 19 chart types, 6 visual templates, 13 languages.`;

// === Trigger (manual — Saurabh executes when ready) ==========================
const trig = trigger({ type: 'n8n-nodes-base.manualTrigger', version: 1, config: { name: 'Manual Launch Trigger', parameters: {}, position: [240, 400] }, output: [{}] });

// === Day Meta ================================================================
const dayMeta = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Day Meta', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const istNow = new Date(new Date().getTime() + (5.5 * 60 * 60 * 1000));\nconst dateStr = istNow.toISOString().slice(0, 10);\nreturn [{ json: { date_str: dateStr, year: istNow.getUTCFullYear() } }];" }, position: [440, 400] }, output: [{ date_str: '2026-04-28', year: 2026 }] });

// === Set Brand Voice =========================================================
const setBrandVoice = node({ type: 'n8n-nodes-base.set', version: 3.4, config: { name: 'Set Brand Voice', parameters: { mode: 'manual', assignments: { assignments: [{ id: 'bv1', name: 'brand_voice', value: BRAND_VOICE, type: 'string' }, { id: 'bv2', name: 'product_facts', value: PRODUCT_FACTS_BLOCK, type: 'string' }] }, includeOtherFields: false }, position: [640, 400] }, output: [{ brand_voice: '...', product_facts: '...' }] });

// === Read Competitor Changelog (last 30 days, filtered in Compose) ===========
const readCompetitorChangelog = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Read Competitor Changelog', parameters: { resource: 'sheet', operation: 'read', documentId: { __rl: true, mode: 'id', value: COMPETITOR_CHANGELOG_ID }, sheetName: { __rl: true, mode: 'name', value: COMPETITOR_CHANGELOG_TAB }, options: { returnAllMatches: 'returnAllMatches', dataLocationOnSheet: { values: { rangeDefinition: 'detectAutomatically', readRowsUntil: 'lastRowInSheet' } } } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, executeOnce: true, onError: 'continueRegularOutput', position: [840, 400] }, output: [{ date: '2026-04-25', competitor: 'AgencyAnalytics', page: '/pricing', summary: 'Added Enterprise tier', status: 'changed' }] });

// === Compose Launch Context ==================================================
// Aggregates brand voice + product facts + 30-day competitor block into the
// final OpenAI prompt context. Single Code node, single output item.
const composeLaunchContext = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Compose Launch Context', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "function safeAll(name) { try { return $(name).all() || []; } catch(e) { return []; } }\nfunction safeFirstJson(name) { try { return ($(name).first() || {}).json || {}; } catch(e) { return {}; } }\nfunction parseDate(v) { if (!v) return null; const d = new Date(v); return isNaN(d.getTime()) ? null : d; }\nconst dayMeta = safeFirstJson('Day Meta');\nconst voiceMeta = safeFirstJson('Set Brand Voice');\nconst brandVoice = String(voiceMeta.brand_voice || '');\nconst productFacts = String(voiceMeta.product_facts || '');\nconst competitorRows = safeAll('Read Competitor Changelog').map(it => (it && it.json) ? it.json : {});\nconst thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);\nconst competitorRecent = competitorRows.filter(r => {\n  const status = String(r.status || '').toLowerCase();\n  if (status && status !== 'changed') return false;\n  const d = parseDate(r.date || r.timestamp);\n  return d && d > thirtyDaysAgo;\n});\nconst competitorBlock = competitorRecent.length === 0 ? '(no competitor changes detected in last 30 days)' : competitorRecent.slice(0, 15).map((r, i) => (i + 1) + '. [' + (r.competitor || 'unknown') + ' ' + (r.page || '') + '] ' + String(r.summary || '').slice(0, 220)).join('\\n');\nreturn [{ json: { ...dayMeta, brand_voice: brandVoice.slice(0, 4000), product_facts: productFacts, competitor_block: competitorBlock, competitor_count: competitorRecent.length } }];" }, position: [1040, 400] }, output: [{ date_str: '2026-04-28', brand_voice: '...', product_facts: '...', competitor_block: '...' }] });

// === Generate Launch Assets (one big OpenAI call producing all 11 assets) ====
const launchSystemPrompt = "You are a Product Hunt launch strategist with founder-voice writing skills, working for Saurabh Singh, founder of GoReportPilot. Your job: produce a complete launch asset pack in ONE structured JSON response.\n\nVOICE: confident, technical, direct, zero fluff. Saurabh built this after personally spending 6 hours/month on client reports during agency work. He speaks from lived experience, not as a marketer.\n\nBANNED PHRASES (never use, no exceptions): leverage, synergy, in today's fast-paced world, revolutionary, AI-powered, AI-driven, game-changer, seamless, robust, cutting-edge, next-generation, best-in-class, streamlined, transform your, elevate your.\n\n== PRODUCT HUNT KNOWLEDGE (constraints from PH itself) ==\n\nTAGLINE (60 chars max, hard PH limit):\n- Hook-driven, NOT 'XYZ for ABC' formula\n- Lead with what's specific (the multi-paragraph AI narrative, the client-count pricing, the editable PPTX) — not generic 'simplify reporting'\n- Examples of good shape: 'Client reports that read like a strategist wrote them' / 'Reporting priced by clients, not reports'\n\nPRODUCT DESCRIPTION (260 chars max, hard PH limit):\n- Benefit-first sentence + concrete differentiator + low-friction CTA\n- No buzzwords. Specific numbers > vague claims.\n- Must fit in EXACTLY 260 chars or under (count carefully — PH truncates)\n\nFIRST COMMENT (founder's post immediately after launch goes live):\n- 300-500 words\n- Origin story (why Saurabh built it — the 6 hours/month pain, the late nights stitching exports)\n- What makes it different (multi-paragraph AI narrative + editable PPTX + client-count pricing)\n- What he's watching today (e.g. 'curious how agencies running weekly cadences feel about the pricing')\n- ONE clear ask at the end (e.g. 'feedback on whether the Pro tier's 10-client limit feels right')\n- NO emojis. Conversational, not corporate.\n\nMAKER REPLIES (3 sample responses for common questions):\n- Each 80-150 words\n- Topics to cover: pricing rationale, comparison to AgencyAnalytics/Whatagraph, what's next on the roadmap\n- Be specific, name competitors honestly, acknowledge tradeoffs\n\nLAUNCH EMAIL (for Saurabh's personal network):\n- Subject: 5-7 words, no spam triggers\n- Body: 80-120 words. Personal, not press-release. ONE specific ask + specific time window (e.g. 'first 4 hours after midnight PT today')\n- Use [NAME] placeholder so Saurabh personalizes per recipient\n\nTWITTER THREAD (5-7 tweets):\n- Each ≤280 chars\n- First tweet hooks + ends with PH link (use {{PH_LAUNCH_URL}} placeholder — Saurabh fills the real URL)\n- Numbered (1/, 2/, etc.)\n- No emojis unless ONE strategic placement\n\nLINKEDIN POST (1200-1500 chars):\n- Hook in first 200 chars (LinkedIn truncates after that)\n- Founder voice. Why now, why this, what's specific.\n- One genuine question at end inviting feedback (NOT 'What do you think?')\n\nHUNTER DM (50 words max):\n- For asking a Product Hunt hunter to post the launch on Saurabh's behalf\n- Mention ONE specific thing about the product that's hunter-worthy\n- Polite, brief, no emoji\n\nFAQS (5 pre-emptive Q&As):\n- Anticipate REAL questions agency founders ask: pricing fit, white-label depth, GA4 setup time, refund policy, what happens if a client fires me\n- Each answer: 60-100 words. Specific, no fluff.\n\nLAUNCH-DAY CHECKLIST (10 actions with timing):\n- Format: 'T-7d: Action description' or 'T+0h: Action description'\n- Span T-7d (warm-up), T-1d (hunter scheduled), T-1h (assets staged), T+0 (launch goes live), T+2h, T+6h, T+24h (close out)\n- Each action: one sentence, concrete and verifiable\n\nOUTPUT — strict JSON only, no markdown fences:\n{\"tagline\": \"...\", \"product_description\": \"...\", \"first_comment\": \"...\", \"maker_replies\": [\"reply 1\", \"reply 2\", \"reply 3\"], \"launch_email_subject\": \"...\", \"launch_email_body\": \"...\", \"twitter_thread\": [\"tweet 1\", \"tweet 2\", \"...\"], \"linkedin_post\": \"...\", \"hunter_dm\": \"...\", \"faqs\": [{\"q\": \"...\", \"a\": \"...\"}, {\"q\": \"...\", \"a\": \"...\"}, {\"q\": \"...\", \"a\": \"...\"}, {\"q\": \"...\", \"a\": \"...\"}, {\"q\": \"...\", \"a\": \"...\"}], \"checklist\": [\"T-7d: ...\", \"T-1d: ...\", \"...\"]}";

const launchUserPrompt = "Generate the complete Product Hunt launch asset pack for the product below. Use the brand voice and competitive context. Output strict JSON.\n\n{{ $json.product_facts }}\n\n== COMPETITIVE LANDSCAPE (last 30 days of competitor changes — use for sharper positioning) ==\n{{ $json.competitor_block }}\n\n== BRAND VOICE NOTES (authoritative — follow strictly) ==\n{{ $json.brand_voice }}\n\nGenerate all 11 assets in one JSON response.";

const generateLaunchAssets = node({ type: '@n8n/n8n-nodes-langchain.openAi', version: 2.1, config: { name: 'Generate Launch Assets', parameters: { resource: 'text', operation: 'response', modelId: { __rl: true, mode: 'id', value: 'gpt-4o' }, responses: { values: [{ type: 'text', role: 'system', content: launchSystemPrompt }, { type: 'text', role: 'user', content: expr(launchUserPrompt) }] }, simplify: true, options: { maxTokens: 6000, temperature: 0.5, textFormat: { textOptions: [{ type: 'json_object' }] } } }, credentials: { openAiApi: newCredential('OpenAI') }, position: [1240, 400] }, output: [{ content: '{"tagline": "...", "product_description": "...", "first_comment": "...", "maker_replies": [], "launch_email_subject": "...", "launch_email_body": "...", "twitter_thread": [], "linkedin_post": "...", "hunter_dm": "...", "faqs": [], "checklist": []}' }] });

// === Parse Launch Assets (defensive parse — handles output[].content[].text) =
const parseLaunchAssets = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Parse Launch Assets', parameters: { mode: 'runOnceForEachItem', language: 'javaScript', jsCode: "const j = $input.item.json || {};\nlet raw = '';\nif (typeof j === 'string') raw = j;\nelse if (typeof j.content === 'string') raw = j.content;\nelse if (typeof j.text === 'string') raw = j.text;\nelse if (typeof j.output_text === 'string') raw = j.output_text;\nelse if (typeof j.output === 'string') raw = j.output;\nelse if (j.message && typeof j.message.content === 'string') raw = j.message.content;\nelse if (Array.isArray(j.output)) {\n  for (const o of j.output) {\n    const cs = Array.isArray(o.content) ? o.content : (o.content ? [o.content] : []);\n    for (const c of cs) { if (c && typeof c.text === 'string') raw += c.text; }\n  }\n}\nif (!raw) raw = JSON.stringify(j);\nlet parsed = null;\ntry { parsed = JSON.parse(raw); } catch(e) { const m = raw.match(/\\{[\\s\\S]*\\}/); if (m) { try { parsed = JSON.parse(m[0]); } catch(_) {} } }\nif (!parsed || typeof parsed !== 'object') parsed = {};\nconst dayMeta = $('Day Meta').first().json;\nreturn {\n  ...dayMeta,\n  tagline: String(parsed.tagline || '').trim(),\n  product_description: String(parsed.product_description || '').trim(),\n  first_comment: String(parsed.first_comment || '').trim(),\n  maker_replies: Array.isArray(parsed.maker_replies) ? parsed.maker_replies.map(r => String(r || '').trim()).filter(Boolean) : [],\n  launch_email_subject: String(parsed.launch_email_subject || '').trim(),\n  launch_email_body: String(parsed.launch_email_body || '').trim(),\n  twitter_thread: Array.isArray(parsed.twitter_thread) ? parsed.twitter_thread.map(t => String(t || '').trim()).filter(Boolean) : [],\n  linkedin_post: String(parsed.linkedin_post || '').trim(),\n  hunter_dm: String(parsed.hunter_dm || '').trim(),\n  faqs: Array.isArray(parsed.faqs) ? parsed.faqs.filter(f => f && f.q && f.a) : [],\n  checklist: Array.isArray(parsed.checklist) ? parsed.checklist.map(c => String(c || '').trim()).filter(Boolean) : [],\n  parse_failed: (!parsed.tagline && !parsed.product_description) ? true : false\n};" }, position: [1440, 400] }, output: [{ tagline: '...', product_description: '...', first_comment: '...', maker_replies: [], launch_email_subject: '...', launch_email_body: '...', twitter_thread: [], linkedin_post: '...', hunter_dm: '...', faqs: [], checklist: [] }] });

// === Find ProductHunt-Launch folder (operation=search + searchMethod=query) ==
const findLaunchFolder = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Find Launch Folder', parameters: { resource: 'fileFolder', operation: 'search', searchMethod: 'query', queryString: "name = 'ProductHunt-Launch' and '1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false", returnAll: true, filter: {}, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [1640, 400] }, output: [{ id: 'mockFolderId', name: 'ProductHunt-Launch' }] });

const resolveFolderId = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Resolve Folder ID', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const items = $input.all();\nconst hits = items.filter(it => it && it.json && it.json.id && (it.json.mimeType === 'application/vnd.google-apps.folder' || !it.json.mimeType));\nif (hits.length > 0) {\n  return [{ json: { folder_id: hits[0].json.id, folder_name: hits[0].json.name || 'ProductHunt-Launch', _exists: true } }];\n}\nreturn [{ json: { folder_id: '', _exists: false } }];" }, position: [1840, 400] }, output: [{ folder_id: 'mockFolderId', _exists: true }] });

const folderExistsIf = ifElse({ version: 2.3, config: { name: 'Folder Exists?', parameters: { conditions: { combinator: 'and', options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 }, conditions: [{ leftValue: expr('{{ $json._exists }}'), rightValue: true, operator: { type: 'boolean', operation: 'true' } }] } }, position: [2040, 400] } });

const createLaunchFolder = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Create Launch Folder', parameters: { resource: 'folder', operation: 'create', name: PH_LAUNCH_FOLDER_NAME, driveId: { __rl: true, mode: 'list', value: 'My Drive' }, folderId: { __rl: true, mode: 'id', value: MARKETING_PARENT_ID }, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, position: [2240, 250] }, output: [{ id: 'newFolderId', name: 'ProductHunt-Launch' }] });

// === Build Asset Files =======================================================
// Reads parsed assets from upstream and emits 11 binary items (one per file).
// Each item carries the same folder_id; the downstream Drive upload runs once
// per item, producing 11 files. SUMMARY.md is generated last with overview.
const buildAssetFiles = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Build Asset Files', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const item = $input.first();\nconst j = (item && item.json) ? item.json : {};\nconst folder_id = j.folder_id || j.id || '';\nconst meta = $('Parse Launch Assets').first().json;\nconst dayMeta = $('Day Meta').first().json;\nconst dateStr = dayMeta.date_str || new Date().toISOString().slice(0, 10);\nfunction enc(content, name, mimeType) {\n  const ext = name.endsWith('.md') ? 'md' : 'txt';\n  return { json: { folder_id: folder_id, file_name: name }, binary: { data: { data: Buffer.from(String(content || '(empty)'), 'utf8').toString('base64'), mimeType: mimeType || 'text/plain', fileName: name, fileExtension: ext } } };\n}\nconst makerReplies = (meta.maker_replies || []).map((r, i) => '### Reply ' + (i + 1) + '\\n\\n' + r).join('\\n\\n');\nconst emailContent = 'Subject: ' + (meta.launch_email_subject || '') + '\\n\\n---\\n\\n' + (meta.launch_email_body || '');\nconst tweets = (meta.twitter_thread || []);\nconst tweetContent = tweets.map((t, i) => (i + 1) + '/' + tweets.length + '\\n\\n' + t).join('\\n\\n---\\n\\n');\nconst faqContent = (meta.faqs || []).map((f, i) => '### Q' + (i + 1) + ': ' + (f.q || '') + '\\n\\n' + (f.a || '')).join('\\n\\n');\nconst checklistContent = (meta.checklist || []).map((c, i) => (i + 1) + '. ' + c).join('\\n');\nconst summary = '# Product Hunt Launch — Asset Pack\\n\\n_Generated: ' + dateStr + '_\\n\\nThis folder contains the complete asset pack for launching GoReportPilot on Product Hunt. **Every file is a draft. Saurabh edits before posting.**\\n\\n## Files in this folder\\n\\n1. **tagline.txt** — 60-char Product Hunt tagline\\n2. **product-description.txt** — 260-char description (PH hard limit)\\n3. **first-comment.txt** — Saurabh\\'s founder intro post (post immediately after launch goes live)\\n4. **maker-replies.txt** — 3 sample replies to common questions (pricing / competitor / roadmap)\\n5. **launch-email.txt** — Subject + body for personal-network outreach. Replace [NAME] placeholder per recipient.\\n6. **twitter-thread.txt** — 5-7 numbered tweets. First tweet ends with PH URL placeholder.\\n7. **linkedin-post.txt** — 1200-1500 char LinkedIn announcement\\n8. **hunter-dm.txt** — 50-word DM to a Product Hunt hunter\\n9. **faqs.txt** — 5 anticipated Q&As\\n10. **checklist.txt** — Launch-day timeline (T-7d through T+24h)\\n\\n## Final review checklist before posting\\n\\n- [ ] Tagline reads well — does it hook on first read?\\n- [ ] Product description fits exactly within 260 chars (verify in PH preview)\\n- [ ] First comment has SPECIFIC origin story details, no buzzwords\\n- [ ] Maker replies are conversational, not corporate\\n- [ ] Launch email is personalized — replace [NAME] and [CONTEXT] placeholders\\n- [ ] Twitter thread first tweet ends with the actual PH launch URL (replace {{PH_LAUNCH_URL}})\\n- [ ] LinkedIn post hooks in first 200 chars (LinkedIn truncates)\\n- [ ] Hunter DM mentions ONE specific thing about the product\\n- [ ] FAQs anticipate the actual questions, not generic ones\\n- [ ] Checklist timing fits Saurabh\\'s actual launch day timezone\\n\\n## Notes\\n\\n- Generated using gpt-4o based on hardcoded PRODUCT facts + 30-day competitor context.\\n- Brand voice rules enforced. Banned phrases: leverage, synergy, AI-powered, AI-driven, game-changer, seamless, robust, cutting-edge, streamlined, transform your, elevate your.\\n- Parse-failure flag in run log if the AI output couldn\\'t be parsed.\\n';\nreturn [\n  enc(meta.tagline || '', 'tagline.txt'),\n  enc(meta.product_description || '', 'product-description.txt'),\n  enc(meta.first_comment || '', 'first-comment.txt'),\n  enc(makerReplies, 'maker-replies.txt'),\n  enc(emailContent, 'launch-email.txt'),\n  enc(tweetContent, 'twitter-thread.txt'),\n  enc(meta.linkedin_post || '', 'linkedin-post.txt'),\n  enc(meta.hunter_dm || '', 'hunter-dm.txt'),\n  enc(faqContent, 'faqs.txt'),\n  enc(checklistContent, 'checklist.txt'),\n  enc(summary, 'SUMMARY.md', 'text/markdown')\n];" }, position: [2440, 400] }, output: [{ folder_id: 'mockFolderId', file_name: 'tagline.txt' }] });

// === Save Assets — Drive upload runs 11 times (once per input item) =========
const saveAssets = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Save Assets', parameters: { resource: 'file', operation: 'upload', inputDataFieldName: 'data', name: '={{ $json.file_name }}', driveId: { __rl: true, mode: 'list', value: 'My Drive' }, folderId: { __rl: true, mode: 'id', value: '={{ $json.folder_id }}' }, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [2640, 400] }, output: [{ id: 'fileId', name: 'tagline.txt', webViewLink: 'https://drive.google.com/...' }] });

// === Shape Log Row ===========================================================
const shapeLogRow = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Shape Log Row', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "function safeFirstJson(name){ try { return ($(name).first() || {}).json || {}; } catch(e){ return {}; } }\nconst saveItems = $input.all();\nconst dayMeta = safeFirstJson('Day Meta');\nconst meta = safeFirstJson('Parse Launch Assets');\nconst folderResolve = safeFirstJson('Resolve Folder ID');\nconst created = safeFirstJson('Create Launch Folder');\nconst folder_id = folderResolve.folder_id || created.id || '';\nconst folderUrl = folder_id ? ('https://drive.google.com/drive/folders/' + folder_id) : '';\nconst successFiles = saveItems.filter(it => it && it.json && it.json.id);\nconst filesCreated = successFiles.length;\nconst totalAttempted = saveItems.length;\nconst parseFailed = !!meta.parse_failed;\nlet status = 'success';\nlet errorMsg = '';\nif (parseFailed) { status = 'parse_failed'; errorMsg = 'OpenAI output JSON parse failed'; }\nelse if (filesCreated === 0) { status = 'all_uploads_failed'; errorMsg = 'No files saved (Drive uploads all failed)'; }\nelse if (filesCreated < totalAttempted) { status = 'partial_upload'; errorMsg = (totalAttempted - filesCreated) + ' of ' + totalAttempted + ' uploads failed'; }\nreturn [{ json: { timestamp: new Date().toISOString(), status: status, folder_url: folderUrl, files_created: String(filesCreated) + '/' + String(totalAttempted), error: errorMsg } }];" }, position: [2840, 400] }, output: [{ timestamp: '2026-04-28T00:00:00Z', status: 'success', folder_url: 'https://drive.google.com/...', files_created: '11/11', error: '' }] });

// === Append Log Row ==========================================================
const appendLogRow = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Append Log Row', parameters: { resource: 'sheet', operation: 'append', documentId: { __rl: true, mode: 'id', value: PH_LAUNCH_LOG_SHEET_ID }, sheetName: { __rl: true, mode: 'name', value: PH_LAUNCH_LOG_TAB }, columns: { mappingMode: 'autoMapInputData', value: null, matchingColumns: [], schema: [], attemptToConvertTypes: false, convertFieldsToString: true }, options: { useAppend: true, handlingExtraData: 'ignoreIt' } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [3040, 400] }, output: [{ ok: true }] });

// === Topology ===============================================================
export default workflow('grp-producthunt-launch-prep', 'GRP - Product Hunt Launch Prep (One-time)')
  .add(trig)
  .to(dayMeta)
  .to(setBrandVoice)
  .to(readCompetitorChangelog)
  .to(composeLaunchContext)
  .to(generateLaunchAssets)
  .to(parseLaunchAssets)
  .to(findLaunchFolder)
  .to(resolveFolderId)
  .to(folderExistsIf
    .onTrue(buildAssetFiles)
    .onFalse(createLaunchFolder.to(buildAssetFiles))
  )
  .add(buildAssetFiles)
  .to(saveAssets)
  .to(shapeLogRow)
  .to(appendLogRow);
