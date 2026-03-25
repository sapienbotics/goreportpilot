'use client'
import { BarChart2, Megaphone, TrendingUp, Search, Database, Link2, Unlink, Loader2, Upload } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import CSVUploadDialog from '@/components/clients/CSVUploadDialog'
import type { Connection } from '@/types'

interface Props {
  clientId: string
  connections: Connection[]
  connectionsLoading: boolean
  connectingGa4: boolean
  connectingMeta: boolean
  connectingGads: boolean
  connectingGsc: boolean
  disconnecting: string | null
  showCsvUpload: boolean
  setShowCsvUpload: (v: boolean) => void
  handleConnectGa4: () => void
  handleConnectMeta: () => void
  handleConnectGoogleAds: () => void
  handleConnectSearchConsole: () => void
  handleDisconnect: (id: string) => void
  onConnectionsRefresh: () => void
}

interface PlatformRowConfig {
  platform: string
  label: string
  Icon: React.FC<{ className?: string }>
  connecting: boolean
  onConnect: () => void
  notConnectedSubtext: string
  connectLabel: string
}

function PlatformRow({ conn, cfg, disconnecting, handleDisconnect }: {
  conn: Connection | undefined
  cfg: PlatformRowConfig
  disconnecting: string | null
  handleDisconnect: (id: string) => void
}) {
  const { Icon, label, connecting, onConnect, notConnectedSubtext, connectLabel } = cfg
  if (conn) {
    const healthy = conn.status === 'active'
    return (
      <div className={`flex items-center justify-between rounded-lg border px-4 py-3 ${healthy ? 'border-emerald-100 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}>
        <div className="flex items-center gap-3 min-w-0">
          <Icon className={`h-4 w-4 shrink-0 ${healthy ? 'text-emerald-600' : 'text-amber-500'}`} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">{conn.account_name}</p>
            <p className="text-xs text-slate-400 truncate">{conn.account_id}</p>
          </div>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${healthy ? 'text-emerald-700 bg-emerald-100' : 'text-amber-700 bg-amber-100'}`}>
            {healthy ? 'Active' : conn.status === 'error' ? 'Error' : 'Expired'}
          </span>
        </div>
        <div className="flex items-center gap-2 ml-3 shrink-0">
          {!healthy && (
            <button onClick={onConnect} disabled={connecting} className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 transition-colors disabled:opacity-60">
              {connecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Link2 className="h-3 w-3" />}
              Reconnect
            </button>
          )}
          <button onClick={() => handleDisconnect(conn.id)} disabled={disconnecting === conn.id} className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-60">
            {disconnecting === conn.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Unlink className="h-3 w-3" />}
            Disconnect
          </button>
        </div>
      </div>
    )
  }
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-slate-400 shrink-0" />
        <div>
          <p className="text-sm font-medium text-slate-700">{label}</p>
          <p className="text-xs text-slate-400">{notConnectedSubtext}</p>
        </div>
      </div>
      <button onClick={onConnect} disabled={connecting} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60 shrink-0 ml-3">
        {connecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Link2 className="h-3 w-3" />}
        {connectLabel}
      </button>
    </div>
  )
}

export default function IntegrationsTab({
  clientId, connections, connectionsLoading,
  connectingGa4, connectingMeta, connectingGads, connectingGsc,
  disconnecting, showCsvUpload, setShowCsvUpload,
  handleConnectGa4, handleConnectMeta, handleConnectGoogleAds, handleConnectSearchConsole,
  handleDisconnect, onConnectionsRefresh,
}: Props) {
  const ga4 = connections.find(c => c.platform === 'ga4' || c.platform === 'google_analytics')
  const meta = connections.find(c => c.platform === 'meta_ads')
  const gads = connections.find(c => c.platform === 'google_ads')
  const gsc = connections.find(c => c.platform === 'search_console')
  const csvConns = connections.filter(c => c.platform.startsWith('csv_'))

  const platforms: Array<{ key: string; conn: Connection | undefined; cfg: PlatformRowConfig }> = [
    {
      key: 'ga4',
      conn: ga4,
      cfg: { platform: 'ga4', label: 'Google Analytics 4', Icon: BarChart2, connecting: connectingGa4, onConnect: handleConnectGa4, notConnectedSubtext: 'Not connected — reports use sample data', connectLabel: 'Connect GA4' },
    },
    {
      key: 'meta',
      conn: meta,
      cfg: { platform: 'meta_ads', label: 'Meta Ads', Icon: Megaphone, connecting: connectingMeta, onConnect: handleConnectMeta, notConnectedSubtext: 'Not connected — reports use sample data', connectLabel: 'Connect Meta Ads' },
    },
    {
      key: 'gads',
      conn: gads,
      cfg: { platform: 'google_ads', label: 'Google Ads', Icon: TrendingUp, connecting: connectingGads, onConnect: handleConnectGoogleAds, notConnectedSubtext: 'Not connected — reports use sample data', connectLabel: 'Connect Google Ads' },
    },
    {
      key: 'gsc',
      conn: gsc,
      cfg: { platform: 'search_console', label: 'Google Search Console', Icon: Search, connecting: connectingGsc, onConnect: handleConnectSearchConsole, notConnectedSubtext: 'Not connected — SEO slides use sample data', connectLabel: 'Connect Search Console' },
    },
  ]

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-slate-400" />
            Platform Connections
          </CardTitle>
        </CardHeader>
        <CardContent>
          {connectionsLoading ? (
            <div className="h-12 rounded-lg bg-slate-100 animate-pulse" />
          ) : (
            <div className="space-y-3">
              {platforms.map(({ key, conn, cfg }) => (
                <PlatformRow key={key} conn={conn} cfg={cfg} disconnecting={disconnecting} handleDisconnect={handleDisconnect} />
              ))}

              {/* CSV row */}
              <div className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3">
                <div className="flex items-center gap-3">
                  <Database className="h-4 w-4 text-slate-400 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-slate-700">CSV / Manual Data</p>
                    <p className="text-xs text-slate-400">
                      {csvConns.length > 0 ? `${csvConns.length} CSV source(s) connected` : 'Upload LinkedIn Ads, TikTok, Shopify, or custom metrics'}
                    </p>
                  </div>
                </div>
                <button onClick={() => setShowCsvUpload(true)} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-800 transition-colors shrink-0 ml-3">
                  <Upload className="h-3 w-3" />
                  Upload CSV
                </button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {showCsvUpload && (
        <CSVUploadDialog
          clientId={clientId}
          onClose={() => setShowCsvUpload(false)}
          onSuccess={() => { setShowCsvUpload(false); onConnectionsRefresh() }}
        />
      )}
    </div>
  )
}
