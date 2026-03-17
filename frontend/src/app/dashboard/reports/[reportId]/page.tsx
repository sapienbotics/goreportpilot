// Report detail/preview page — view generated report content
// Shows AI narrative, charts, and metrics inline
// See docs/reportpilot-feature-design-blueprint.md for report preview wireframe

export default function ReportDetailPage({
  params,
}: {
  params: { reportId: string }
}) {
  return <div>Report {params.reportId} — Coming soon</div>
}
