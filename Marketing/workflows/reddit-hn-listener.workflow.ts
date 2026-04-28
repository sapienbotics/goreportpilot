// Canonical source for n8n workflow: GRP - Reddit HN Listener (2x Daily)
// Workflow ID: lYCSDKm6vTw7W9wi
// Active version verified: 40adaf83-c8e5-4ed5-846f-2d1194ff570b (2026-04-27 — text-mode + try/catch JSON.parse fix)
//
// IMPORTANT: Fetch HN + Reddit uses responseFormat='text' (not 'json'). Reasoning:
// n8n HTTP Request v4.4 throws on JSON parse failure BEFORE applying neverError,
// so a Reddit anti-bot HTML response would crash the run. With text mode the body
// arrives as a string in $json.body, and Normalize Results JSON.parses it inside
// try/catch — non-JSON sources (Reddit blocks) become empty results and increment
// parse_failures, surfaced in the Listener-Log errors column.
//
// Twice daily (08:00 + 19:00 IST = 02:30 + 13:30 UTC). Searches HN Algolia + Reddit
// JSON across 8 ICP keywords × (HN + 7-subreddit multi-search) = 16 HTTP requests.
// Combines + dedupes, batch-scores via gpt-4o-mini in ONE call (cost optimization),
// filters score >= 7, saves each qualifying post as a .txt comment-draft in the
// Engage folder, logs run summary to Listener-Log.
//
// To deploy:
//   1. update_workflow(workflowId='lYCSDKm6vTw7W9wi', code=<this file>)
//   2. get_workflow_details — copy the resulting versionId (the draft)
//   3. publish_workflow(workflowId='lYCSDKm6vTw7W9wi', versionId=<that versionId>)
//
// ⛔ Never edit and Save this workflow from the n8n UI — it overwrites this version.

import { workflow, node, trigger, ifElse, splitInBatches, nextBatch, newCredential, expr } from '@n8n/workflow-sdk';

const LISTENER_LOG_ID = '1iXiV_DFS5v7z7LNHcRfJIbQFP2O_K7CfCtjy3Ll0JX0';
const LISTENER_LOG_TAB = 'Listener-Log';
const ENGAGE_FOLDER_ID = '1y-bimMAnsrfCUd0v3CILtAb37xHpUQMy';

const trig = trigger({ type: 'n8n-nodes-base.scheduleTrigger', version: 1.3, config: { name: 'Twice Daily 8AM 7PM IST', parameters: { rule: { interval: [{ field: 'cronExpression', expression: '0 30 2,13 * * *' }] } }, position: [240, 300] }, output: [{ timestamp: '2026-04-26T02:30:00.000Z' }] });

const buildSearchList = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Build Search List',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const keywords = [\n" +
        "  'client reporting', 'looker studio alternative', 'AgencyAnalytics', 'Whatagraph',\n" +
        "  'automate reports', 'white label report', 'agency reporting tool', 'marketing report automation'\n" +
        "];\n" +
        "const subs = ['digital_marketing','PPC','AgencyGrowth','SaaS','SEO','marketing','Entrepreneur'].join('+');\n" +
        "const cutoff = Math.floor(Date.now() / 1000) - 43200;\n" +
        "const out = [];\n" +
        "for (const k of keywords) {\n" +
        "  out.push({ json: { source: 'hn', keyword: k, cutoff: cutoff,\n" +
        "    url: 'http://hn.algolia.com/api/v1/search_by_date?query=' + encodeURIComponent(k) + '&tags=story,comment&numericFilters=created_at_i>' + cutoff } });\n" +
        "  out.push({ json: { source: 'reddit', keyword: k, cutoff: cutoff,\n" +
        "    url: 'https://www.reddit.com/r/' + subs + '/search.json?q=' + encodeURIComponent(k) + '&sort=new&restrict_sr=1&t=day&limit=10' } });\n" +
        "}\n" +
        "return out;"
    },
    position: [440, 300]
  },
  output: [{ source: 'hn', keyword: 'client reporting', cutoff: 1714000000, url: 'http://hn.algolia.com/api/v1/search_by_date?query=client%20reporting&tags=story,comment&numericFilters=created_at_i>1714000000' }]
});

