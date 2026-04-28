// Canonical source for n8n workflow: GRP - Competitor Monitor (Daily)
// Workflow ID: 0sU9XMFAHSCHkCpt
//
// This file is the single source of truth. To deploy:
//   1. update_workflow(workflowId='0sU9XMFAHSCHkCpt', code=<contents of this file>)
//   2. get_workflow_details — copy the resulting `versionId` (the draft)
//   3. publish_workflow(workflowId='0sU9XMFAHSCHkCpt', versionId=<that versionId>)
//
// ⛔ Never edit and Save this workflow from the n8n UI — it overwrites this version.
// See Marketing/RUNBOOK.md for the full hard rule and recovery procedure.

import { workflow, node, trigger, ifElse, splitInBatches, nextBatch, newCredential, expr } from '@n8n/workflow-sdk';

const SNAPSHOTS_FOLDER_ID = '1sgCklwLyVrIbn_OZwk6GZmVs37G0BDTN';
const CHANGELOG_SHEET_ID = '10eUXlTpu0_9MnsbXF_SJqYBkGxDhX5lyALTuotx4wcM';
const CHANGELOG_TAB_NAME = 'Competitor-Changelog';

const scheduleTrigger = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.3,
  config: {
    name: 'Daily 8AM IST',
    parameters: { rule: { interval: [{ field: 'cronExpression', expression: '0 30 2 * * *' }] } },
    position: [240, 300]
  },
  output: [{}]
});

const buildUrlList = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Build URL List',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const targets = [\n" +
        "  { competitor: 'agencyanalytics', page: 'pricing', url: 'https://agencyanalytics.com/pricing' },\n" +
        "  { competitor: 'agencyanalytics', page: 'features', url: 'https://agencyanalytics.com/features' },\n" +
        "  { competitor: 'agencyanalytics', page: 'home', url: 'https://agencyanalytics.com/' },\n" +
        "  { competitor: 'whatagraph', page: 'pricing', url: 'https://whatagraph.com/pricing' },\n" +
        "  { competitor: 'whatagraph', page: 'features', url: 'https://whatagraph.com/features' },\n" +
        "  { competitor: 'whatagraph', page: 'home', url: 'https://whatagraph.com/' },\n" +
        "  { competitor: 'swydo', page: 'pricing', url: 'https://www.swydo.com/pricing/' },\n" +
        "  { competitor: 'swydo', page: 'features', url: 'https://www.swydo.com/features/' },\n" +
        "  { competitor: 'swydo', page: 'home', url: 'https://www.swydo.com/' },\n" +
        "  { competitor: 'ninjacat', page: 'pricing', url: 'https://www.ninjacat.io/pricing' },\n" +
        "  { competitor: 'ninjacat', page: 'features', url: 'https://www.ninjacat.io/features' },\n" +
        "  { competitor: 'ninjacat', page: 'home', url: 'https://www.ninjacat.io/' }\n" +
        "];\n" +
        "return targets.map(t => ({ json: { ...t, doc_name: t.competitor + '-' + t.page + '.txt' } }));"
    },
    position: [440, 300]
  },
  output: [{ competitor: 'agencyanalytics', page: 'pricing', url: 'https://agencyanalytics.com/pricing', doc_name: 'agencyanalytics-pricing.txt' }]
});

const loopUrls = splitInBatches({
  version: 3,
  config: { name: 'Loop Over URLs', parameters: { batchSize: 1 }, position: [640, 300] }
});

const fetchPage = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Fetch Page HTML',
    parameters: {
      method: 'GET',
      url: expr('{{ $json.url }}'),
      sendHeaders: true,
      specifyHeaders: 'keypair',
      headerParameters: {
        parameters: [
          { name: 'User-Agent', value: 'Mozilla/5.0 (compatible; GoReportPilot-CompetitorMonitor/1.0)' },
          { name: 'Accept', value: 'text/html,application/xhtml+xml' }
        ]
      },
      options: {
        response: { response: { responseFormat: 'text', neverError: true } },
        timeout: 30000,
        redirect: { redirect: { followRedirects: true, maxRedirects: 5 } }
      }
    },
    alwaysOutputData: true,
    position: [840, 300]
  },
  output: [{ data: '<html>...</html>' }]
});

