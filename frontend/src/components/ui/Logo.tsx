"use client";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  variant?: "light" | "dark";
  className?: string;
}

export function Logo({ size = "md", variant = "light", className = "" }: LogoProps) {
  const sizes = {
    sm: { fontSize: 18, circleR: 8.5, svgWidth: 220, svgHeight: 34 },
    md: { fontSize: 23, circleR: 11, svgWidth: 280, svgHeight: 44 },
    lg: { fontSize: 30, circleR: 14, svgWidth: 360, svgHeight: 54 },
  };

  const s = sizes[size];
  const textColor = variant === "dark" ? "#F8FAFC" : "currentColor";
  const pilotColor = variant === "dark" ? "#818CF8" : "#4338CA";
  const brandColor = "#4338CA";

  // "G" x position
  const gX = 0;
  // Circle center for "o" — positioned after G
  const circleX = size === "sm" ? 22 : size === "md" ? 26 : 32;
  const circleY = s.svgHeight / 2;
  // "ReportPilot" starts after the circle
  const textX = circleX + s.circleR + (size === "sm" ? 4 : 5);
  const textY = s.svgHeight * 0.68;

  // Arrow inside circle
  const arrowStartX = circleX - s.circleR * 0.3;
  const arrowEndX = circleX + s.circleR * 0.4;
  const arrowTipSize = s.circleR * 0.32;

  return (
    <svg
      width={s.svgWidth}
      height={s.svgHeight}
      viewBox={`0 0 ${s.svgWidth} ${s.svgHeight}`}
      className={className}
      aria-label="GoReportPilot"
    >
      {/* G */}
      <text
        x={gX}
        y={textY}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize={s.fontSize}
        fontWeight="700"
        fill={brandColor}
      >
        G
      </text>

      {/* o — circle with forward arrow */}
      <circle
        cx={circleX}
        cy={circleY}
        r={s.circleR}
        fill="none"
        stroke={brandColor}
        strokeWidth={size === "sm" ? 2 : 2.5}
      />
      <line
        x1={arrowStartX}
        y1={circleY}
        x2={arrowEndX}
        y2={circleY}
        stroke={brandColor}
        strokeWidth={size === "sm" ? 1.5 : 2}
        strokeLinecap="round"
      />
      <polyline
        points={`${arrowEndX - arrowTipSize},${circleY - arrowTipSize} ${arrowEndX},${circleY} ${arrowEndX - arrowTipSize},${circleY + arrowTipSize}`}
        stroke={brandColor}
        strokeWidth={size === "sm" ? 1.5 : 2}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* ReportPilot */}
      <text
        x={textX}
        y={textY}
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize={s.fontSize}
        fontWeight="600"
        fill={textColor}
      >
        Report
        <tspan fill={pilotColor}>Pilot</tspan>
      </text>
    </svg>
  );
}
