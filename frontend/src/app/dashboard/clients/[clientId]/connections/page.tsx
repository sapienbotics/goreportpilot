// Client connections page — manage GA4, Meta Ads, Google Ads connections for this client
// Shows connected accounts, connection status, and OAuth connect buttons
// See docs/reportpilot-auth-integration-deepdive.md for OAuth flow

export default function ClientConnectionsPage({
  params,
}: {
  params: { clientId: string }
}) {
  return <div>Connections for client {params.clientId} — Coming soon</div>
}