const fetchAll = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Fetch HN + Reddit',
    parameters: {
      method: 'GET',
      url: expr('{{ $json.url }}'),
      sendHeaders: true,
      specifyHeaders: 'keypair',
      headerParameters: {
        parameters: [
          { name: 'User-Agent', value: 'GoReportPilot-Monitor/1.0 (by /u/sapienbotics)' },
          { name: 'Accept', value: 'application/json' }
        ]
      },
      options: {
        response: { response: { responseFormat: 'text', neverError: true, outputPropertyName: 'body' } },
        timeout: 15000,
        redirect: { redirect: { followRedirects: true, maxRedirects: 3 } },
        batching: { batch: { batchSize: 4, batchInterval: 1500 } }
      }
    },
    alwaysOutputData: true,
    position: [640, 300]
  },
  output: [{ body: '{"hits":[{"objectID":"12345","title":"Test post","author":"someone","url":"https://example.com/post","story_text":"About reporting"}]}' }]
});

const normalize = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Normalize Results',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const responses = $input.all();\n" +
        "const inputs = $('Build Search List').all();\n" +
        "const all = [];\n" +
        "const seen = new Set();\n" +
        "let hn_count = 0;\n" +
        "let reddit_count = 0;\n" +
        "let parse_failures = 0;\n" +
        "for (let i = 0; i < responses.length && i < inputs.length; i++) {\n" +
        "  const meta = (inputs[i] && inputs[i].json) ? inputs[i].json : {};\n" +
        "  const respJson = (responses[i] && responses[i].json) ? responses[i].json : {};\n" +
        "  let rawText = '';\n" +
        "  if (typeof respJson === 'string') rawText = respJson;\n" +
        "  else if (typeof respJson.body === 'string') rawText = respJson.body;\n" +
        "  else if (typeof respJson.data === 'string') rawText = respJson.data;\n" +
        "  else if (respJson && (respJson.hits || respJson.data)) { try { rawText = JSON.stringify(respJson); } catch(_) { rawText = ''; } }\n" +
        "  let body = {};\n" +
        "  if (rawText && (rawText.charAt(0) === '{' || rawText.charAt(0) === '[')) {\n" +
        "    try { body = JSON.parse(rawText); } catch(e) { parse_failures++; body = {}; }\n" +
        "  } else if (rawText) {\n" +
        "    parse_failures++;\n" +
        "  }\n" +
        "  if (meta.source === 'hn') {\n" +
        "    const hits = (body && Array.isArray(body.hits)) ? body.hits : [];\n" +
        "    for (const h of hits) {\n" +
        "      const url = h.url || ('https://news.ycombinator.com/item?id=' + h.objectID);\n" +
        "      if (seen.has(url)) continue;\n" +
        "      seen.add(url);\n" +
        "      hn_count++;\n" +
        "      all.push({\n" +
        "        id: 'hn-' + h.objectID,\n" +
        "        source: 'hn',\n" +
        "        keyword: meta.keyword,\n" +
        "        url: url,\n" +
        "        title: String(h.title || h.story_title || (h.comment_text || '').slice(0, 100)).slice(0, 200),\n" +
        "        author: String(h.author || ''),\n" +
        "        snippet: String((h.story_text || h.comment_text || '')).replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ').slice(0, 500),\n" +
        "        subreddit: '',\n" +
        "        points: h.points || 0,\n" +
        "        num_comments: h.num_comments || 0,\n" +
        "        created_at: h.created_at || ''\n" +
        "      });\n" +
        "    }\n" +
        "  } else if (meta.source === 'reddit') {\n" +
        "    const children = (body && body.data && Array.isArray(body.data.children)) ? body.data.children : [];\n" +
        "    for (const c of children) {\n" +
        "      const d = (c && c.data) ? c.data : {};\n" +
        "      const url = 'https://reddit.com' + (d.permalink || '');\n" +
        "      if (seen.has(url) || !d.permalink) continue;\n" +
        "      seen.add(url);\n" +
        "      reddit_count++;\n" +
        "      all.push({\n" +
        "        id: 'reddit-' + (d.id || ''),\n" +
        "        source: 'reddit',\n" +
        "        keyword: meta.keyword,\n" +
        "        url: url,\n" +
        "        title: String(d.title || '').slice(0, 200),\n" +
        "        author: String(d.author || ''),\n" +
        "        snippet: String(d.selftext || '').replace(/\\s+/g, ' ').slice(0, 500),\n" +
        "        subreddit: String(d.subreddit || ''),\n" +
        "        points: d.score || 0,\n" +
        "        num_comments: d.num_comments || 0,\n" +
        "        created_at: d.created_utc ? new Date(d.created_utc * 1000).toISOString() : ''\n" +
        "      });\n" +
        "    }\n" +
        "  }\n" +
        "}\n" +
        "all.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));\n" +
        "const top = all.slice(0, 50);\n" +
        "if (top.length === 0) return [{ json: { _no_posts: true, hn_count: 0, reddit_count: 0, total: 0, posts: [], parse_failures: parse_failures } }];\n" +
        "return [{ json: { _no_posts: false, hn_count: hn_count, reddit_count: reddit_count, total: top.length, posts: top, parse_failures: parse_failures } }];"
    },
    position: [840, 300]
  },
  output: [{ _no_posts: false, hn_count: 5, reddit_count: 8, total: 13, parse_failures: 0, posts: [{ id: 'hn-1', source: 'hn', keyword: 'client reporting', url: 'https://news.ycombinator.com/item?id=1', title: 'Best client reporting tool?', author: 'pm123', snippet: 'Looking for...', subreddit: '', points: 5, num_comments: 12, created_at: '2026-04-26T01:00:00Z' }] }]
});

