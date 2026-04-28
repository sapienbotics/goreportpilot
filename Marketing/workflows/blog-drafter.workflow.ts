// Canonical source for n8n workflow: GRP - Weekly Blog Drafter (Monday)
// Workflow ID: 4XQjZ38p8O4FJPnd
//
// Drafts 1 long-form blog post per week (1500-2500 words) for goreportpilot.com.
// Saurabh reviews + publishes manually. SEO-focused: target keyword in title +
// first paragraph + at least one H2, FAQ section with 3 Q&As, internal-link
// suggestions, slug, meta description.
//
// Schedule: Every Monday 09:00 IST (cron 0 30 3 * * 1 UTC)
//
// Topic source priority:
//   1. Read Blog-Topic-Pipeline sheet, pick first row with status=queued (oldest first)
//   2. If none queued → OpenAI generates a topic from competitor changelog gaps
//      + keyword themes (agency reporting, GA4, white-label, client retention)
//
// Output:
//   - .md draft saved to Blog-Drafts/{YYYY-MM-DD}-{slug}.md in Drive (folder
//     auto-created on first run)
//   - Topic Pipeline row updated to status=drafted with draft_url + scheduled_date
//     (only if the topic came from a queued row)
//   - One row appended to Blog-Drafts-Log per run
//
// Pre-launch: Saurabh creates Blog-Topic-Pipeline + Blog-Drafts-Log sheets in
// GoReportPilot-Marketing folder, sends IDs. Until then, placeholder IDs make
// the Sheets reads/writes fail gracefully (onError continueRegularOutput).
//
// Patterns follow RUNBOOK conventions (brand voice hardcoded — WF7 lesson;
// Drive folder lookup operation=search + searchMethod=query — WF7 lesson;
// all jsCode as single double-quoted strings with \n; one log row per run).

import { workflow, node, trigger, ifElse, newCredential, expr } from '@n8n/workflow-sdk';

// === Resource IDs ============================================================
const MARKETING_PARENT_ID = '1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj';
const COMPETITOR_CHANGELOG_ID = '10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM';
const COMPETITOR_CHANGELOG_TAB = 'Competitor-Changelog';
const BLOG_DRAFTS_FOLDER_NAME = 'Blog-Drafts';

const BLOG_TOPIC_PIPELINE_SHEET_ID = '1x88g1kgDgB_pED4vw9uPiYdx4h9GtWYG_E1Lf9320sw';
const BLOG_TOPIC_PIPELINE_TAB = 'Blog-Topic-Pipeline';
const BLOG_DRAFTS_LOG_SHEET_ID = '1BLmo6KLQapMQDX1detDg8b1VbKzq8-SQr2N7OpflnR4';
const BLOG_DRAFTS_LOG_TAB = 'Blog-Drafts-Log';

// === Brand voice (synced from Marketing/context/brand-voice.md) ==============
// Source-of-truth lives here in this SDK. Set Brand Voice node feeds the prompt.
// To update: edit BRAND_VOICE + update_workflow + publish_workflow.
// (WF7 v2 lesson: Drive download path returns 6-byte stub due to filesystem
// binaryMode. Hardcoding bypasses that entirely.)
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

## Founder context (one-line bio for any time we sign off)

Saurabh Singh, founder of GoReportPilot. Bareilly, India. Built it after spending too many late nights stitching together GA4 + Meta Ads + Google Ads exports for client reports.

## Differentiator we lean on

