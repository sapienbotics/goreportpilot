export function LogoIcon({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-label="GoReportPilot">
      <rect width="32" height="32" rx="7" fill="#4338CA" />
      <text
        x="4"
        y="23"
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="16"
        fontWeight="700"
        fill="white"
      >
        G
      </text>
      <circle cx="22" cy="16" r="7" fill="none" stroke="white" strokeWidth="1.8" />
      <line x1="19.5" y1="16" x2="25" y2="16" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
      <polyline
        points="23,13.5 25,16 23,18.5"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