const hasPosts = ifElse({
  version: 2.3,
  config: {
    name: 'Has Posts?',
    parameters: {
      conditions: {
        combinator: 'and',
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
        conditions: [{
          leftValue: expr('{{ $json._no_posts }}'),
          rightValue: true,
          operator: { type: 'boolean', operation: 'true' }
        }]
      },
      looseTypeValidation: true
    },
    position: [1040, 300]
  }
});

const scoreAll = node({
  type: '@n8n/n8n-nodes-langchain.openAi',
  version: 2.1,
  config: {
    name: 'Score All Posts',
    parameters: {
      resource: 'text',
      operation: 'response',
      modelId: { __rl: true, mode: 'id', value: 'gpt-4o-mini' },
      responses: {
        values: [
          {
            type: 'text',
            role: 'system',
            content: "You evaluate social media posts for engagement potential for GoReportPilot, a B2B SaaS reporting tool for digital marketing agencies (GA4 + Meta Ads + Google Ads + Search Console -> narrated PPTX/PDF reports). For each post in the input array, score 1-10 based on: relevance to agency reporting pain, buying intent signals, engagement potential (recent, active thread), fit to our ICP (agency owners, NOT freelancers/enterprises). Output ONLY a JSON ARRAY: [{\"id\": <post id verbatim>, \"score\": <1-10 integer>, \"reason\": <1 sentence why this score>, \"draft_comment\": <30-60 word value-first reply>}]. For draft_comment: write 30-60 words that ANSWER their question or add value. NEVER pitch GoReportPilot in the opening sentence. Only mention GoReportPilot if directly relevant — phrased as 'I'm building X for this exact problem'. Sound human, not corporate. Disclose founder status if mentioning the product."
          },
          {
            type: 'text',
            role: 'user',
            content: expr('Score these posts. Return one JSON array with the same number of objects as posts, each keyed by id verbatim.\n\nPOSTS:\n{{ JSON.stringify($json.posts) }}')
          }
        ]
      },
      simplify: true,
      options: {
        maxTokens: 4000,
        temperature: 0.2,
        textFormat: { textOptions: [{ type: 'json_object' }] }
      }
    },
    credentials: { openAiApi: newCredential('OpenAI') },
    position: [1240, 400]
  },
  output: [{ content: '[{"id":"hn-1","score":8,"reason":"Direct match for client reporting pain","draft_comment":"For 5+ clients I built a tool that... (founder note)"}]' }]
});