Most reporting tools (AgencyAnalytics, Whatagraph) charge by report volume — the more you report, the more you pay. We charge by client count: Starter 2 / Pro 10 / Agency 50 clients, unlimited reports per client. This matters most for agencies running weekly cadences — they're the ones the volume-based pricing punishes. Mention this only when it's actually relevant to the prospect, not as a boilerplate line.
`;

// === Trigger =================================================================
const trig = trigger({ type: 'n8n-nodes-base.scheduleTrigger', version: 1.3, config: { name: 'Monday 9AM IST', parameters: { rule: { interval: [{ field: 'cronExpression', expression: '0 30 3 * * 1' }] } }, position: [240, 400] }, output: [{ 'Day of week': 'Monday', timestamp: '2026-04-28T03:30:00.000Z' }] });

// === Day Meta — emit dateStr for filenames + log =============================
const dayMeta = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Day Meta', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const istNow = new Date(new Date().getTime() + (5.5 * 60 * 60 * 1000));\nconst dateStr = istNow.toISOString().slice(0, 10);\nconst yearStart = new Date(istNow.getUTCFullYear(), 0, 1);\nconst weekNum = Math.ceil(((istNow.getTime() - yearStart.getTime()) / 86400000 + yearStart.getUTCDay() + 1) / 7);\nreturn [{ json: { date_str: dateStr, week_num: weekNum, year: istNow.getUTCFullYear() } }];" }, position: [440, 400] }, output: [{ date_str: '2026-04-28', week_num: 18, year: 2026 }] });

// === Set Brand Voice =========================================================
const setBrandVoice = node({ type: 'n8n-nodes-base.set', version: 3.4, config: { name: 'Set Brand Voice', parameters: { mode: 'manual', assignments: { assignments: [{ id: 'bv1', name: 'brand_voice', value: BRAND_VOICE, type: 'string' }] }, includeOtherFields: false }, position: [640, 250] }, output: [{ brand_voice: 'Tone: confident, technical...' }] });

// === Read Topic Pipeline =====================================================
const readTopicPipeline = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Read Topic Pipeline', parameters: { resource: 'sheet', operation: 'read', documentId: { __rl: true, mode: 'id', value: BLOG_TOPIC_PIPELINE_SHEET_ID }, sheetName: { __rl: true, mode: 'name', value: BLOG_TOPIC_PIPELINE_TAB }, options: { returnAllMatches: 'returnAllMatches', dataLocationOnSheet: { values: { rangeDefinition: 'detectAutomatically', readRowsUntil: 'lastRowInSheet' } } } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, executeOnce: true, onError: 'continueRegularOutput', position: [840, 250] }, output: [{ topic: 'Why client reporting eats your Sundays', target_keyword: 'client reporting automation', status: 'queued', scheduled_date: '', draft_url: '', published_url: '', notes: '' }] });

// === Read Competitor Changelog (last 14 days, filtered in Compose Context) ===
const readCompetitorChangelog = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Read Competitor Changelog', parameters: { resource: 'sheet', operation: 'read', documentId: { __rl: true, mode: 'id', value: COMPETITOR_CHANGELOG_ID }, sheetName: { __rl: true, mode: 'name', value: COMPETITOR_CHANGELOG_TAB }, options: { returnAllMatches: 'returnAllMatches', dataLocationOnSheet: { values: { rangeDefinition: 'detectAutomatically', readRowsUntil: 'lastRowInSheet' } } } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, executeOnce: true, onError: 'continueRegularOutput', position: [1040, 250] }, output: [{ date: '2026-04-25', competitor: 'AgencyAnalytics', page: '/pricing', summary: 'Added Enterprise tier', status: 'changed' }] });

// === Pick or Decide Topic ====================================================
// Reads Topic Pipeline output. Picks first queued row (oldest first, preserved
// by sheet order). Extracts published titles for the AI to avoid duplicates.
// If no queued rows → flag _needs_generation=true to trigger fallback OpenAI.
// Builds competitor_summary + published_summary inline so Generate Topic (in
// the onTrue branch) has them available without depending on Compose Context
// (which only runs after the merge).
const pickOrDecideTopic = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Pick or Decide Topic', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "function safeAll(name) { try { return $(name).all() || []; } catch(e) { return []; } }\nconst rows = safeAll('Read Topic Pipeline').map(it => (it && it.json) ? it.json : {}).filter(r => r && (r.topic || r.target_keyword));\nconst queued = rows.filter(r => String(r.status || '').toLowerCase().trim() === 'queued');\nconst published = rows.filter(r => String(r.status || '').toLowerCase().trim() === 'published');\nconst publishedTitles = published.map(r => String(r.topic || '').trim()).filter(Boolean).slice(0, 30);\nconst publishedSummary = publishedTitles.length === 0 ? '(no previously published posts)' : publishedTitles.map((t, i) => (i + 1) + '. ' + t).join('\\n');\nconst competitorRows = safeAll('Read Competitor Changelog').map(it => (it && it.json) ? it.json : {});\nconst fourteenDaysAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);\nconst competitorRecent = competitorRows.filter(r => {\n  const st = String(r.status || '').toLowerCase();\n  if (st && st !== 'changed') return false;\n  const d = new Date(r.date || r.timestamp);\n  return !isNaN(d.getTime()) && d > fourteenDaysAgo;\n});\nconst competitorSummary = competitorRecent.length === 0 ? '(no competitor changes in last 14 days)' : competitorRecent.slice(0, 6).map((r, i) => (i + 1) + '. [' + (r.competitor || 'unknown') + '] ' + String(r.summary || '').slice(0, 180)).join('\\n');\nconst base = { published_titles: publishedTitles, published_summary: publishedSummary, competitor_summary: competitorSummary };\nif (queued.length > 0) {\n  const pick = queued[0];\n  return [{ json: { ...base, topic: String(pick.topic || '').trim(), target_keyword: String(pick.target_keyword || '').trim(), notes: String(pick.notes || '').trim(), _has_queued: true, _queued_lookup_topic: String(pick.topic || '').trim(), _needs_generation: false } }];\n}\nreturn [{ json: { ...base, topic: '', target_keyword: '', notes: '', _has_queued: false, _queued_lookup_topic: '', _needs_generation: true } }];" }, position: [1240, 400] }, output: [{ topic: 'Why client reporting eats your Sundays', target_keyword: 'client reporting automation', _has_queued: true, _needs_generation: false, published_titles: [], competitor_summary: '...', published_summary: '...' }] });

// === Needs Generation? IF ====================================================
const needsGenerationIf = ifElse({ version: 2.3, config: { name: 'Needs Generation?', parameters: { conditions: { combinator: 'and', options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 }, conditions: [{ leftValue: expr('{{ $json._needs_generation }}'), rightValue: true, operator: { type: 'boolean', operation: 'true' } }] } }, position: [1440, 400] } });

// === Generate Topic (OpenAI gpt-4o-mini, only fires when no queued rows) =====
// BUG 3 FIX (exec 17735): rewritten to enforce EDUCATIONAL/teach-not-sell focus
// with explicit banned + good topic patterns and concrete examples. Previous
// prompt allowed product-pitch titles like "Automate Client Reporting with X".
const generateTopicSystemPrompt = "You are an SEO content strategist generating EDUCATIONAL blog topics for an audience of digital marketing agency founders and operators.\n\nThe topic must TEACH the reader something useful, not sell. GoReportPilot (a B2B SaaS that automates agency client reporting — pulls GA4, Meta Ads, Google Ads, Search Console; AI-narrated PPTX/PDF) can be mentioned later in the post as ONE example among others, but it is NEVER the subject of the title or post.\n\nBANNED TOPIC PATTERNS (never propose these):\n- 'How GoReportPilot does X'\n- 'Why choose GoReportPilot'\n- 'Automate <anything> with GoReportPilot'\n- 'GoReportPilot vs <competitor>'\n- Anything that puts the product name or 'automate with' in the title\n\nGOOD TOPIC PATTERNS (use any of these structures):\n- 'How to <achieve a specific agency outcome>'\n- 'N strategies for <agency problem>'\n- 'Why <industry shift / metric / mistake> matters'\n- 'Beginner's guide to <topic>'\n- 'The N <items> every <role> should <action>'\n- '<Specific metric / setup / decision> for <audience>'\n\nEXAMPLES:\n✓ GOOD: '5 GA4 Metrics That Matter More Than Sessions for Agencies'\n✓ GOOD: 'How to Build a White-Label Client Report in Under 30 Minutes'\n✓ GOOD: 'Why Weekly Client Check-ins Outperform Monthly Reports'\n✗ BAD: 'Automate Client Reporting with GoReportPilot'\n✗ BAD: 'Why GoReportPilot Beats AgencyAnalytics'\n✗ BAD: 'Streamline Your Agency Workflow with GoReportPilot'\n\nThemes to pick from: agency reporting workflows, GA4 setup/insights, white-label client deliverables, client retention through reporting, ROI demonstration, marketing analytics tooling, agency operations.\n\nThe topic must be:\n- Specific (not 'How to do X' but 'The 3 GA4 metrics agencies should put in client reports first')\n- Search-relevant (target_keyword should be 2-4 words a real agency person would type into Google)\n- Not on the avoid list (already-published titles passed in user message)\n\nOUTPUT — strict JSON only, no markdown fences:\n{\"topic\": \"the editorial blog post title\", \"target_keyword\": \"2-4 word search phrase\", \"rationale\": \"one sentence on why this is worth writing now\"}";

const generateTopicUserPrompt = "Avoid these recently-published titles:\n{{ $json.published_summary }}\n\nFresh angles from the last 14 days of competitor changes (use for counter-narrative or gap-spotting):\n{{ $json.competitor_summary }}\n\nGenerate ONE topic.";

const generateTopic = node({ type: '@n8n/n8n-nodes-langchain.openAi', version: 2.1, config: { name: 'Generate Topic', parameters: { resource: 'text', operation: 'response', modelId: { __rl: true, mode: 'id', value: 'gpt-4o-mini' }, responses: { values: [{ type: 'text', role: 'system', content: generateTopicSystemPrompt }, { type: 'text', role: 'user', content: expr(generateTopicUserPrompt) }] }, simplify: true, options: { maxTokens: 300, temperature: 0.5, textFormat: { textOptions: [{ type: 'json_object' }] } } }, credentials: { openAiApi: newCredential('OpenAI') }, position: [1640, 250] }, output: [{ content: '{"topic": "The 3 GA4 events agencies should set up before client onboarding", "target_keyword": "GA4 client onboarding", "rationale": "Agencies frequently scramble to wire GA4 events post-launch."}' }] });

// BUG 1 FIX (exec 17735): Generate Topic returns the gpt-4o-mini Responses API
// shape: { output: [{ content: [{ text: "<json>" }] }] }. The previous code
// missed the Array.isArray(j.output) branch and JSON.parse succeeded on the
// outer envelope (no topic field), leaving topic=''. Now mirrors WF7's
// Parse Draft defensive pattern: walks output[].content[].text, JSON.parse
// with regex fallback, falls back to pick.topic if truly empty.
const parseGenTopic = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Parse Generated Topic', parameters: { mode: 'runOnceForEachItem', language: 'javaScript', jsCode: "const j = $input.item.json || {};\nlet raw = '';\nif (typeof j === 'string') raw = j;\nelse if (typeof j.content === 'string') raw = j.content;\nelse if (typeof j.text === 'string') raw = j.text;\nelse if (typeof j.output_text === 'string') raw = j.output_text;\nelse if (typeof j.output === 'string') raw = j.output;\nelse if (j.message && typeof j.message.content === 'string') raw = j.message.content;\nelse if (Array.isArray(j.output)) {\n  for (const o of j.output) {\n    const cs = Array.isArray(o.content) ? o.content : (o.content ? [o.content] : []);\n    for (const c of cs) { if (c && typeof c.text === 'string') raw += c.text; }\n  }\n}\nif (!raw) raw = JSON.stringify(j);\nlet parsed = null;\ntry { parsed = JSON.parse(raw); } catch(e) { const m = raw.match(/\\{[\\s\\S]*\\}/); if (m) { try { parsed = JSON.parse(m[0]); } catch(_) {} } }\nif (!parsed || typeof parsed !== 'object') parsed = {};\nconst pick = $('Pick or Decide Topic').first().json;\nconst topic = String(parsed.topic || '').trim();\nconst target_keyword = String(parsed.target_keyword || '').trim();\nconst rationale = String(parsed.rationale || '').trim();\nreturn { ...pick, topic: topic || pick.topic || '', target_keyword: target_keyword || pick.target_keyword || '', notes: rationale || pick.notes || '', _generated_topic: true };" }, position: [1840, 250] }, output: [{ topic: '...', target_keyword: '...', _has_queued: false, _generated_topic: true }] });

// === Compose Context (merge point — both branches lead here) =================
const composeContext = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Compose Context', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "function safeAll(name) { try { return $(name).all() || []; } catch(e) { return []; } }\nfunction safeFirstJson(name) { try { return ($(name).first() || {}).json || {}; } catch(e) { return {}; } }\nfunction parseDate(v) { if (!v) return null; const d = new Date(v); return isNaN(d.getTime()) ? null : d; }\nconst inputJ = (($input.first() || {}).json) || {};\nconst topic = String(inputJ.topic || '').trim();\nconst target_keyword = String(inputJ.target_keyword || '').trim();\nconst published_titles = Array.isArray(inputJ.published_titles) ? inputJ.published_titles : [];\nconst _has_queued = !!inputJ._has_queued;\nconst _queued_lookup_topic = String(inputJ._queued_lookup_topic || '').trim();\nconst dayMeta = safeFirstJson('Day Meta');\nconst brandVoice = String(safeFirstJson('Set Brand Voice').brand_voice || '');\nconst competitorRows = safeAll('Read Competitor Changelog').map(it => (it && it.json) ? it.json : {});\nconst fourteenDaysAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);\nconst competitorRecent = competitorRows.filter(r => {\n  const status = String(r.status || '').toLowerCase();\n  if (status && status !== 'changed') return false;\n  const d = parseDate(r.date || r.timestamp);\n  return d && d > fourteenDaysAgo;\n});\nconst competitorBlock = competitorRecent.length === 0 ? '(no competitor changes detected in the last 14 days)' : competitorRecent.slice(0, 12).map((r, i) => (i + 1) + '. [' + (r.competitor || 'unknown') + ' ' + (r.page || '') + '] ' + String(r.summary || '').slice(0, 220)).join('\\n');\nconst publishedBlock = published_titles.length === 0 ? '(no previously published posts)' : published_titles.map((t, i) => (i + 1) + '. ' + t).join('\\n');\nreturn [{ json: { ...dayMeta, topic: topic, target_keyword: target_keyword, _has_queued: _has_queued, _queued_lookup_topic: _queued_lookup_topic, brand_voice: brandVoice.slice(0, 4000), competitor_block: competitorBlock, published_block: publishedBlock, competitor_count: competitorRecent.length, published_count: published_titles.length } }];" }, position: [2040, 400] }, output: [{ date_str: '2026-04-28', topic: '...', target_keyword: '...', brand_voice: '...', competitor_block: '...', published_block: '...' }] });

// === Two-stage drafting ======================================================
// Single-prompt drafting hit 671 words on exec 17740 despite explicit minimums
// (gpt-4o "agreed" to the rules but didn't honor them). Two-stage forces the
// model to commit to structure first (5-7 H2s × 3-4 H3s) and then expand each
// pre-defined slot, which is far more reliable for hitting 1500+ words.

// === Stage 1: Generate Outline (gpt-4o, low cost — short response) ===========
const outlineSystemPrompt = "You write detailed blog post outlines for goreportpilot.com (B2B SaaS, automates agency client reporting). For the given topic and target_keyword, produce:\n- 1 intro brief (one sentence on the hook)\n- 5-7 H2 sections, each with 3-4 H3 subsections\n- Each H2 has a brief sentence on what it covers\n- Each H3 has a title + a brief sentence\n- 1 conclusion brief\n\nThe structure must support a 1800-2500 word post when expanded — H2s should be substantive enough that 250-400 words of prose each will fit naturally.\n\nKeep H2s editorial and specific (e.g. 'Why GA4's session count misleads agencies' not 'GA4 metrics'). Each H3 should drill into one concrete sub-aspect.\n\nOUTPUT — strict JSON only, no markdown fences:\n{\"intro_brief\": \"one sentence\", \"sections\": [{\"h2\": \"H2 title\", \"h3s\": [{\"title\": \"H3 title\", \"brief\": \"one sentence on what to cover\"}]}], \"conclusion_brief\": \"one sentence\"}";

const outlineUserPrompt = "TOPIC: {{ $json.topic }}\nTARGET KEYWORD: {{ $json.target_keyword }}\n\nBRAND VOICE NOTES (for tone — full version goes to Stage 2):\n{{ $json.brand_voice }}\n\nGenerate the outline. 5-7 H2 sections, 3-4 H3s each. Output strict JSON.";

const generateOutline = node({ type: '@n8n/n8n-nodes-langchain.openAi', version: 2.1, config: { name: 'Generate Outline', parameters: { resource: 'text', operation: 'response', modelId: { __rl: true, mode: 'id', value: 'gpt-4o' }, responses: { values: [{ type: 'text', role: 'system', content: outlineSystemPrompt }, { type: 'text', role: 'user', content: expr(outlineUserPrompt) }] }, simplify: true, options: { maxTokens: 1500, temperature: 0.4, textFormat: { textOptions: [{ type: 'json_object' }] } } }, credentials: { openAiApi: newCredential('OpenAI') }, position: [2240, 400] }, output: [{ content: '{"intro_brief": "...", "sections": [{"h2": "...", "h3s": [{"title":"...","brief":"..."}]}], "conclusion_brief": "..."}' }] });

// === Parse Outline — converts outline JSON to a prompt-ready text block ======
// Uses the WF7-style defensive parse (handles output[].content[].text shape).
// Spreads Compose Context data so the next prompt has topic, brand_voice, etc.
const parseOutline = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Parse Outline', parameters: { mode: 'runOnceForEachItem', language: 'javaScript', jsCode: "const j = $input.item.json || {};\nlet raw = '';\nif (typeof j === 'string') raw = j;\nelse if (typeof j.content === 'string') raw = j.content;\nelse if (typeof j.text === 'string') raw = j.text;\nelse if (typeof j.output_text === 'string') raw = j.output_text;\nelse if (typeof j.output === 'string') raw = j.output;\nelse if (j.message && typeof j.message.content === 'string') raw = j.message.content;\nelse if (Array.isArray(j.output)) {\n  for (const o of j.output) { const cs = Array.isArray(o.content) ? o.content : (o.content ? [o.content] : []); for (const c of cs) { if (c && typeof c.text === 'string') raw += c.text; } }\n}\nif (!raw) raw = JSON.stringify(j);\nlet parsed = null;\ntry { parsed = JSON.parse(raw); } catch(e) { const m = raw.match(/\\{[\\s\\S]*\\}/); if (m) { try { parsed = JSON.parse(m[0]); } catch(_) {} } }\nif (!parsed || typeof parsed !== 'object') parsed = { intro_brief: '', sections: [], conclusion_brief: '' };\nconst sections = Array.isArray(parsed.sections) ? parsed.sections : [];\nconst introBrief = String(parsed.intro_brief || '').trim();\nconst conclBrief = String(parsed.conclusion_brief || '').trim();\nconst lines = [];\nlines.push('# OUTLINE');\nlines.push('');\nlines.push('## INTRO');\nlines.push('Brief: ' + introBrief);\nlines.push('Target length: 80-150 words');\nlines.push('');\nfor (let i = 0; i < sections.length; i++) {\n  const s = sections[i] || {};\n  lines.push('## H2 #' + (i + 1) + ': ' + (s.h2 || ''));\n  lines.push('Target length: 250-400 words across all H3s in this section');\n  const h3s = Array.isArray(s.h3s) ? s.h3s : [];\n  for (let k = 0; k < h3s.length; k++) {\n    const h3 = h3s[k] || {};\n    lines.push('  ### H3: ' + (h3.title || ''));\n    lines.push('  Brief: ' + (h3.brief || ''));\n    lines.push('  Target length: 80-150 words');\n  }\n  lines.push('');\n}\nlines.push('## CONCLUSION');\nlines.push('Brief: ' + conclBrief);\nlines.push('Target length: 80-150 words');\nconst outlineText = lines.join('\\n');\nconst meta = $('Compose Context').first().json;\nconst h3Count = sections.reduce((n, s) => n + (Array.isArray(s.h3s) ? s.h3s.length : 0), 0);\nreturn { ...meta, outline_text: outlineText, outline_section_count: sections.length, outline_h3_count: h3Count };" }, position: [2440, 400] }, output: [{ outline_text: '# OUTLINE\\n\\n## INTRO...', outline_section_count: 6, outline_h3_count: 18 }] });

// === Stage 2: Expand To Draft (gpt-4o, maxTokens 12000) ======================
// Receives the outline + topic + target_keyword + brand voice + competitor block
// + already-published list. Expands every brief into prose with strict per-H2
// and per-H3 word minimums. Produces the final {title, meta, slug, body, faqs}.
const expandSystemPrompt = "You expand a blog outline into a full SEO-optimized post for goreportpilot.com (B2B SaaS, automates agency client reporting — pulls GA4, Meta Ads, Google Ads, Search Console; AI-narrated PPTX/PDF). Saurabh Singh writes as a builder in public, founder voice.\n\nThe outline below is NON-NEGOTIABLE STRUCTURE. Expand every brief into prose. Do not skip sections, do not collapse them, do not reorder them.\n\nWORD COUNT (CRITICAL — non-negotiable):\n- EACH H2 section: 250-400 words across its H3s. Sections under 250 words will be rejected.\n- EACH H3 subsection: 80-150 words.\n- Intro paragraph: 80-150 words.\n- Conclusion paragraph: 80-150 words.\n- Total target: 1800-2500 words in body_markdown.\n- Count your words before submitting. If total is under 1500, expand the thinnest H3s with concrete examples, mini case scenarios (e.g. 'A 12-client agency in Austin spent 6 hours/week on...'), specific numbers, or step-by-step walkthroughs.\n\nVOICE: confident, technical, direct, zero fluff. Sound like a founder who used to spend 6 hours a month making client reports and got fed up.\n\nBANNED PHRASES (never use, no exceptions): leverage, synergy, in today's fast-paced world, revolutionary, AI-powered, AI-driven, game-changer, seamless, robust, cutting-edge, next-generation, best-in-class, streamlined, transform your, elevate your.\n\nSEO RULES:\n- target_keyword MUST appear in: the title, the first paragraph (within first 100 words), and at least one H2.\n- H2/H3 hierarchy in body_markdown: ## for H2, ### for H3.\n- One natural CTA paragraph somewhere mid-body pointing to https://goreportpilot.com/signup. Frame: 'try it on one client first'. Not pitchy.\n- FAQ section: EXACTLY 3 question/answer pairs at the end (returned in faqs array, NOT in body_markdown).\n- Slug: URL-safe lowercase with hyphens, max 60 chars.\n- Meta description: max 155 characters, includes target_keyword, benefit-led.\n- 3-5 internal_links_suggested to other goreportpilot.com paths (/features, /pricing, /blog/<other-slug>, /signup, /demo).\n\nFORMAT:\n- First paragraph: STATEMENT hook with a concrete number or scenario. NEVER open with a rhetorical question (any sentence ending in '?').\n- Name competitors when relevant (AgencyAnalytics, Whatagraph, Swydo, NinjaCat, Looker Studio).\n- Specific numbers > vague claims.\n- Use mini case scenarios and concrete examples to fill word count, not filler/repetition.\n\nOUTPUT — strict JSON only, no markdown fences around the JSON:\n{\"title\": \"...\", \"meta_description\": \"...\", \"slug\": \"...\", \"body_markdown\": \"...\", \"faqs\": [{\"q\": \"...\", \"a\": \"...\"}, {\"q\": \"...\", \"a\": \"...\"}, {\"q\": \"...\", \"a\": \"...\"}], \"internal_links_suggested\": [\"/features\", \"/pricing\", \"...\"]}";

const expandUserPrompt = "TOPIC: {{ $json.topic }}\nTARGET KEYWORD: {{ $json.target_keyword }}\n\nOUTLINE — non-negotiable structure, expand every brief into prose:\n{{ $json.outline_text }}\n\nRECENT COMPETITOR CHANGES (last 14 days, for counter-narrative or specifics — don't summarize):\n{{ $json.competitor_block }}\n\nPREVIOUSLY PUBLISHED TITLES — do not duplicate angle:\n{{ $json.published_block }}\n\nBRAND VOICE NOTES (authoritative — follow strictly):\n{{ $json.brand_voice }}\n\nExpand the outline. Each H2 must be 250-400 words. Each H3 must be 80-150 words. Total 1800-2500 words. Output strict JSON.";

const expandToDraft = node({ type: '@n8n/n8n-nodes-langchain.openAi', version: 2.1, config: { name: 'Expand To Draft', parameters: { resource: 'text', operation: 'response', modelId: { __rl: true, mode: 'id', value: 'gpt-4o' }, responses: { values: [{ type: 'text', role: 'system', content: expandSystemPrompt }, { type: 'text', role: 'user', content: expr(expandUserPrompt) }] }, simplify: true, options: { maxTokens: 12000, temperature: 0.5, textFormat: { textOptions: [{ type: 'json_object' }] } } }, credentials: { openAiApi: newCredential('OpenAI') }, position: [2640, 400] }, output: [{ content: '{"title": "...", "meta_description": "...", "slug": "...", "body_markdown": "...", "faqs": [{"q":"...","a":"..."}], "internal_links_suggested": ["/features"]}' }] });

// === Parse Draft =============================================================
const parseDraft = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Parse Draft', parameters: { mode: 'runOnceForEachItem', language: 'javaScript', jsCode: "function slugify(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60); }\nconst j = $input.item.json || {};\nlet raw = '';\nif (typeof j === 'string') raw = j;\nelse if (typeof j.content === 'string') raw = j.content;\nelse if (typeof j.text === 'string') raw = j.text;\nelse if (typeof j.output_text === 'string') raw = j.output_text;\nelse if (typeof j.output === 'string') raw = j.output;\nelse if (j.message && typeof j.message.content === 'string') raw = j.message.content;\nelse if (Array.isArray(j.output)) {\n  for (const o of j.output) { const cs = Array.isArray(o.content) ? o.content : (o.content ? [o.content] : []); for (const c of cs) { if (c && typeof c.text === 'string') raw += c.text; } }\n}\nif (!raw) raw = JSON.stringify(j);\nlet parsed = null;\ntry { parsed = JSON.parse(raw); } catch(e) { const m = raw.match(/\\{[\\s\\S]*\\}/); if (m) { try { parsed = JSON.parse(m[0]); } catch(_) {} } }\nif (!parsed || typeof parsed !== 'object') parsed = { title: 'Untitled', meta_description: '', slug: '', body_markdown: raw, faqs: [], internal_links_suggested: [] };\nconst meta = $('Compose Context').first().json;\nconst title = String(parsed.title || 'Untitled').trim();\nconst slug = String(parsed.slug || '').trim() || slugify(title);\nconst meta_description = String(parsed.meta_description || '').trim().slice(0, 200);\nconst body_markdown = String(parsed.body_markdown || '').trim();\nconst word_count = body_markdown.split(/\\s+/).filter(Boolean).length;\nconst faqsArr = Array.isArray(parsed.faqs) ? parsed.faqs.filter(f => f && f.q && f.a).slice(0, 5) : [];\nconst internalLinks = Array.isArray(parsed.internal_links_suggested) ? parsed.internal_links_suggested.map(l => String(l).trim()).filter(Boolean).slice(0, 6) : [];\nconst draftFileName = (meta.date_str || new Date().toISOString().slice(0,10)) + '-' + slugify(slug || title) + '.md';\nreturn { ...meta, title: title, slug: slug, meta_description: meta_description, body_markdown: body_markdown, faqs: faqsArr, internal_links: internalLinks, word_count: word_count, faqs_count: faqsArr.length, draft_file_name: draftFileName };" }, position: [2440, 400] }, output: [{ title: '...', slug: 'why-client-reporting-eats-your-sundays', word_count: 1850, faqs_count: 3, draft_file_name: '2026-04-28-why-client-reporting-eats-your-sundays.md' }] });

// === Find Blog-Drafts Folder (operation=search + searchMethod=query, per WF7) =
const findDraftsFolder = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Find Drafts Folder', parameters: { resource: 'fileFolder', operation: 'search', searchMethod: 'query', queryString: "name = 'Blog-Drafts' and '1IqoA6XJsrm8Iw69-LQ9dbeP3yI6GrARj' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false", returnAll: true, filter: {}, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [2640, 400] }, output: [{ id: 'mockFolderId', name: 'Blog-Drafts' }] });

const resolveFolderId = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Resolve Folder ID', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const items = $input.all();\nconst hits = items.filter(it => it && it.json && it.json.id && (it.json.mimeType === 'application/vnd.google-apps.folder' || !it.json.mimeType));\nif (hits.length > 0) {\n  return [{ json: { folder_id: hits[0].json.id, folder_name: hits[0].json.name || 'Blog-Drafts', _exists: true } }];\n}\nreturn [{ json: { folder_id: '', _exists: false } }];" }, position: [2840, 400] }, output: [{ folder_id: 'mockFolderId', _exists: true }] });

const folderExistsIf = ifElse({ version: 2.3, config: { name: 'Folder Exists?', parameters: { conditions: { combinator: 'and', options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 }, conditions: [{ leftValue: expr('{{ $json._exists }}'), rightValue: true, operator: { type: 'boolean', operation: 'true' } }] } }, position: [3040, 400] } });

const createDraftsFolder = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Create Drafts Folder', parameters: { resource: 'folder', operation: 'create', name: BLOG_DRAFTS_FOLDER_NAME, driveId: { __rl: true, mode: 'list', value: 'My Drive' }, folderId: { __rl: true, mode: 'id', value: MARKETING_PARENT_ID }, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, position: [3240, 250] }, output: [{ id: 'newFolderId', name: 'Blog-Drafts' }] });

// === Encode Draft .md File ===================================================
// Frontmatter + body + FAQ section + suggested internal links. Reads folder_id
// from whichever upstream branch fired (resolveFolderId or createDraftsFolder).
const encodeDraftFile = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Encode Draft MD', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const item = $input.first();\nconst j = (item && item.json) ? item.json : {};\nconst folder_id = j.folder_id || j.id || '';\nconst meta = $('Parse Draft').first().json;\nconst dayMeta = $('Day Meta').first().json;\nconst faqs = Array.isArray(meta.faqs) ? meta.faqs : [];\nconst links = Array.isArray(meta.internal_links) ? meta.internal_links : [];\nconst frontmatter = '---\\ntitle: ' + JSON.stringify(meta.title || '') + '\\nslug: ' + (meta.slug || '') + '\\nmeta_description: ' + JSON.stringify(meta.meta_description || '') + '\\ntarget_keyword: ' + JSON.stringify(meta.target_keyword || '') + '\\ndate_drafted: ' + (dayMeta.date_str || '') + '\\nstatus: drafted\\nword_count: ' + (meta.word_count || 0) + '\\ninternal_links_suggested:\\n' + (links.length ? links.map(l => '  - ' + l).join('\\n') : '  - (none)') + '\\n---\\n\\n';\nconst body = (meta.body_markdown || '');\nconst faqSection = faqs.length === 0 ? '' : ('\\n\\n## FAQ\\n\\n' + faqs.map(f => '### ' + (f.q || '') + '\\n\\n' + (f.a || '')).join('\\n\\n'));\nconst draftText = frontmatter + body + faqSection + '\\n';\nconst fileName = meta.draft_file_name || ((dayMeta.date_str || new Date().toISOString().slice(0,10)) + '-untitled.md');\nreturn [{ json: { folder_id: folder_id, file_name: fileName, title: meta.title, slug: meta.slug, target_keyword: meta.target_keyword, word_count: meta.word_count, faqs_count: meta.faqs_count, _has_queued: !!meta._has_queued, _queued_lookup_topic: meta._queued_lookup_topic || '' }, binary: { data: { data: Buffer.from(draftText, 'utf8').toString('base64'), mimeType: 'text/markdown', fileName: fileName, fileExtension: 'md' } } }];" }, position: [3440, 400] }, output: [{ folder_id: 'mockFolderId', file_name: '2026-04-28-why-client-reporting-eats-your-sundays.md', title: '...', word_count: 1850 }] });

// === Save Draft MD (Drive upload) ============================================
const saveDraft = node({ type: 'n8n-nodes-base.googleDrive', version: 3, config: { name: 'Save Draft MD', parameters: { resource: 'file', operation: 'upload', inputDataFieldName: 'data', name: '={{ $json.file_name }}', driveId: { __rl: true, mode: 'list', value: 'My Drive' }, folderId: { __rl: true, mode: 'id', value: '={{ $json.folder_id }}' }, options: {} }, credentials: { googleDriveOAuth2Api: newCredential('Google Drive') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [3640, 400] }, output: [{ id: 'newDraftFileId', name: '2026-04-28-why-client-reporting-eats-your-sundays.md', webViewLink: 'https://drive.google.com/file/d/newDraftFileId/view' }] });

// === Has Queued Row? IF =====================================================
// Only update the Topic Pipeline row if the topic came from a queued row.
// Generated topics aren't in the pipeline so there's nothing to update.
const hasQueuedRowIf = ifElse({ version: 2.3, config: { name: 'Has Queued Row?', parameters: { conditions: { combinator: 'and', options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 }, conditions: [{ leftValue: expr('{{ $(\"Encode Draft MD\").first().json._has_queued }}'), rightValue: true, operator: { type: 'boolean', operation: 'true' } }] } }, position: [3840, 400] } });

// === Update Topic Pipeline Row (only if queued) ==============================
// Sheets `update` matches by the `topic` column. If Saurabh has duplicate topics
// in the pipeline (e.g. re-queued), this updates the FIRST matching row.
// The row data we send: topic (matching), status=drafted, draft_url, scheduled_date.
const buildUpdateRow = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Build Update Row', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "const driveResp = $input.first().json || {};\nconst encodeMeta = $('Encode Draft MD').first().json;\nconst dayMeta = $('Day Meta').first().json;\nconst drive_file_id = driveResp.id || '';\nconst webViewLink = driveResp.webViewLink || (drive_file_id ? ('https://drive.google.com/file/d/' + drive_file_id + '/view') : '');\nreturn [{ json: { topic: encodeMeta._queued_lookup_topic || encodeMeta.title || '', status: 'drafted', draft_url: webViewLink, scheduled_date: dayMeta.date_str || '' } }];" }, position: [4040, 250] }, output: [{ topic: 'Why client reporting eats your Sundays', status: 'drafted', draft_url: 'https://drive.google.com/...', scheduled_date: '2026-04-28' }] });

const updateTopicRow = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Update Topic Row', parameters: { resource: 'sheet', operation: 'update', documentId: { __rl: true, mode: 'id', value: BLOG_TOPIC_PIPELINE_SHEET_ID }, sheetName: { __rl: true, mode: 'name', value: BLOG_TOPIC_PIPELINE_TAB }, columns: { mappingMode: 'autoMapInputData', value: null, matchingColumns: ['topic'], schema: [], attemptToConvertTypes: false, convertFieldsToString: true }, options: { handlingExtraData: 'ignoreIt' } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [4240, 250] }, output: [{ ok: true }] });

// === Shape Log Row (merge point — both branches converge here) ===============
const shapeLogRow = node({ type: 'n8n-nodes-base.code', version: 2, config: { name: 'Shape Log Row', parameters: { mode: 'runOnceForAllItems', language: 'javaScript', jsCode: "function safeFirstJson(name){ try { return ($(name).first() || {}).json || {}; } catch(e){ return {}; } }\nconst saveResp = safeFirstJson('Save Draft MD');\nconst meta = safeFirstJson('Parse Draft');\nconst dayMeta = safeFirstJson('Day Meta');\nconst encodeMeta = safeFirstJson('Encode Draft MD');\nconst drive_file_id = saveResp.id || '';\nconst webViewLink = saveResp.webViewLink || (drive_file_id ? ('https://drive.google.com/file/d/' + drive_file_id + '/view') : '');\nconst saveOk = !!drive_file_id;\nlet status = 'success';\nlet errorMsg = '';\nif (!saveOk) { status = 'drive_upload_failed'; errorMsg = 'drive: ' + String(saveResp.message || saveResp.error || 'no_id_returned'); }\nreturn [{ json: { timestamp: new Date().toISOString(), topic: meta.topic || encodeMeta.title || '', target_keyword: meta.target_keyword || '', slug: meta.slug || '', word_count: String(meta.word_count || 0), status: status, draft_url: webViewLink, faqs_count: String(meta.faqs_count || 0), error: errorMsg } }];" }, position: [4440, 400] }, output: [{ timestamp: '2026-04-28T03:30:00Z', topic: '...', target_keyword: '...', slug: '...', word_count: '1850', status: 'success', draft_url: '...', faqs_count: '3', error: '' }] });

// === Append Log Row ==========================================================
const appendLogRow = node({ type: 'n8n-nodes-base.googleSheets', version: 4.7, config: { name: 'Append Log Row', parameters: { resource: 'sheet', operation: 'append', documentId: { __rl: true, mode: 'id', value: BLOG_DRAFTS_LOG_SHEET_ID }, sheetName: { __rl: true, mode: 'name', value: BLOG_DRAFTS_LOG_TAB }, columns: { mappingMode: 'autoMapInputData', value: null, matchingColumns: [], schema: [], attemptToConvertTypes: false, convertFieldsToString: true }, options: { useAppend: true, handlingExtraData: 'ignoreIt' } }, credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') }, alwaysOutputData: true, onError: 'continueRegularOutput', position: [4640, 400] }, output: [{ ok: true }] });

// === Topology ===============================================================
export default workflow('grp-blog-drafter', 'GRP - Weekly Blog Drafter (Monday)')
  .add(trig)
  .to(dayMeta)
  .to(setBrandVoice)
  .to(readTopicPipeline)
  .to(readCompetitorChangelog)
  .to(pickOrDecideTopic)
  .to(needsGenerationIf
    .onTrue(generateTopic.to(parseGenTopic).to(composeContext))
    .onFalse(composeContext)
  )
  .add(composeContext)
  .to(generateOutline)
  .to(parseOutline)
  .to(expandToDraft)
  .to(parseDraft)
  .to(findDraftsFolder)
  .to(resolveFolderId)
  .to(folderExistsIf
    .onTrue(encodeDraftFile)
    .onFalse(createDraftsFolder.to(encodeDraftFile))
  )
  .add(encodeDraftFile)
  .to(saveDraft)
  .to(hasQueuedRowIf
    .onTrue(buildUpdateRow.to(updateTopicRow).to(shapeLogRow))
    .onFalse(shapeLogRow)
  )
  .add(shapeLogRow)
  .to(appendLogRow);
