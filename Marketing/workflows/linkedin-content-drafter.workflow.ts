// Canonical source for n8n workflow: GRP - LinkedIn Content Drafter (Mon/Wed/Fri)
// Workflow ID: KmLgtb3iyt6ZTBiH
//
// Drafts 3 LinkedIn posts/week for Saurabh as founder of GoReportPilot.
// Saurabh reviews and posts manually. Never auto-posts.
//
// Schedule: Mon/Wed/Fri 07:00 IST (cron 0 30 1 * * 1,3,5 UTC)
//
// 2026-04-28 v2 — brand voice hardcoded as a string constant.
//   v1's Drive download path returned a 6-byte stub regardless of file ID,
//   because the workflow's binaryMode='separate' (filesystem mode) means the
//   Code node received a binary REFERENCE, not the bytes. Rather than fight
//   n8n's binary handling, we hardcode the brand voice string in this SDK.
//   Tradeoff: brand voice updates require editing this file + republish.
//   Acceptable since voice doc changes monthly at most.
//
//   To update brand voice:
//     1. Edit BRAND_VOICE constant below (or sync from Marketing/context/brand-voice.md).
//     2. update_workflow + publish_workflow.
//
// SDK gotcha: the parser blocks Array.prototype.join() and other function calls
// at module scope. All multi-line jsCode is a single double-quoted string with \n.
// Top-level template-literal strings (backticks) ARE allowed and used here.

import { workflow, node, trigger, ifElse, newCredential, expr } from '@n8n/workflow-sdk';

// === Resource IDs ============================================================
const MARKETING_PARENT_ID = '1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj';
const COMPETITOR_CHANGELOG_ID = '10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM';
const COMPETITOR_CHANGELOG_TAB = 'Competitor-Changelog';
const LISTENER_LOG_ID = '1iXiV_DFS5v7z7LNHcRfJIbQFP2O_K7CfCtjy3Ll0JX0';
const LISTENER_LOG_TAB = 'Listener-Log';
const DRAFTS_FOLDER_NAME = 'LinkedIn-Drafts';
// Canonical LinkedIn-Drafts folder ID: 18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA
// (resolved at runtime via Find Drafts Folder search; ID kept here as a
// reference. Two duplicates from the v1 search-bug period were manually
// deleted by Saurabh.)
const LINKEDIN_DRAFTS_LOG_SHEET_ID = '14kphwWlnEi9EifkwzLpfDN7hWGGE_Zl-MF1Rb-hQWOw';
const LINKEDIN_DRAFTS_LOG_TAB = 'LinkedIn-Drafts-Log';

// === Brand voice (synced from Marketing/context/brand-voice.md) ==============
// Authoritative copy lives in this SDK. Set Brand Voice node below feeds it
// downstream. To update: edit this constant + update_workflow + publish_workflow.
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

## Always do

- Name competitors specifically (AgencyAnalytics, Whatagraph, Swydo, NinjaCat, Looker Studio) when context calls for it.
- Use specific numbers (6 hours/month, 59 dollars saved/client, 12 reports/week) — not vague claims like "save tons of time".
- Write like a person, not a brand. Contractions are fine. First-person singular when the founder is speaking.
- Lead with the prospect's situation, not the product.
- Acknowledge tradeoffs honestly. We have an opinion ("limited by client count, not by report volume — that's deliberate") not just a feature list.
- End with a specific, low-friction CTA.

## Length targets by channel

- Cold email body: 80–120 words
- Reddit / HN comment: 30–60 words
- LinkedIn post: 100–200 words (but LinkedIn-native posts can run longer in characters; aim for 800–1500 chars total)
- Signup welcome email: 100–150 words
- Churn winback email: 80–120 words

## LinkedIn opening rules (critical)

NEVER open with a rhetorical question. A rhetorical question is ANY first sentence ending in "?". Examples of banned openings:
- "Spent 6 hours every month on reports?"
- "Are you struggling with X?"
- "What if you could X?"
- "Tired of X?"
- "Ever wonder why X?"

The hook must be a STATEMENT with a concrete detail. Examples of good openings:
- "Last Tuesday I deleted a 47-page client deck and replaced it with a 2-page narrative. The client noticed in 30 seconds."
- "Three weeks ago Whatagraph quietly raised their Boost plan from 199 to 249 dollars."
- "An agency owner showed me his AgencyAnalytics bill last week. 1,200 dollars/month for 35 clients."

