'use client'
import Link from 'next/link'
import { FileText, Link2, Calendar, ChevronRight, Building2, Globe, Mail } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Client, Report, Connection } from '@/types'

interface Props {
  client: Client
  reports: Report[]
  connections: Connection[]
  reportsLoading: boolean
  connectionsLoading: boolean
}

export default function OverviewTab({ client, reports, connections, reportsLoading, connectionsLoading }: Props) {
  const activeConnections = connections.filter(c => c.status === 'active').length
  const lastReport = reports[0] ?? null

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Total Reports</p>
            {reportsLoading ? (
              <div className="h-8 w-12 rounded bg-slate-100 animate-pulse mt-1" />
            ) : (
              <p className="text-3xl font-bold text-slate-800 mt-1">{reports.length}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Active Connections</p>
            {connectionsLoading ? (
              <div className="h-8 w-12 rounded bg-slate-100 animate-pulse mt-1" />
            ) : (
              <p className="text-3xl font-bold text-slate-800 mt-1">{activeConnections}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Last Report</p>
            {reportsLoading ? (
              <div className="h-8 w-28 rounded bg-slate-100 animate-pulse mt-1" />
            ) : lastReport ? (
              <p className="text-sm font-semibold text-slate-800 mt-1">
                {new Date(lastReport.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            ) : (
              <p className="text-sm text-slate-400 mt-1">None yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Client info summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base text-slate-700">Client Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {client.website_url && (
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <Globe className="h-4 w-4 text-slate-400 shrink-0" />
              <a href={client.website_url} target="_blank" rel="noopener noreferrer" className="text-indigo-700 hover:underline truncate">
                {client.website_url.replace(/^https?:\/\//, '')}
              </a>
            </div>
          )}
          {client.primary_contact_email && (
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <Mail className="h-4 w-4 text-slate-400 shrink-0" />
              <a href={`mailto:${client.primary_contact_email}`} className="text-indigo-700 hover:underline">{client.primary_contact_email}</a>
            </div>
          )}
          {client.industry && (
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <Building2 className="h-4 w-4 text-slate-400 shrink-0" />
              <span>{client.industry}</span>
            </div>
          )}
          {client.goals_context && (
            <div className="mt-2">
              <p className="text-xs font-medium text-slate-500 mb-1">Goals & context</p>
              <p className="text-sm text-slate-700 whitespace-pre-wrap bg-slate-50 rounded-lg p-3 border border-slate-100">{client.goals_context}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active connections summary */}
      {!connectionsLoading && connections.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700 flex items-center gap-2">
              <Link2 className="h-4 w-4 text-slate-400" />
              Connected Platforms
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {connections.filter(c => c.status === 'active').map(conn => (
                <span key={conn.id} className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-100 px-3 py-1 text-xs font-medium text-emerald-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {conn.account_name || conn.platform}
                </span>
              ))}
              {connections.filter(c => c.status !== 'active').map(conn => (
                <span key={conn.id} className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-100 px-3 py-1 text-xs font-medium text-amber-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  {conn.account_name || conn.platform} (expired)
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent reports */}
      {!reportsLoading && reports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base text-slate-700 flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-400" />
              Recent Reports
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-slate-100">
              {reports.slice(0, 3).map(report => (
                <li key={report.id}>
                  <Link href={`/dashboard/reports/${report.id}`} className="flex items-center justify-between py-3 hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors group">
                    <div className="flex items-start gap-3">
                      <FileText className="h-4 w-4 text-indigo-400 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-slate-800 group-hover:text-indigo-700 transition-colors">{report.title}</p>
                        <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                          <Calendar className="h-3 w-3" />
                          {report.period_start} → {report.period_end}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-500 transition-colors" />
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
