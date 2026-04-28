// ComparisonTable — shared server component used on both / (landing) and /features
// Extracted so both pages stay in sync without copy-paste drift.
// Pure server component — no client state needed.

const ROWS = [
  ['Price (15 clients)',       '$179–239/mo',    '$249–999/mo',     'Free (DIY)',       '$39/mo ✓'],
  ['AI multi-para narrative',  'Add-on only',    'Short summaries', 'None',             'Included ✓'],
  ['Editable PPTX export',     '✗ (PDF only)',   '✗ (PDF only)',    '✗',                'Yes ✓'],
  ['Pricing model',            'Per client',     'Per data src',    'Free / DIY setup', 'Per client (flat) ✓'],
  ['White-label',              'Higher tiers',   'Yes',             'DIY only',         'Pro+ ✓'],
  ['13-language reports',      '✗',              '✗',               'DIY templates',    'Yes ✓'],
  ['CSV upload (any source)',   '✗',              'Limited',         'DIY',              'Yes ✓'],
  ['Time to first report',      '30+ min setup',  '1+ hour',         'Days (DIY)',        '<5 min ✓'],
] as const

export default function ComparisonTable() {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-100 shadow-sm">
      <table className="w-full min-w-[760px] text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            <th className="text-left py-4 px-6 text-slate-400 font-medium text-xs uppercase tracking-wide w-[30%]">
              Feature
            </th>
            <th className="text-center py-4 px-3 text-slate-400 font-medium text-xs uppercase tracking-wide">
              AgencyAnalytics
            </th>
            <th className="text-center py-4 px-3 text-slate-400 font-medium text-xs uppercase tracking-wide">
              Whatagraph
            </th>
            <th className="text-center py-4 px-3 text-slate-400 font-medium text-xs uppercase tracking-wide">
              Looker Studio
            </th>
            <th className="text-center py-4 px-3 bg-indigo-50 text-indigo-700 font-bold text-xs uppercase tracking-wide">
              GoReportPilot
            </th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(([feature, aa, wg, ls, rp], i) => (
            <tr
              key={feature}
              className={`border-b border-slate-50 last:border-0 ${i % 2 === 0 ? '' : 'bg-slate-50/40'}`}
            >
              <td className="py-3.5 px-6 text-slate-700 font-medium text-sm">{feature}</td>
              <td className="py-3.5 px-3 text-center text-slate-400 text-sm">{aa}</td>
              <td className="py-3.5 px-3 text-center text-slate-400 text-sm">{wg}</td>
              <td className="py-3.5 px-3 text-center text-slate-400 text-sm">{ls}</td>
              <td className="py-3.5 px-3 text-center bg-indigo-50 text-indigo-700 font-semibold text-sm">{rp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