const stripHtml = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Strip HTML to Text',
    parameters: {
      mode: 'runOnceForEachItem',
      language: 'javaScript',
      jsCode: "const item = $input.item.json;\n" +
        "let html = '';\n" +
        "if (typeof item === 'string') html = item;\n" +
        "else if (item.data) html = String(item.data);\n" +
        "else if (item.body) html = String(item.body);\n" +
        "else html = JSON.stringify(item);\n" +
        "let text = html;\n" +
        "text = text.replace(/<script[\\s\\S]*?<\\/script>/gi, ' ');\n" +
        "text = text.replace(/<style[\\s\\S]*?<\\/style>/gi, ' ');\n" +
        "text = text.replace(/<noscript[\\s\\S]*?<\\/noscript>/gi, ' ');\n" +
        "text = text.replace(/<!--[\\s\\S]*?-->/g, ' ');\n" +
        "text = text.replace(/<[^>]+>/g, ' ');\n" +
        "text = text.replace(/&nbsp;/gi, ' ');\n" +
        "text = text.replace(/&amp;/gi, '&');\n" +
        "text = text.replace(/&lt;/gi, '<');\n" +
        "text = text.replace(/&gt;/gi, '>');\n" +
        "text = text.replace(/&quot;/gi, '\"');\n" +
        "text = text.replace(/&#39;/gi, \"'\");\n" +
        "text = text.replace(/\\s+/g, ' ').trim();\n" +
        "if (text.length > 60000) text = text.slice(0, 60000);\n" +
        "const meta = $('Loop Over URLs').item.json;\n" +
        "return { competitor: meta.competitor, page: meta.page, url: meta.url, doc_name: meta.doc_name, new_text: text };"
    },
    position: [1040, 300]
  },
  output: [{ competitor: 'agencyanalytics', page: 'pricing', url: 'https://...', doc_name: 'agencyanalytics-pricing.txt', new_text: 'plain text' }]
});

const searchSnapshot = node({
  type: 'n8n-nodes-base.googleDrive',
  version: 3,
  config: {
    name: 'Find Existing Snapshot',
    parameters: {
      resource: 'fileFolder',
      operation: 'search',
      searchMethod: 'name',
      queryString: expr('{{ $json.doc_name }}'),
      returnAll: true,
      filter: {
        folderId: { __rl: true, mode: 'id', value: SNAPSHOTS_FOLDER_ID },
        whatToSearch: 'files',
        includeTrashed: false
      },
      options: { fields: ['id', 'name', 'webViewLink', 'mimeType'] }
    },
    credentials: { googleDriveOAuth2Api: newCredential('Google Drive') },
    alwaysOutputData: true,
    position: [1240, 300]
  },
  output: [{ id: 'fileid123', name: 'agencyanalytics-pricing.txt', mimeType: 'text/plain' }]
});

const combineState = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Combine State',
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: "const stripped = $('Strip HTML to Text').item.json;\n" +
        "const all = $input.all();\n" +
        "let file_id = null;\n" +
        "let snapshot_url = null;\n" +
        "for (const it of all) {\n" +
        "  const j = (it && it.json) ? it.json : {};\n" +
        "  if (j.id && j.name === stripped.doc_name && j.mimeType !== 'application/vnd.google-apps.document') {\n" +
        "    file_id = j.id;\n" +
        "    snapshot_url = j.webViewLink || ('https://drive.google.com/file/d/' + j.id + '/view');\n" +
        "    break;\n" +
        "  }\n" +
        "}\n" +
        "return [{ json: {\n" +
        "  competitor: stripped.competitor,\n" +
        "  page: stripped.page,\n" +
        "  url: stripped.url,\n" +
        "  doc_name: stripped.doc_name,\n" +
        "  new_text: stripped.new_text,\n" +
        "  found: !!file_id,\n" +
        "  file_id: file_id,\n" +
        "  snapshot_url: snapshot_url\n" +
        "} }];"
    },
    position: [1440, 300]
  },
  output: [{ competitor: 'agencyanalytics', page: 'pricing', url: 'x', doc_name: 'agencyanalytics-pricing.txt', new_text: 'text', found: true, file_id: 'fileid', snapshot_url: 'https://drive.google.com/...' }]
});

const checkExists = ifElse({
  version: 2.3,
  config: {
    name: 'Snapshot Exists?',
    parameters: {
      conditions: {
        combinator: 'and',
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 },
        conditions: [{
          leftValue: expr('{{ $json.found }}'),
          rightValue: true,
          operator: { type: 'boolean', operation: 'true' }
        }]
      }
    },
    position: [1640, 300]
  }
});

