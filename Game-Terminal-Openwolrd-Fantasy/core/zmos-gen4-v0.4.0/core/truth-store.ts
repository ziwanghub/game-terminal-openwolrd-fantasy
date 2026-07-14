import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import * as path from "node:path";
import * as AjvImport from "ajv";
import * as AjvFormatsImport from "ajv-formats";

const ROOT_DIR = process.cwd();
const ZMOS_DIR = path.join(ROOT_DIR, ".z-mos");
const TRUTH_FILE = path.join(ZMOS_DIR, "truth.contract.json");
const TRUTH_SCHEMA_FILE = path.join(ZMOS_DIR, "schemas", "truth.contract.schema.json");

type TruthWriteOptions = {
  simulateFailureAfterBackup?: boolean;
  now?: Date;
};

export type TruthWriteResult = {
  truthPath: string;
  backupPath: string | null;
  contractHash: string;
};

function buildAjv(): any {
  const AjvCtor =
    (AjvImport as unknown as { default?: new (opts: unknown) => any }).default ??
    (AjvImport as unknown as new (opts: unknown) => any);
  const ajv = new AjvCtor({ strict: true, allErrors: true, validateSchema: true });
  const addFormatsFn =
    (AjvFormatsImport as unknown as { default?: (instance: unknown) => void }).default ??
    (AjvFormatsImport as unknown as (instance: unknown) => void);
  addFormatsFn(ajv);
  return ajv;
}

function buildBackupPath(now: Date): string {
  const stamp = now.toISOString().replace(/[:.]/g, "-");
  return path.join(ZMOS_DIR, `truth.backup.${stamp}.json`);
}

function hashContent(content: string): string {
  return createHash("sha256").update(content).digest("hex");
}

async function fileExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

export async function validateTruthContractPayload(payload: unknown): Promise<void> {
  const schemaRaw = await fs.readFile(TRUTH_SCHEMA_FILE, "utf8");
  const schema = JSON.parse(schemaRaw) as unknown;
  const ajv = buildAjv();
  const schemaValid = ajv.validateSchema(schema);
  if (!schemaValid) {
    const details = (ajv.errors || [])
      .map((err: any) => `${err.instancePath || "/"} ${err.message || "schema validation error"}`)
      .join("; ");
    throw new Error(`truth schema invalid: ${details}`);
  }

  const validate = ajv.compile(schema);
  const validPayload = validate(payload);
  if (!validPayload) {
    const details = (validate.errors || [])
      .map((err: any) => `${err.instancePath || "/"} ${err.message || "payload validation error"}`)
      .join("; ");
    throw new Error(`truth payload invalid: ${details}`);
  }
}

export async function writeTruthContractAtomic(
  payload: unknown,
  options: TruthWriteOptions = {},
): Promise<TruthWriteResult> {
  await fs.mkdir(ZMOS_DIR, { recursive: true });

  const now = options.now ?? new Date();
  const tempPath = path.join(
    ZMOS_DIR,
    `.truth.contract.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`,
  );

  const content = `${JSON.stringify(payload, null, 2)}\n`;
  let backupPath: string | null = null;

  try {
    await fs.writeFile(tempPath, content, "utf8");

    const parsedTemp = JSON.parse(await fs.readFile(tempPath, "utf8")) as unknown;
    await validateTruthContractPayload(parsedTemp);

    const contractHash = hashContent(await fs.readFile(tempPath, "utf8"));

    if (await fileExists(TRUTH_FILE)) {
      backupPath = buildBackupPath(now);
      await fs.copyFile(TRUTH_FILE, backupPath);
    }

    if (options.simulateFailureAfterBackup) {
      throw new Error("simulated failure after backup");
    }

    await fs.rename(tempPath, TRUTH_FILE);
    return {
      truthPath: TRUTH_FILE,
      backupPath,
      contractHash,
    };
  } finally {
    if (await fileExists(tempPath)) {
      await fs.unlink(tempPath).catch(() => undefined);
    }
  }
}
