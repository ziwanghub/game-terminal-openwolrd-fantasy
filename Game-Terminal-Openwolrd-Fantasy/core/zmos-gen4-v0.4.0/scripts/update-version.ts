import { existsSync, readFileSync, writeFileSync } from 'fs';

const newVersion = process.argv[2];

if (!newVersion) {
  console.error('❌ Usage: npm run update-version -- 3.1.0');
  process.exit(1);
}

console.log(`🔄 Updating project version to v${newVersion}...`);

// Update sdk/version.ts (single source of truth)
let versionTs = readFileSync('sdk/version.ts', 'utf-8');
versionTs = versionTs.replace(/export const VERSION = ".*?";/, `export const VERSION = "${newVersion}";`);
versionTs = versionTs.replace(/export const SDK_VERSION = ".*?";/, `export const SDK_VERSION = "${newVersion}";`);
versionTs = versionTs.replace(/export const FULL_VERSION = ".*?";/, `export const FULL_VERSION = "v${newVersion} \\"Purity\\"";`);
versionTs = versionTs.replace(/export const SCHEMA_VERSION_AGENT = ".*?";/, `export const SCHEMA_VERSION_AGENT = "${newVersion}-agent";`);
writeFileSync('sdk/version.ts', versionTs);
console.log(`✅ Updated sdk/version.ts → v${newVersion}`);

// Update common docs/package references (content only, no filename rewrites)
const files = [
  'package.json',
  'docs/AGENT-HANDBOOK.md',
  'docs/ARCHITECTURE.md',
  'docs/COMMUNICATION-STANDARD.md'
];

for (const file of files) {
  if (!existsSync(file)) continue;
  let text = readFileSync(file, 'utf-8');

  // Replace textual runtime/version labels only
  text = text.replace(/v\d+\.\d+\.\d+ \"Purity\"/g, `v${newVersion} \"Purity\"`);
  text = text.replace(/Z-MOS v\d+\.\d+\.\d+/g, `Z-MOS v${newVersion}`);

  if (file === 'package.json') {
    text = text.replace(/"version"\s*:\s*"\d+\.\d+\.\d+"/, `"version": "${newVersion}"`);
  }

  writeFileSync(file, text);
  console.log(`✅ Updated ${file}`);
}

console.log(`\n🎉 Successfully updated to v${newVersion}`);
console.log('Run: npm run build && npm test to verify');
