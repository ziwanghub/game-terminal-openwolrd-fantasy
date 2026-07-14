import { accessSync, constants, existsSync, realpathSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const expectedDistGateway = path.join(rootDir, "dist", "cli", "gateway.js");

function fail(code, likelyCause, nextAction) {
  console.error(`zcl preflight error [${code}]`);
  console.error(`what failed: dist integrity validation`);
  console.error(`likely cause: ${likelyCause}`);
  console.error(`next action: ${nextAction}`);
  process.exit(1);
}

if (!existsSync(expectedDistGateway)) {
  fail(
    "dist-missing",
    "dist/cli/gateway.js is missing",
    "run npm run ops:build and retry operator command",
  );
}

try {
  accessSync(expectedDistGateway, constants.R_OK);
} catch {
  fail(
    "dist-unreadable",
    "dist gateway exists but is not readable",
    "check file permissions, rerun npm run ops:build, then retry",
  );
}

let resolvedPath;
try {
  resolvedPath = realpathSync(expectedDistGateway);
} catch {
  fail(
    "dist-invalid-path",
    "dist gateway path cannot be resolved",
    "rebuild dist and verify dist/cli/gateway.js path",
  );
}

const expectedResolvedPrefix = realpathSync(path.join(rootDir, "dist", "cli"));
if (!resolvedPath.startsWith(expectedResolvedPrefix)) {
  fail(
    "dist-path-mismatch",
    "resolved dist gateway path does not point to intended dist/cli artifact",
    "clean dist, rebuild, and verify operator path uses dist/cli/gateway.js",
  );
}

console.error("zcl preflight: dist integrity check passed");
console.error(`zcl preflight: dist entry=${resolvedPath}`);