const parseScores = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Parse Scores',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const meta = $('Normalize Results').first().json || {};\n" +
        "const j = $input.first().json || {};\n" +
        "let raw = '';\n" +
        "if (typeof j === 'string') raw = j;\n" +
        "else if (typeof j.content === 'string') raw = j.content;\n" +
        "else if (typeof j.text === 'string') raw = j.text;\n" +
        "else if (typeof j.output_text === 'string') raw = j.output_text;\n" +
        "else if (typeof j.output === 'string') raw = j.output;\n" +
        "else if (j.message && typeof j.message.content === 'string') raw = j.message.content;\n" +
        "else if (Array.isArray(j.output)) {\n" +
        "  for (const o of j.output) {\n" +
        "    const cs = Array.isArray(o.content) ? o.content : (o.content ? [o.content] : []);\n" +
        "    for (const c of cs) { if (c && typeof c.text === 'string') raw += c.text; }\n" +
        "  }\n" +
        "}\n" +
        "if (!raw) raw = JSON.stringify(j);\n" +
        "let parsed = null;\n" +
        "try { parsed = JSON.parse(raw); } catch(e) {\n" +
        "  const m = raw.match(/\\[[\\s\\S]*\\]/);\n" +
        "  if (m) { try { parsed = JSON.parse(m[0]); } catch(_) {} }\n" +
        "}\n" +
        "if (parsed && !Array.isArray(parsed) && Array.isArray(parsed.scores)) parsed = parsed.scores;\n" +
        "if (parsed && !Array.isArray(parsed) && Array.isArray(parsed.results)) parsed = parsed.results;\n" +
        "if (!Array.isArray(parsed)) parsed = [];\n" +
        "const scoreById = {};\n" +
        "for (const s of parsed) {\n" +
        "  if (s && s.id) scoreById[s.id] = s;\n" +
        "}\n" +
        "const enriched = (meta.posts || []).map(p => {\n" +
        "  const s = scoreById[p.id] || {};\n" +
        "  const sc = parseInt(s.score, 10);\n" +
        "  return { ...p, score: isNaN(sc) ? 0 : sc, reason: String(s.reason || 'no score').slice(0, 300), draft_comment: String(s.draft_comment || '').slice(0, 1000) };\n" +
        "});\n" +
        "const qualified = enriched.filter(p => p.score >= 7);\n" +
        "return [{ json: {\n" +
        "  hn_count: meta.hn_count || 0,\n" +
        "  reddit_count: meta.reddit_count || 0,\n" +
        "  total_scored: enriched.length,\n" +
        "  qualified_count: qualified.length,\n" +
        "  qualified: qualified,\n" +
        "  _none_qualified: qualified.length === 0\n" +
        "} }];"
    },
    position: [1440, 400]
  },
  output: [{ hn_count: 5, reddit_count: 8, total_scored: 13, qualified_count: 2, _none_qualified: false, qualified: [{ id: 'hn-1', score: 8, reason: 'Direct match', draft_comment: 'For 5+ clients...', source: 'hn', url: 'https://...', title: 'Best client reporting tool?', keyword: 'client reporting', author: 'pm123', snippet: 'Looking...', subreddit: '', points: 5, num_comments: 12, created_at: '2026-04-26T01:00:00Z' }] }]
});