const downloadDoc = node({
  type: 'n8n-nodes-base.googleDrive',
  version: 3,
  config: {
    name: 'Download Prior Snapshot',
    parameters: {
      resource: 'file',
      operation: 'download',
      fileId: { __rl: true, mode: 'id', value: expr('{{ $json.file_id }}') },
      options: { binaryPropertyName: 'data' }
    },
    credentials: { googleDriveOAuth2Api: newCredential('Google Drive') },
    position: [1840, 200]
  },
  output: [{ id: 'fileid', name: 'agencyanalytics-pricing.txt' }]
});

const decodePrior = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Decode Prior Snapshot',
    parameters: {
      mode: 'runOnceForEachItem',
      language: 'javaScript',
      jsCode: "const meta = $('Combine State').item.json;\n" +
        "const bin = $input.item.binary && $input.item.binary.data;\n" +
        "let old_text = '';\n" +
        "if (bin && bin.data) {\n" +
        "  old_text = Buffer.from(bin.data, 'base64').toString('utf8');\n" +
        "}\n" +
        "old_text = old_text.replace(/\\r\\n?/g, '\\n').trim();\n" +
        "if (old_text.length > 60000) old_text = old_text.slice(0, 60000);\n" +
        "return {\n" +
        "  competitor: meta.competitor,\n" +
        "  page: meta.page,\n" +
        "  url: meta.url,\n" +
        "  doc_name: meta.doc_name,\n" +
        "  file_id: meta.file_id,\n" +
        "  snapshot_url: meta.snapshot_url,\n" +
        "  new_text: meta.new_text,\n" +
        "  old_text: old_text\n" +
        "};"
    },
    position: [2040, 200]
  },
  output: [{ competitor: 'x', page: 'y', new_text: 'a', old_text: 'b' }]
});

const diffViaOpenAi = node({
  type: '@n8n/n8n-nodes-langchain.openAi',
  version: 2.1,
  config: {
    name: 'Diff via GPT-4o-mini',
    parameters: {
      resource: 'text',
      operation: 'response',
      modelId: { __rl: true, mode: 'id', value: 'gpt-4o-mini' },
      responses: {
        values: [
          { type: 'text', role: 'system', content: "You compare two snapshots of a SaaS competitor web page and decide if anything strategically meaningful changed. Output ONLY a JSON object with keys: has_meaningful_change (boolean), summary (2-3 sentence plain English of what changed), categories (array of strings from this set: pricing, features, positioning, cosmetic). Ignore: dates, view/download counters, A/B test variations, footer copyright years, minor word reordering, whitespace, navigation menu reorderings, cookie banners, social-proof rotations. If only cosmetic changes occurred, set has_meaningful_change to false. Always return valid JSON." },
          { type: 'text', role: 'user', content: expr('PAGE: {{ $json.competitor }} {{ $json.page }}\nURL: {{ $json.url }}\n\n=== OLD VERSION ===\n{{ $json.old_text }}\n\n=== NEW VERSION ===\n{{ $json.new_text }}') }
        ]
      },
      simplify: true,
      options: { maxTokens: 600, temperature: 0.1, textFormat: { textOptions: [{ type: 'json_object' }] } }
    },
    credentials: { openAiApi: newCredential('OpenAI') },
    position: [2240, 200]
  },
  output: [{ content: '{"has_meaningful_change": true, "summary": "Pricing page added Enterprise tier at $199/mo.", "categories": ["pricing"]}' }]
});

