import { promises as fs } from "node:fs";
import * as path from "node:path";
import * as AjvImport from "ajv";
import * as AjvFormatsImport from "ajv-formats";

type SchemaCheck = {
  file: string;
  ok: boolean;
  details: string[];
};

const SCHEMA_DIR = path.join(process.cwd(), ".z-mos", "schemas");
const SCHEMA_FILES = [
  "truth.contract.schema.json",
  "intent.card.schema.json",
  "trace.record.schema.json",
] as const;

async function readJson(filePath: string): Promise<unknown> {
  return JSON.parse(await fs.readFile(filePath, "utf8")) as unknown;
}

function formatCheckLine(label: string, ok: boolean): string {
  return `${label.padEnd(28, " ")} ${ok ? "PASS" : "FAIL"}`;
}

export async function runSchemaValidateCommand(): Promise<void> {
  const AjvCtor =
    (AjvImport as unknown as { default?: new (opts: unknown) => any }).default ??
    (AjvImport as unknown as new (opts: unknown) => any);
  const ajv = new AjvCtor({ strict: true, allErrors: true, validateSchema: true });
  const addFormatsFn =
    (AjvFormatsImport as unknown as { default?: (instance: unknown) => void }).default ??
    (AjvFormatsImport as unknown as (instance: unknown) => void);
  addFormatsFn(ajv);
  const checks: SchemaCheck[] = [];
  const schemaObjects = new Map<string, unknown>();
  let failed = false;

  for (const file of SCHEMA_FILES) {
    const fullPath = path.join(SCHEMA_DIR, file);
    const errors: string[] = [];
    let ok = true;
    let parsed: unknown = null;

    try {
      parsed = await readJson(fullPath);
      schemaObjects.set(file, parsed);
    } catch (error) {
      ok = false;
      errors.push(
        `Cannot read/parse schema: ${error instanceof Error ? error.message : String(error)}`,
      );
    }

    if (ok) {
      const validSchema = ajv.validateSchema(parsed);
      if (!validSchema) {
        ok = false;
        const schemaErrors = ajv.errors ?? [];
        for (const err of schemaErrors) {
          errors.push(
            `Schema invalid (${err.instancePath || "/"}): ${err.message || "unknown error"}`,
          );
        }
      }
    }

    checks.push({ file, ok, details: errors });
    if (!ok) {
      failed = true;
    }
  }

  const instanceChecks: SchemaCheck[] = [];
  const candidates: Array<{ file: string; schema: string }> = [
    { file: path.join(process.cwd(), ".z-mos", "truth.contract.json"), schema: "truth.contract.schema.json" },
    { file: path.join(process.cwd(), ".z-mos", "intent.card.json"), schema: "intent.card.schema.json" },
  ];

  for (const candidate of candidates) {
    try {
      await fs.access(candidate.file);
    } catch {
      continue;
    }

    const label = path.relative(process.cwd(), candidate.file);
    const schemaObj = schemaObjects.get(candidate.schema);
    if (!schemaObj) {
      failed = true;
      instanceChecks.push({
        file: label,
        ok: false,
        details: [`Missing loaded schema dependency: ${candidate.schema}`],
      });
      continue;
    }

    const validate = ajv.compile(schemaObj);
    let ok = true;
    const details: string[] = [];

    try {
      const payload = await readJson(candidate.file);
      const valid = validate(payload);
      if (!valid) {
        ok = false;
        for (const err of validate.errors ?? []) {
          details.push(
            `Instance invalid (${err.instancePath || "/"}): ${err.message || "unknown error"}`,
          );
        }
      }
    } catch (error) {
      ok = false;
      details.push(
        `Cannot read/parse instance: ${error instanceof Error ? error.message : String(error)}`,
      );
    }

    if (!ok) {
      failed = true;
    }
    instanceChecks.push({ file: label, ok, details });
  }

  console.log("Z-MOS SCHEMA VALIDATION");
  console.log("----------------------");
  for (const check of checks) {
    console.log(formatCheckLine(check.file, check.ok));
    if (!check.ok) {
      for (const detail of check.details) {
        console.log(`  - ${detail}`);
      }
    }
  }

  if (instanceChecks.length > 0) {
    console.log("");
    console.log("INSTANCE CHECKS");
    console.log("---------------");
    for (const check of instanceChecks) {
      console.log(formatCheckLine(check.file, check.ok));
      if (!check.ok) {
        for (const detail of check.details) {
          console.log(`  - ${detail}`);
        }
      }
    }
  }

  console.log("");
  console.log(`VERDICT: ${failed ? "FAIL" : "PASS"}`);
  process.exitCode = failed ? 1 : 0;
}
