export interface IntentCard {
  schema_version: string;
  mission_id: string;
  mission_name: string;
  status: "active" | "completed" | "aborted" | "paused";
  created_at: string;
  updated_at: string;
  actors: {
    id: string;
    role: string;
  }[];
  tasks: {
    id: string;
    description: string;
    status: "pending" | "in_progress" | "completed" | "failed";
    assigned_to?: string;
  }[];
  context?: Record<string, unknown>;
}
