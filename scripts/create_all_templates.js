/**
 * ReportPilot — Generate all 3 PPTX templates.
 * Run: node scripts/create_all_templates.js
 */
const { execSync } = require("child_process");
const path = require("path");

const scripts = [
  "create_modern_clean.js",
  "create_dark_executive.js",
  "create_colorful_agency.js",
];

for (const script of scripts) {
  const full = path.join(__dirname, script);
  console.log(`\nBuilding: ${script}`);
  execSync(`node "${full}"`, { stdio: "inherit" });
}

console.log("\n\u2713 All 3 templates generated successfully.");