const hasQualified = ifElse({
  version: 2.3,
  config: {
    name: 'Has Qualified?',
    parameters: {
      conditions: {
        combinator: 'and',
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose', version: 2 },
        conditions: [{
          leftValue: expr('{{ $json._none_qualified }}'),
          rightValue: true,
          operator: { type: 'boolean', operation: 'true' }
        }]
      },
      looseTypeValidation: true
    },
    position: [1640, 400]
  }
});

const splitQualified = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Split Qualified',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const j = $input.first().json || {};\n" +
        "const arr = Array.isArray(j.qualified) ? j.qualified : [];\n" +
        "if (arr.length === 0) return [{ json: { _empty: true } }];\n" +
        "return arr.map(p => ({ json: p }));"
    },
    position: [1840, 500]
  },
  output: [{ id: 'hn-1', score: 8, reason: 'Direct match', draft_comment: 'For 5+ clients...', source: 'hn', url: 'https://...', title: 'Best client reporting tool?', keyword: 'client reporting' }]
});

const loop = splitInBatches({
  version: 3,
  config: { name: 'Loop Qualified', parameters: { batchSize: 1 }, position: [2040, 500] }
});

const shapeDoc = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Shape Engage Doc',
    parameters: {
      mode: 'runOnceForEachItem',
      language: 'javaScript',
      jsCode: "const j = $input.item.json;\n" +
        "const d = new Date();\n" +
        "const ist = new Date(d.getTime() + (5.5 * 60 * 60 * 1000));\n" +
        "const dateStr = ist.toISOString().slice(0, 10);\n" +
        "const titleSlug = String(j.title || 'untitled').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);\n" +
        "const sourceLabel = j.source === 'reddit' ? ('reddit-' + (j.subreddit || 'x')) : 'hn';\n" +
        "const doc_name = dateStr + '-' + sourceLabel + '-' + titleSlug + '.txt';\n" +
        "const content = 'Source: ' + (j.source || '') + '\\n' +\n" +
        "  'URL: ' + (j.url || '') + '\\n' +\n" +
        "  'Title: ' + (j.title || '') + '\\n' +\n" +
        "  'Author: ' + (j.author || '') + '\\n' +\n" +
        "  (j.subreddit ? 'Subreddit: r/' + j.subreddit + '\\n' : '') +\n" +
        "  'Keyword: ' + (j.keyword || '') + '\\n' +\n" +
        "  'Points: ' + (j.points || 0) + ' | Comments: ' + (j.num_comments || 0) + '\\n' +\n" +
        "  'Created: ' + (j.created_at || '') + '\\n' +\n" +
        "  'Score: ' + (j.score || 0) + '/10\\n' +\n" +
        "  'Reason: ' + (j.reason || '') + '\\n\\n' +\n" +
        "  '---\\n\\nORIGINAL POST SNIPPET:\\n' + ((j.snippet || '').slice(0, 200)) + '\\n\\n' +\n" +
        "  '---\\n\\nDRAFT COMMENT (rewrite in your voice before posting):\\n' + (j.draft_comment || '') + '\\n\\n' +\n" +
        "  '---\\nGenerated at: ' + new Date().toISOString();\n" +
        "return { ...j, doc_name: doc_name, doc_content: content };"
    },
    position: [2240, 500]
  },
  output: [{ id: 'hn-1', source: 'hn', url: 'https://...', title: 'Best client reporting tool?', score: 8, doc_name: '2026-04-26-hn-best-client-reporting-tool.txt', doc_content: 'Source: hn\\n...' }]
});

const saveDoc = node({
  type: 'n8n-nodes-base.googleDrive',
  version: 3,
  config: {
    name: 'Save Engage Doc',
    parameters: {
      resource: 'file',
      operation: 'createFromText',
      content: expr('{{ $json.doc_content }}'),
      name: expr('{{ $json.doc_name }}'),
      driveId: { __rl: true, mode: 'list', value: 'My Drive' },
      folderId: { __rl: true, mode: 'id', value: ENGAGE_FOLDER_ID },
      options: { convertToGoogleDocument: false }
    },
    credentials: { googleDriveOAuth2Api: newCredential('Google Drive') },
    alwaysOutputData: true,
    position: [2440, 500]
  },
  output: [{ id: 'newfileid', name: '2026-04-26-hn-best-client-reporting-tool.txt', webViewLink: 'https://drive.google.com/file/d/newfileid/view' }]
});

