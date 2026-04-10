/**
 * Timezone helpers for the scheduled reports UI.
 *
 * The backend stores and processes every schedule in UTC.
 * The frontend lets the user pick a local time + IANA timezone,
 * and converts to/from UTC using only `Intl.DateTimeFormat` —
 * no external date libraries.
 */

export interface TimezoneOption {
  value: string // IANA name, e.g. "Asia/Kolkata"
  label: string // Friendly label shown in the dropdown
}

export const TIMEZONE_OPTIONS: TimezoneOption[] = [
  { value: 'UTC',                 label: 'UTC' },
  { value: 'Asia/Kolkata',        label: 'India — IST (UTC+5:30)' },
  { value: 'America/New_York',    label: 'US Eastern — ET (EST/EDT)' },
  { value: 'America/Chicago',     label: 'US Central — CT (CST/CDT)' },
  { value: 'America/Denver',      label: 'US Mountain — MT (MST/MDT)' },
  { value: 'America/Los_Angeles', label: 'US Pacific — PT (PST/PDT)' },
  { value: 'Europe/London',       label: 'UK — GMT/BST' },
  { value: 'Europe/Berlin',       label: 'Central Europe — CET/CEST' },
  { value: 'Australia/Sydney',    label: 'Sydney — AEST/AEDT' },
]

/**
 * Detect the user's IANA timezone via the browser.
 * Falls back to "UTC" if unavailable (e.g. SSR).
 * If the detected zone isn't in TIMEZONE_OPTIONS, it is still returned
 * unchanged so the caller can keep it as the default; the dropdown
 * will simply fall back to UTC for display.
 */
export function detectUserTimezone(): string {
  try {
    if (typeof Intl === 'undefined') return 'UTC'
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    return tz || 'UTC'
  } catch {
    return 'UTC'
  }
}

/**
 * Snap a detected timezone to the closest entry in TIMEZONE_OPTIONS.
 * If the exact IANA name is in the list, return it. Otherwise return 'UTC'.
 */
export function snapToKnownTimezone(tz: string): string {
  return TIMEZONE_OPTIONS.some(o => o.value === tz) ? tz : 'UTC'
}

/**
 * Get the offset (in minutes) of an IANA timezone relative to UTC
 * at a given moment. Positive = east of UTC (e.g. IST = +330).
 */
function getTimezoneOffsetMinutes(tz: string, referenceUtc: Date): number {
  if (tz === 'UTC') return 0
  const dtf = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    hour12:   false,
    year:     'numeric',
    month:    '2-digit',
    day:      '2-digit',
    hour:     '2-digit',
    minute:   '2-digit',
    second:   '2-digit',
  })
  const parts = dtf.formatToParts(referenceUtc)
  const lookup = (type: string): number => {
    const v = parts.find(p => p.type === type)?.value
    return v ? Number(v) : 0
  }
  // `hour` can come back as "24" on some engines at midnight boundaries.
  let hour = lookup('hour')
  if (hour === 24) hour = 0
  const asUtc = Date.UTC(
    lookup('year'),
    lookup('month') - 1,
    lookup('day'),
    hour,
    lookup('minute'),
    lookup('second'),
  )
  return Math.round((asUtc - referenceUtc.getTime()) / 60000)
}

/** Pad a number to 2 digits ("9" → "09"). */
function pad2(n: number): string {
  return n.toString().padStart(2, '0')
}

/** Normalise a time string into numeric HH, MM (safe against "9:5", "09:05"). */
function parseHHMM(time: string): [number, number] {
  const [rawH, rawM] = (time || '00:00').split(':')
  const h = Number(rawH) || 0
  const m = Number(rawM) || 0
  return [h, m]
}

/** Format HH and MM (possibly out-of-range) into a normalised "HH:MM". */
function formatHHMM(h: number, m: number): string {
  // Wrap hours into 0..23
  let total = h * 60 + m
  total = ((total % 1440) + 1440) % 1440
  const hh = Math.floor(total / 60)
  const mm = total % 60
  return `${pad2(hh)}:${pad2(mm)}`
}

/**
 * Convert an "HH:MM" local time in the given IANA timezone
 * into the equivalent "HH:MM" in UTC.
 *
 * Uses today's date as the reference moment so DST is respected.
 *
 * Example: localTimeToUtc("09:00", "Asia/Kolkata") → "03:30"
 */
export function localTimeToUtc(time: string, tz: string): string {
  const [h, m] = parseHHMM(time)
  if (tz === 'UTC') return formatHHMM(h, m)
  const offsetMin = getTimezoneOffsetMinutes(tz, new Date())
  // local = UTC + offset  ⇒  UTC = local − offset
  return formatHHMM(h, m - offsetMin)
}

/**
 * Convert an "HH:MM" UTC time into the equivalent "HH:MM" in the
 * given IANA timezone. Uses today's date as the reference moment.
 *
 * Example: utcToLocalTime("03:30", "Asia/Kolkata") → "09:00"
 */
export function utcToLocalTime(time: string, tz: string): string {
  const [h, m] = parseHHMM(time)
  if (tz === 'UTC') return formatHHMM(h, m)
  const offsetMin = getTimezoneOffsetMinutes(tz, new Date())
  // local = UTC + offset
  return formatHHMM(h, m + offsetMin)
}

/**
 * Friendly short label for a timezone (for inline display).
 * Returns the entry's label if known, else the raw IANA name.
 */
export function getTimezoneShortLabel(tz: string): string {
  const opt = TIMEZONE_OPTIONS.find(o => o.value === tz)
  return opt ? opt.label : tz
}