const parseDiff = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Parse Diff Result',
    parameters: {
      mode: 'runOnceForEachItem',
      language: 'javaScript',
      jsCode: "const j = $input.item.json || {};\n" +
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
        "    for (const c of cs) {\n" +
        "      if (c && typeof c.text === 'string') raw += c.text;\n" +
        "      else if (typeof c === 'string') raw += c;\n" +
        "    }\n" +
        "  }\n" +
        "}\n" +
        "if (!raw) raw = JSON.stringify(j);\n" +
        "let parsed = null;\n" +
        "try { parsed = JSON.parse(raw); } catch(e) {\n" +
        "  const m = raw.match(/\\{[\\s\\S]*\\}/);\n" +
        "  if (m) { try { parsed = JSON.parse(m[0]); } catch(_) {} }\n" +
        "}\n" +
        "if (!parsed || typeof parsed !== 'object') parsed = { has_meaningful_change: false, summary: 'parse_failed', categories: ['cosmetic'] };\n" +
        "const meta = $('Decode Prior Snapshot').item.json;\n" +
        "return {\n" +
        "  competitor: meta.competitor,\n" +
        "  page: meta.page,\n" +
        "  url: meta.url,\n" +
        "  doc_name: meta.doc_name,\n" +
        "  file_id: meta.file_id,\n" +
        "  snapshot_url: meta.snapshot_url,\n" +
        "  new_text: meta.new_text,\n" +
        "  has_meaningful_change: !!parsed.has_meaningful_change,\n" +
        "  summary: parsed.summary || '',\n" +
        "  categories: Array.isArray(parsed.categories) ? parsed.categories.join(',') : (parsed.categories || '')\n" +
        "};"
    },
    position: [2440, 200]
  },
  output: [{ has_meaningful_change: true, summary: 'pricing changed', categories: 'pricing', competitor: 'x', page: 'y', new_text: 'z', file_id: 'fid', snapshot_url: 'url', doc_name: 'd', url: 'u' }]
});

const checkMeaningful = ifElse({
  version: 2.3,
  config: {
    name: 'Meaningful Change?',
    parameters: {
      conditions: {
        combinator: 'and',
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 },
        conditions: [{
          leftValue: expr('{{ $json.has_meaningful_change }}'),
          rightValue: true,
          operator: { type: 'boolean', operation: 'true' }
        }]
      }
    },
    position: [2640, 200]
  }
});

const prepareUpdateBinary = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Prepare Update Binary',
    parameters: {
      mode: 'runOnceForEachItem',
      language: 'javaScript',
      jsCode: "const j = $input.item.json;\n" +
        "const buf = Buffer.from(j.new_text || '', 'utf8');\n" +
        "const binData = await this.helpers.prepareBinaryData(buf, j.doc_name, 'text/plain');\n" +
        "return { json: j, binary: { data: binData } };"
    },
    position: [2840, 100]
  },
  output: [{ competitor: 'x', file_id: 'fid', new_text: 'a' }]
});

const updateDoc = node({
  type: 'n8n-nodes-base.googleDrive',
  version: 3,
  config: {
    name: 'Update Snapshot Doc',
    parameters: {
      resource: 'file',
      operation: 'update',
      fileId: { __rl: true, mode: 'id', value: expr('{{ $json.file_id }}') },
      changeFileContent: true,
      inputDataFieldName: 'data',
      options: { keepRevisionForever: false, fields: ['id', 'webViewLink'] }
    },
    credentials: { googleDriveOAuth2Api: newCredential('Google Drive') },
    position: [3040, 100]
  },
  output: [{ id: 'fileid', webViewLink: 'https://drive.google.com/...' }]
});

const shapeChangeRow = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Shape Change Row',
    parameters: {
      mode: 'manual',
      assignments: {
        assignments: [
          { id: 'a1', name: 'date', value: expr('{{ $now.toISO() }}'), type: 'string' },
          { id: 'a2', name: 'competitor', value: expr("{{ $('Parse Diff Result').item.json.competitor }}"), type: 'string' },
          { id: 'a3', name: 'page', value: expr("{{ $('Parse Diff Result').item.json.page }}"), type: 'string' },
          { id: 'a4', name: 'summary', value: expr("{{ $('Parse Diff Result').item.json.summary }}"), type: 'string' },
          { id: 'a5', name: 'categories', value: expr("{{ $('Parse Diff Result').item.json.categories }}"), type: 'string' },
          { id: 'a6', name: 'snapshot_url', value: expr("{{ $('Parse Diff Result').item.json.snapshot_url }}"), type: 'string' },
          { id: 'a7', name: 'status', value: 'changed', type: 'string' }
        ]
      },
      includeOtherFields: false
    },
    position: [3240, 100]
  },
  output: [{ date: '2026-04-26T10:00:00.000Z', competitor: 'agencyanalytics', page: 'pricing', summary: 'x', categories: 'pricing', snapshot_url: 'https://...', status: 'changed' }]
});