const shapeRunLog = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Shape Run Log Row',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "function safeFirstJson(name){ try { return $(name).first().json || {}; } catch(e){ return {}; } }\n" +
        "function safeAll(name){ try { return $(name).all() || []; } catch(e){ return []; } }\n" +
        "const norm = safeFirstJson('Normalize Results');\n" +
        "const parse = safeFirstJson('Parse Scores');\n" +
        "const noPosts = !!norm._no_posts;\n" +
        "const totalScored = parse.total_scored || 0;\n" +
        "const qualifiedCount = parse.qualified_count || 0;\n" +
        "const splitAll = safeAll('Split Qualified');\n" +
        "const draftsCreated = splitAll.filter(it => it && it.json && !it.json._empty).length;\n" +
        "const cost = (totalScored > 0 ? 0.05 : 0).toFixed(4);\n" +
        "const parseFails = norm.parse_failures || 0;\n" +
        "let status = 'success';\n" +
        "if (noPosts) status = 'no_posts_found';\n" +
        "else if (qualifiedCount === 0) status = 'none_qualified';\n" +
        "const errors = parseFails > 0 ? (parseFails + ' source(s) returned non-JSON (likely Reddit rate limit/HTML block)') : '';\n" +
        "return [{ json: {\n" +
        "  date: new Date().toISOString(),\n" +
        "  hn_posts_found: String(norm.hn_count || 0),\n" +
        "  reddit_posts_found: String(norm.reddit_count || 0),\n" +
        "  total_scored: String(totalScored),\n" +
        "  qualified_count: String(qualifiedCount),\n" +
        "  drafts_created: String(draftsCreated),\n" +
        "  openai_cost_usd: cost,\n" +
        "  errors: errors,\n" +
        "  status: status\n" +
        "} }];"
    },
    position: [2640, 700]
  },
  output: [{ date: '2026-04-26T02:30:00Z', hn_posts_found: '5', reddit_posts_found: '8', total_scored: '13', qualified_count: '2', drafts_created: '2', openai_cost_usd: '0.0500', errors: '', status: 'success' }]
});

const logRun = node({
  type: 'n8n-nodes-base.googleSheets',
  version: 4.7,
  config: {
    name: 'Log Run',
    parameters: {
      resource: 'sheet',
      operation: 'append',
      documentId: { __rl: true, mode: 'id', value: LISTENER_LOG_ID },
      sheetName: { __rl: true, mode: 'name', value: LISTENER_LOG_TAB },
      columns: { mappingMode: 'autoMapInputData', value: null, matchingColumns: [], schema: [], attemptToConvertTypes: false, convertFieldsToString: true },
      options: { useAppend: true, handlingExtraData: 'ignoreIt' }
    },
    credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') },
    position: [2840, 700]
  },
  output: [{ ok: true }]
});

export default workflow('grp-reddit-hn-listener', 'GRP - Reddit HN Listener (2x Daily)')
  .add(trig)
  .to(buildSearchList)
  .to(fetchAll)
  .to(normalize)
  .to(hasPosts
    .onTrue(shapeRunLog)
    .onFalse(scoreAll
      .to(parseScores)
      .to(hasQualified
        .onTrue(shapeRunLog)
        .onFalse(splitQualified
          .to(loop
            .onDone(shapeRunLog)
            .onEachBatch(
              shapeDoc
                .to(saveDoc)
                .to(nextBatch(loop))
            )
          )
        )
      )
    )
  )
  .add(shapeRunLog)
  .to(logRun);
