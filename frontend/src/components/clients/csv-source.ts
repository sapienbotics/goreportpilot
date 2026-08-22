import type { CSVSourcePayload } from '@/lib/api'

/**
 * A file the user has imported and attached to the report being generated.
 *
 * Holds the *whole* mapped payload rather than just the KPI list: a mapped
 * upload can also carry a daily series (which drives a trend chart) and an
 * entity breakdown, and both are lost if only `metrics` is passed along.
 */
export interface AttachedCSVSource {
  source: CSVSourcePayload
  fileName: string
}