const appendChangeRow = node({
  type: 'n8n-nodes-base.googleSheets',
  version: 4.7,
  config: {
    name: 'Log Change',
    parameters: {
      resource: 'sheet',
      operation: 'append',
      documentId: { __rl: true, mode: 'id', value: CHANGELOG_SHEET_ID },
      sheetName: { __rl: true, mode: 'name', value: CHANGELOG_TAB_NAME },
      columns: {
        mappingMode: 'autoMapInputData',
        value: null,
        matchingColumns: [],
        schema: [],
        attemptToConvertTypes: false,
        convertFieldsToString: true
      },
      options: { useAppend: true, handlingExtraData: 'ignoreIt' }
    },
    credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') },
    position: [3440, 100]
  },
  output: [{ ok: true }]
});

const createInitialDoc = node({
  type: 'n8n-nodes-base.googleDrive',
  version: 3,
  config: {
    name: 'Create Initial Snapshot',
    parameters: {
      resource: 'file',
      operation: 'createFromText',
      content: expr('{{ $json.new_text }}'),
      name: expr('{{ $json.doc_name }}'),
      driveId: { __rl: true, mode: 'list', value: 'My Drive' },
      folderId: { __rl: true, mode: 'id', value: SNAPSHOTS_FOLDER_ID },
      options: { convertToGoogleDocument: false }
    },
    credentials: { googleDriveOAuth2Api: newCredential('Google Drive') },
    position: [1840, 500]
  },
  output: [{ id: 'newfileid', webViewLink: 'https://drive.google.com/...' }]
});

const shapeInitialRow = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Shape Initial Row',
    parameters: {
      mode: 'manual',
      assignments: {
        assignments: [
          { id: 'b1', name: 'date', value: expr('{{ $now.toISO() }}'), type: 'string' },
          { id: 'b2', name: 'competitor', value: expr("{{ $('Combine State').item.json.competitor }}"), type: 'string' },
          { id: 'b3', name: 'page', value: expr("{{ $('Combine State').item.json.page }}"), type: 'string' },
          { id: 'b4', name: 'summary', value: 'Initial snapshot captured.', type: 'string' },
          { id: 'b5', name: 'categories', value: 'initial', type: 'string' },
          { id: 'b6', name: 'snapshot_url', value: expr("{{ $json.webViewLink || ('https://drive.google.com/file/d/' + $json.id + '/view') }}"), type: 'string' },
          { id: 'b7', name: 'status', value: 'initial', type: 'string' }
        ]
      },
      includeOtherFields: false
    },
    position: [2040, 500]
  },
  output: [{ date: '2026-04-26T10:00:00.000Z', competitor: 'agencyanalytics', page: 'pricing', summary: 'Initial snapshot captured.', categories: 'initial', snapshot_url: 'https://...', status: 'initial' }]
});

const appendInitialRow = node({
  type: 'n8n-nodes-base.googleSheets',
  version: 4.7,
  config: {
    name: 'Log Initial',
    parameters: {
      resource: 'sheet',
      operation: 'append',
      documentId: { __rl: true, mode: 'id', value: CHANGELOG_SHEET_ID },
      sheetName: { __rl: true, mode: 'name', value: CHANGELOG_TAB_NAME },
      columns: {
        mappingMode: 'autoMapInputData',
        value: null,
        matchingColumns: [],
        schema: [],
        attemptToConvertTypes: false,
        convertFieldsToString: true
      },
      options: { useAppend: true, handlingExtraData: 'ignoreIt' }
    },
    credentials: { googleSheetsOAuth2Api: newCredential('Google Sheets') },
    position: [2240, 500]
  },
  output: [{ ok: true }]
});

export default workflow('grp-competitor-monitor', 'GRP - Competitor Monitor (Daily)')
  .add(scheduleTrigger)
  .to(buildUrlList)
  .to(loopUrls
    .onEachBatch(
      fetchPage
        .to(stripHtml)
        .to(searchSnapshot)
        .to(combineState)
        .to(checkExists
          .onTrue(
            downloadDoc
              .to(decodePrior)
              .to(diffViaOpenAi)
              .to(parseDiff)
              .to(checkMeaningful
                .onTrue(
                  prepareUpdateBinary
                    .to(updateDoc)
                    .to(shapeChangeRow)
                    .to(appendChangeRow)
                    .to(nextBatch(loopUrls))
                )
                .onFalse(nextBatch(loopUrls))
              )
          )
          .onFalse(
            createInitialDoc
              .to(shapeInitialRow)
              .to(appendInitialRow)
              .to(nextBatch(loopUrls))
          )
        )
    )
  );
