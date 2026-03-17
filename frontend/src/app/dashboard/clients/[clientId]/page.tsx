// Client detail page — shows client info, connected platforms, recent reports
// See docs/reportpilot-feature-design-blueprint.md for client detail wireframe

export default function ClientDetailPage({
  params,
}: {
  params: { clientId: string }
}) {
  return <div>Client {params.clientId} — Coming soon</div>
}
