// Client reports list — all reports generated for this client
// See docs/reportpilot-feature-design-blueprint.md for reports wireframe

export default function ClientReportsPage({
  params,
}: {
  params: { clientId: string }
}) {
  return <div>Reports for client {params.clientId} — Coming soon</div>
}
