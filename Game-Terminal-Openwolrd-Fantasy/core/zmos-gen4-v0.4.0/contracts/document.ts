export const DOCUMENT_STATUSES = [
  "draft",
  "active",
  "revised",
  "superseded",
  "archived",
] as const;

export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export const DOCUMENT_TYPES = [
  "runlog",
  "case",
  "playbook",
  "manual",
  "policy",
  "report",
  "guide",
] as const;

export type DocumentType = (typeof DOCUMENT_TYPES)[number];

export type ZmosDocumentContract = {
  document_id: string;
  document_type: DocumentType;
  project_code: string;
  phase: string;
  version: string;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  related_trace_ids?: string[];
  related_commands?: string[];
  superseded_by?: string;
};

export const DOCUMENT_FILENAME_PATTERN =
  /^ZMOS-([A-Z0-9]+)-([A-Z0-9]+)-([A-Z0-9]+)-(\d{4})-(\d{3})-([A-Z0-9-]+)\.md$/;

export type DocumentFilenameParts = {
  type: string;
  project: string;
  phase: string;
  year: string;
  seq: string;
  title: string;
};

export function parseDocumentFilename(filename: string): DocumentFilenameParts | null {
  const match = filename.match(DOCUMENT_FILENAME_PATTERN);
  if (!match) {
    return null;
  }

  return {
    type: match[1],
    project: match[2],
    phase: match[3],
    year: match[4],
    seq: match[5],
    title: match[6],
  };
}

export function normalizeDocumentType(value: string): string {
  return value.trim().toLowerCase();
}

export function normalizeDocumentToken(value: string): string {
  return value.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "-");
}
