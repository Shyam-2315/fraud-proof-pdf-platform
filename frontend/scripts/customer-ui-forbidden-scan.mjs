import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(scriptDir, "..");

const customerFiles = [
  "src/components/AccountUsageCard.tsx",
  "src/components/Footer.tsx",
  "src/components/Navbar.tsx",
  "src/components/PdfForm.tsx",
  "src/components/PdfHistoryTable.tsx",
  "src/components/PricingCard.tsx",
  "src/components/UsageCard.tsx",
  "src/pages/AccountPage.tsx",
  "src/pages/GeneratePage.tsx",
  "src/pages/HistoryPage.tsx",
  "src/pages/LandingPage.tsx",
  "src/pages/LoginPage.tsx",
  "src/pages/PricingPage.tsx",
  "src/pages/SignupPage.tsx",
  "src/pages/UsagePage.tsx",
];

const forbidden = [
  { label: "admin", pattern: /\/admin|\badmin\b/i },
  { label: "fraud", pattern: /\bfraud\b/i },
  { label: "risk", pattern: /\brisk\b/i },
  { label: "suspicious", pattern: /\bsuspicious\b/i },
  { label: "abuse", pattern: /\babuse\b/i },
  { label: "fingerprint", pattern: /\bfingerprint\b/i },
  { label: "tracking", pattern: /\btracking\b/i },
  { label: "ml", pattern: /\bml\b/i },
  { label: "visitor investigation", pattern: /visitor investigation/i },
  { label: "IP monitoring", pattern: /ip monitoring/i },
  { label: "user-agent", pattern: /user-agent/i },
  { label: "security engine", pattern: /security engine/i },
];

const failures = [];

for (const file of customerFiles) {
  const path = resolve(frontendRoot, file);
  const content = readFileSync(path, "utf8");
  for (const term of forbidden) {
    if (term.pattern.test(content)) {
      failures.push(`${file}: ${term.label}`);
    }
  }
}

if (failures.length > 0) {
  console.error("Customer UI forbidden-word scan failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Customer UI forbidden-word scan passed.");
