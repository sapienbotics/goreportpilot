'use client'
import { BarChart2, Megaphone, TrendingUp, Search, Link2, Unlink, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
  connectLabel: string
  notConnectedSubtext: string
  onConnect: () => void
}

function PlatformRow({
  conn,
  cfg,
  disconnecting,
  handleDisconnect,
}: {
  conn: Connection | undefined
  cfg: PlatformRowConfig
  disconnecting: string | null
  handleDisconnect: (id: string) => void
}) {
  const { Icon, label, connecting, onConnect, notConnectedSubtext, connectLabel } = cfg
  const isConnected = !!conn && conn.status === 'active'
  const isExpired   = !!conn && (conn.status === 'expired' || conn.status === 'error')
  const isDisconnecting = conn ? disconnecting === conn.id : false

  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        <Icon className={`h-4 w-4 shrink-0 ${isConnected ? 'text-indigo-600' : 'text-slate-400'}`} />
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-700">{label}</p>
          {isConnected ? (
            <p className="text-xs text-emerald-600">
              Connected{conn.account_name ? ` — ${conn.account_name}` : ''}
            </p>
          ) : isExpired ? (
            <p className="text-xs text-amber-600">Token expired — reconnect</p>
          ) : (
            <p className="text-xs text-slate-400">{notConnectedSubtext}</p>
          )}
        </div>
      </div>
      {isConnected ? (
        <button
          onClick={() => conn && handleDisconnect(conn.id)}
          disabled={isDisconnecting}
          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-60 shrink-0 ml-3"
        >
          {isDisconnecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Unlink className="h-3 w-3" />}
          {isDisconnecting ? 'Disconnecting…' : 'Disconnect'}
        </button>
      ) : (
        <button onClick={onConnect} disabled={connecting} className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-800 transition-colors disabled:opacity-60 shrink-0 ml-3">
          {connecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Link2 className="h-3 w-3" />}
          {connectLabel}
        </button>
      )}
    </div>
  )
}

export default function IntegrationsTab({
  connections, connectionsLoading,
  connectingGa4, connectingMeta, connectingGads, connectingGsc,
  disconnecting,
  handleConnectGa4, handleConnectMeta, handleConnectGoogleAds, handleConnectSearchConsole,
  handleDisconnect,
}: Props) {
  const ga4  = connections.find(c => c.platform === 'ga4' || c.platform === 'google_analytics')
  const meta = connections.find(c => c.platform === 'meta_ads')
  const gads = connections.find(c => c.platform === 'google_ads')
  const gsc  = connections.find(c => c.platform === 'search_console')

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
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-slate-400">
        To include additional data sources (LinkedIn Ads, TikTok, Shopify, etc.), upload a CSV in the <strong>Reports</strong> tab when generating a report.
      </p>
    </div>
  )
}
