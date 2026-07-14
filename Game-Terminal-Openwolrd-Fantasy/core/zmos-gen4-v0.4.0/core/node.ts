import { promises as fs } from "node:fs";
import * as path from "node:path";

const ROOT_DIR = process.cwd();
const NODE_PATH = path.join(ROOT_DIR, ".z-mos", "node.json");

export type ZmosNodeIdentity = {
  node_id: string;
  node_role: string;
  runtime: string;
  capabilities: string[];
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function assertString(
  value: unknown,
  fieldPath: string,
): asserts value is string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid node identity: ${fieldPath} must be a non-empty string`);
  }
}

function assertStringArray(
  value: unknown,
  fieldPath: string,
): asserts value is string[] {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
    throw new Error(`Invalid node identity: ${fieldPath} must be an array of strings`);
  }
}

function validateNodeIdentity(value: unknown): ZmosNodeIdentity {
  if (!isObject(value)) {
    throw new Error("Invalid node identity: root value must be an object");
  }

  assertString(value.node_id, "node_id");
  assertString(value.node_role, "node_role");
  assertString(value.runtime, "runtime");
  assertStringArray(value.capabilities, "capabilities");

  return value as ZmosNodeIdentity;
}

export async function loadNodeIdentity(): Promise<ZmosNodeIdentity> {
  const rawNode = await fs.readFile(NODE_PATH, "utf8");
  let parsedNode: unknown;

  try {
    parsedNode = JSON.parse(rawNode) as unknown;
  } catch {
    throw new Error(`Invalid node identity: ${NODE_PATH} is not valid JSON`);
  }

  return validateNodeIdentity(parsedNode);
}

export function getNodePath(): string {
  return NODE_PATH;
}

export async function getNodeId(): Promise<string> {
  const node = await loadNodeIdentity();
  return node.node_id;
}

export async function getNodeRole(): Promise<string> {
  const node = await loadNodeIdentity();
  return node.node_role;
}