## Founder context (one-line bio for any time we sign off)

Saurabh Singh, founder of GoReportPilot. Bareilly, India. Built it after spending too many late nights stitching together GA4 + Meta Ads + Google Ads exports for client reports.

## Differentiator we lean on

Most reporting tools (AgencyAnalytics, Whatagraph) charge by report volume — the more you report, the more you pay. We charge by client count: Starter 2 / Pro 10 / Agency 50 clients, unlimited reports per client. This matters most for agencies running weekly cadences — they're the ones the volume-based pricing punishes. Mention this only when it's actually relevant to the prospect, not as a boilerplate line.
`;

// === Trigger =================================================================
const trig = trigger({ type: 'n8n-nodes-base.scheduleTrigger', version: 1.3, config: { name: 'Mon Wed Fri 7AM IST', parameters: { rule: { interval: [{ field: 'cronExpression', expression: '0 30 1 * * 1,3,5' }] } }, position: [240, 400] }, output: [{ 'Day of week': 'Monday', timestamp: '2026-04-27T01:30:00.000Z' }] });

// === Day Router — pick today's content angle ================================
const dayRouter = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Day Router', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const angles = {\n  1: { angle: 'build-in-public',  headline: 'Build in public',  brief: 'Share a metric, learning, or recently shipped feature. Concrete numbers and specifics. Show the work behind GoReportPilot.' },\n  3: { angle: 'industry-insight', headline: 'Industry insight', brief: 'Comment on agency reporting pain points, competitor moves (use the recent competitor changes below), or tooling trends in marketing analytics.' },\n  5: { angle: 'educational',      headline: 'Educational',      brief: 'Practical tip for marketing agencies on client reporting, GA4, ROI demonstration, or workflow automation. Immediately useful, not abstract.' }\n};\nconst dayMap = { Sunday: 0, Monday: 1, Tuesday: 2, Wednesday: 3, Thursday: 4, Friday: 5, Saturday: 6 };\nconst rev = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];\nconst item = $input.first();\nconst dowStr = (item && item.json) ? item.json['Day of week'] : null;\nlet day;\nif (dowStr && dayMap[dowStr] !== undefined) { day = dayMap[dowStr]; }\nelse { const now = new Date(); const ist = new Date(now.getTime() + (5.5 * 60 * 60 * 1000)); day = ist.getUTCDay(); }\nconst pick = angles[day] || angles[1];\nconst istNow = new Date(new Date().getTime() + (5.5 * 60 * 60 * 1000));\nconst dateStr = istNow.toISOString().slice(0, 10);\nconst draftFileName = dateStr + '-' + pick.angle + '.txt';\nreturn [{ json: { day: day, day_of_week: rev[day] || dowStr || 'Monday', date_str: dateStr, angle: pick.angle, angle_headline: pick.headline, angle_brief: pick.brief, draft_file_name: draftFileName } }];" }, position: [440, 400] }, output: [{ day: 1, day_of_week: 'Monday', date_str: '2026-04-27', angle: 'build-in-public', angle_headline: 'Build in public', angle_brief: 'Share a metric...', draft_file_name: '2026-04-27-build-in-public.txt' }] });

// === Set Brand Voice (replaces v1 Read Brand Voice + Decode Brand Voice) =====
// Hardcoded string from BRAND_VOICE constant. Bypasses n8n's filesystem-mode
// binary handling that broke the v1 Drive download path.
const setBrandVoice = node({ type: 'n8n-nodes-base.set', version: 3.4, config: { name: 'Set Brand Voice', parameters: { mode: 'manual', assignments: { assignments: [{ id: 'bv1', name: 'brand_voice', value: BRAND_VOICE, type: 'string' }] }, includeOtherFields: false }, position: [640, 250] }, output: [{ brand_voice: 'Tone: confident, technical, direct...' }] });

// === Read Competitor Changelog (last 7 days, filtered in Compose Context) ===
const readCompetitorChangelog = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Read Competitor Changelog', parameters: { resource: 'sheet', operation: 'read', documentId: { __rl: true, mode: 'id', value: COMPETITOR_CHANGELOG_ID }, sheetName: { __rl: true, mode: 'name', value: COMPETITOR_CHANGELOG_TAB }, options: { returnAllMatches: 'returnAllMatches', dataLocationOnSheet: { values: { rangeDefinition: 'detectAutomatically', readRowsUntil: 'lastRowInSheet' } } } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, executeOnce: true, onError: 'continueRegularOutput', position: [840, 250] }, output: [{ date: '2026-04-25', competitor: 'AgencyAnalytics', page: '/pricing', summary: 'Added Enterprise tier', status: 'changed' }] });

// === Read Listener-Log (last 7 days of HN/Reddit run summaries) =============
const readListenerLog = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Read Listener Log', parameters: { resource: 'sheet', operation: 'read', documentId: { __rl: true, mode: 'id', value: LISTENER_LOG_ID }, sheetName: { __rl: true, mode: 'name', value: LISTENER_LOG_TAB }, options: { returnAllMatches: 'returnAllMatches', dataLocationOnSheet: { values: { rangeDefinition: 'detectAutomatically', readRowsUntil: 'lastRowInSheet' } } } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, executeOnce: true, onError: 'continueRegularOutput', position: [1040, 250] }, output: [{ date: '2026-04-25', hn_posts_found: '4', reddit_posts_found: '6', qualified_count: '3', drafts_created: '3', status: 'success' }] });

// === Compose Context — aggregates everything for the AI prompt ===============
const composeContext = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Compose Context', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "function safeAll(name) { try { return $(name).all() || []; } catch(e) { return []; } }\nfunction safeFirstJson(name) { try { return ($(name).first() || {}).json || {}; } catch(e) { return {}; } }\nfunction parseDate(v) { if (!v) return null; const d = new Date(v); return isNaN(d.getTime()) ? null : d; }\nconst dayMeta = safeFirstJson('Day Router');\nconst brandVoice = String(safeFirstJson('Set Brand Voice').brand_voice || '');\nconst competitorRows = safeAll('Read Competitor Changelog').map(it => (it && it.json) ? it.json : {});\nconst listenerRows = safeAll('Read Listener Log').map(it => (it && it.json) ? it.json : {});\nconst sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);\nconst competitorRecent = competitorRows.filter(r => {\n  const status = String(r.status || '').toLowerCase();\n  if (status && status !== 'changed') return false;\n  const d = parseDate(r.date || r.timestamp);\n  return d && d > sevenDaysAgo;\n});\nconst listenerRecent = listenerRows.filter(r => {\n  const d = parseDate(r.date || r.timestamp);\n  return d && d > sevenDaysAgo;\n});\nconst competitorBlock = competitorRecent.length === 0 ? '(no competitor changes detected in the last 7 days)' : competitorRecent.slice(0, 8).map((r, i) => (i + 1) + '. [' + (r.competitor || 'unknown') + ' ' + (r.page || '') + '] ' + String(r.summary || '').slice(0, 240) + (r.categories ? ' (categories: ' + r.categories + ')' : '')).join('\\n');\nlet listenerBlock;\nif (listenerRecent.length === 0) {\n  listenerBlock = '(no community-listener runs in the last 7 days)';\n} else {\n  const totalQualified = listenerRecent.reduce((s, r) => s + (parseInt(r.qualified_count, 10) || 0), 0);\n  const totalDrafts = listenerRecent.reduce((s, r) => s + (parseInt(r.drafts_created, 10) || 0), 0);\n  listenerBlock = 'Last 7 days of Reddit/HN listening: ' + listenerRecent.length + ' runs, ' + totalQualified + ' qualified threads, ' + totalDrafts + ' draft comments generated. Themes worth riffing on: agency reporting time cost, Looker Studio frustration, AgencyAnalytics pricing, white-label PDF needs.';\n}\nconst voiceExcerpt = brandVoice.slice(0, 4000);\nreturn [{ json: { ...dayMeta, brand_voice: voiceExcerpt, competitor_block: competitorBlock, listener_block: listenerBlock, competitor_count: competitorRecent.length, listener_count: listenerRecent.length, brand_voice_chars: voiceExcerpt.length } }];" }, position: [1240, 400] }, output: [{ day: 1 }] });

// === OpenAI Draft (gpt-4o) ===================================================
// System prompt tightened in v2 to fix exec 17701 violations:
//   - "AI-driven" added to banned phrases (was "AI-powered" only)
//   - Rhetorical-question ban hardened with concrete examples
const draftSystemPrompt = "You draft a LinkedIn post for Saurabh Singh, founder of GoReportPilot — a B2B SaaS that automates client reporting for digital marketing agencies (pulls GA4, Meta Ads, Google Ads, Search Console; AI-narrated PPTX/PDF reports). Saurabh writes as a builder in public.\n\nVOICE: confident, technical, direct, zero fluff. Sound like a founder who used to spend 6 hours/month making client reports and got fed up. Use the brand voice excerpt below as authoritative.\n\nBANNED PHRASES (never use, no exceptions): leverage, synergy, in today's fast-paced world, revolutionary, AI-powered, AI-driven, game-changer, seamless, robust, cutting-edge, next-generation, best-in-class.\n\nFORMAT:\n- 800-1500 characters in post_body (LinkedIn sweet spot — not Twitter brevity, not blog length).\n- First sentence is a hook — a STATEMENT with a concrete detail. NEVER open with a rhetorical question. A rhetorical question is ANY first sentence ending in '?'. Examples of banned openings: 'Spent 6 hours every month on reports?', 'Are you struggling with X?', 'What if you could X?', 'Tired of X?', 'Ever wonder why X?'. If the first sentence ends in '?', rewrite it as a statement.\n- Specific numbers and named tools beat vague claims. Name competitors when relevant: AgencyAnalytics, Whatagraph, Swydo, NinjaCat, Looker Studio.\n- One concrete takeaway the reader can act on or remember.\n- End with an invitation to engage — a real question grounded in specifics, not 'What do you think?'.\n- No emojis unless ONE strategic placement adds something. Default: zero emojis.\n- Line breaks between paragraphs. LinkedIn shows the first ~210 chars before '...see more' — make those count.\n\nOUTPUT — strict JSON only, no markdown fences:\n{\"post_body\": \"the full post text, 800-1500 chars\", \"hashtags\": [\"AgencyLife\", \"BuildInPublic\", \"MarketingOps\"], \"rationale\": \"one sentence on why this post works for Saurabh's audience of agency founders\"}";

const draftUserPrompt = "Today is {{ $json.day_of_week }} ({{ $json.date_str }}).\nAngle: {{ $json.angle_headline }} — {{ $json.angle_brief }}\n\nRECENT COMPETITOR CHANGES (last 7 days, status=changed):\n{{ $json.competitor_block }}\n\nRECENT COMMUNITY DISCUSSIONS (last 7 days, Reddit/HN listener summary):\n{{ $json.listener_block }}\n\nBRAND VOICE NOTES (authoritative — follow strictly):\n{{ $json.brand_voice }}\n\nDraft today's LinkedIn post. Output strict JSON.";

const draftPost = node({ type: '@n8n/n8n-nodes-langchain.openAi', version: 2.1, config: { name: 'Draft Post', parameters: { resource: 'text', operation: 'response', modelId: { __rl: true, mode: 'id', value: 'gpt-4o' }, responses: { values: [{ type: 'text', role: 'system', content: draftSystemPrompt }, { type: 'text', role: 'user', content: expr(draftUserPrompt) }] }, simplify: true, options: { maxTokens: 900, temperature: 0.6, textFormat: { textOptions: [{ type: 'json_object' }] } } }, credentials: { openAiApi: newCredential('OpenAI') }, position: [1440, 400] }, output: [{ content: '{"post_body": "...", "hashtags": ["AgencyLife"], "rationale": "..."}' }] });

// === Parse Draft — extracts body, hashtags, rationale, char_count ============
const parseDraft = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Parse Draft', parameters: { mode: 'runOnceForEachItem', language: 'javaScript', jsCode: "const j = $input.item.json || {};\nlet raw = '';\nif (typeof j === 'string') raw = j;\nelse if (typeof j.content === 'string') raw = j.content;\nelse if (typeof j.text === 'string') raw = j.text;\nelse if (typeof j.output_text === 'string') raw = j.output_text;\nelse if (typeof j.output === 'string') raw = j.output;\nelse if (j.message && typeof j.message.content === 'string') raw = j.message.content;\nelse if (Array.isArray(j.output)) {\n  for (const o of j.output) { const cs = Array.isArray(o.content) ? o.content : (o.content ? [o.content] : []); for (const c of cs) { if (c && typeof c.text === 'string') raw += c.text; } }\n}\nif (!raw) raw = JSON.stringify(j);\nlet parsed = null;\ntry { parsed = JSON.parse(raw); } catch(e) { const m = raw.match(/\\{[\\s\\S]*\\}/); if (m) { try { parsed = JSON.parse(m[0]); } catch(_) {} } }\nif (!parsed || typeof parsed !== 'object') parsed = { post_body: raw, hashtags: [], rationale: 'parse_failed' };\nconst meta = $('Compose Context').first().json;\nconst post_body = String(parsed.post_body || '').trim();\nconst hashtagsArr = Array.isArray(parsed.hashtags) ? parsed.hashtags.slice(0, 5).map(h => String(h).replace(/^#/, '').trim()).filter(Boolean) : [];\nconst rationale = String(parsed.rationale || '').slice(0, 250);\nconst char_count = post_body.length;\nconst hashtags_str = hashtagsArr.map(h => '#' + h).join(' ');\nreturn { ...meta, post_body: post_body, hashtags: hashtagsArr, hashtags_str: hashtags_str, rationale: rationale, char_count: char_count };" }, position: [1640, 400] }, output: [{ post_body: '...', char_count: 1024 }] });

// === Find Drafts Folder (Drive search by exact name + parent + mimeType) =====
// IMPORTANT: operation='search' (NOT 'getMany') and searchMethod='query' so
// queryString is interpreted as a Drive API query expression. The 'getMany'
// combo silently fails with "Cannot read properties of undefined (reading
// 'execute')" — discovered the hard way (exec 17699).
const findDraftsFolder = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Find Drafts Folder', parameters: { resource: 'fileFolder', operation: 'search', searchMethod: 'query', queryString: "name = 'LinkedIn-Drafts' and '1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false", returnAll: true, filter: {}, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [1840, 400] }, output: [{ id: '18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA', name: 'LinkedIn-Drafts' }] });

// === Resolve Folder ID — emit exactly 1 item with {folder_id, _exists} ======
const resolveFolderId = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Resolve Folder ID', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const items = $input.all();\nconst hits = items.filter(it => it && it.json && it.json.id && (it.json.mimeType === 'application/vnd.google-apps.folder' || !it.json.mimeType));\nif (hits.length > 0) {\n  return [{ json: { folder_id: hits[0].json.id, folder_name: hits[0].json.name || 'LinkedIn-Drafts', _exists: true } }];\n}\nreturn [{ json: { folder_id: '', _exists: false } }];" }, position: [2040, 400] }, output: [{ folder_id: '18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA', _exists: true }] });

const folderExistsIf = ifElse({ version: 2.3, config: { name: 'Folder Exists?', parameters: { conditions: { combinator: 'and', options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 }, conditions: [{ leftValue: expr('{{ $json._exists }}'), rightValue: true, operator: { type: 'boolean', operation: 'true' } }] } }, position: [2240, 400] } });

// === Create Drafts Folder (only fires on first run when folder is missing) ===
const createDraftsFolder = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Create Drafts Folder', parameters: { resource: 'folder', operation: 'create', name: DRAFTS_FOLDER_NAME, driveId: { __rl: true, mode: 'list', value: 'My Drive' }, folderId: { __rl: true, mode: 'id', value: MARKETING_PARENT_ID }, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, position: [2440, 250] }, output: [{ id: 'newFolderId', name: 'LinkedIn-Drafts' }] });

// === Encode Draft File — build .txt content + binary, attach folder_id =======
const encodeDraftFile = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Encode Draft File', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const item = $input.first();\nconst j = (item && item.json) ? item.json : {};\nconst folder_id = j.folder_id || j.id || '';\nconst meta = $('Parse Draft').first().json;\nconst dayMeta = $('Day Router').first().json;\nconst body = (meta.post_body || '');\nconst hashtags = Array.isArray(meta.hashtags) ? meta.hashtags : [];\nconst rationale = meta.rationale || '';\nconst draftText = body + '\\n\\n--- HASHTAGS ---\\n' + (hashtags.map(h => '#' + h).join(' ')) + '\\n\\n--- RATIONALE ---\\n' + rationale + '\\n\\n--- META ---\\nangle: ' + (dayMeta.angle || '') + '\\ndate: ' + (dayMeta.date_str || '') + '\\nchar_count: ' + (meta.char_count || 0) + '\\n';\nconst fileName = dayMeta.draft_file_name || ('linkedin-draft-' + new Date().toISOString().slice(0,10) + '.txt');\nreturn [{ json: { folder_id: folder_id, file_name: fileName, char_count: meta.char_count || 0, hashtags_str: meta.hashtags_str || '', angle: dayMeta.angle || '', day_of_week: dayMeta.day_of_week || '' }, binary: { data: { data: Buffer.from(draftText, 'utf8').toString('base64'), mimeType: 'text/plain', fileName: fileName, fileExtension: 'txt' } } }];" }, position: [2640, 400] }, output: [{ folder_id: '18lE3nJy5d2Y4U86tDsrDSrS7muJ3ytiA', file_name: '2026-04-28-build-in-public.txt', char_count: 1024 }] });

// === Save Draft TXT (Drive upload) ==========================================
const saveDraft = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Save Draft TXT', parameters: { resource: 'file', operation: 'upload', inputDataFieldName: 'data', name: '={{ $json.file_name }}', driveId: { __rl: true, mode: 'list', value: 'My Drive' }, folderId: { __rl: true, mode: 'id', value: '={{ $json.folder_id }}' }, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [2840, 400] }, output: [{ id: 'newDraftFileId', name: '2026-04-28-build-in-public.txt', webViewLink: 'https://drive.google.com/file/d/newDraftFileId/view' }] });

// === Shape Log Row ==========================================================
const shapeLogRow = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Shape Log Row', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "function safeFirstJson(name){ try { return ($(name).first() || {}).json || {}; } catch(e){ return {}; } }\nconst driveResp = (($input.first() || {}).json) || {};\nconst meta = safeFirstJson('Parse Draft');\nconst dayMeta = safeFirstJson('Day Router');\nconst encodeMeta = safeFirstJson('Encode Draft File');\nconst drive_file_id = driveResp.id || '';\nconst webViewLink = driveResp.webViewLink || (drive_file_id ? ('https://drive.google.com/file/d/' + drive_file_id + '/view') : '');\nconst saveOk = !!drive_file_id;\nconst status = saveOk ? 'success' : 'drive_upload_failed';\nconst errorMsg = saveOk ? '' : ('drive: ' + String(driveResp.message || driveResp.error || JSON.stringify(driveResp).slice(0, 200) || 'no_id_returned'));\nreturn [{ json: { timestamp: new Date().toISOString(), day_of_week: dayMeta.day_of_week || encodeMeta.day_of_week || '', angle: dayMeta.angle || encodeMeta.angle || '', status: status, draft_url: webViewLink, char_count: String(meta.char_count || encodeMeta.char_count || 0), hashtags: meta.hashtags_str || encodeMeta.hashtags_str || '', error: errorMsg } }];" }, position: [3040, 400] }, output: [{ status: 'success' }] });

// === Append Log Row =========================================================
const appendLogRow = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Append Log Row', parameters: { resource: 'sheet', operation: 'append', documentId: { __rl: true, mode: 'id', value: LINKEDIN_DRAFTS_LOG_SHEET_ID }, sheetName: { __rl: true, mode: 'name', value: LINKEDIN_DRAFTS_LOG_TAB }, columns: { mappingMode: 'autoMapInputData', value: null, matchingColumns: [], schema: [], attemptToConvertTypes: false, convertFieldsToString: true }, options: { useAppend: true, handlingExtraData: 'ignoreIt' } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [3240, 400] }, output: [{ ok: true }] });

// === Topology ===============================================================
export default workflow('grp-linkedin-content-drafter', 'GRP - LinkedIn Content Drafter (Mon/Wed/Fri)')
  .add(trig)
  .to(dayRouter)
  .to(setBrandVoice)
  .to(readCompetitorChangelog)
  .to(readListenerLog)
  .to(composeContext)
  .to(draftPost)
  .to(parseDraft)
  .to(findDraftsFolder)
  .to(resolveFolderId)
  .to(folderExistsIf
    .onTrue(encodeDraftFile)
    .onFalse(createDraftsFolder.to(encodeDraftFile))
  )
  .add(encodeDraftFile)
  .to(saveDraft)
  .to(shapeLogRow)
  .to(appendLogRow);
