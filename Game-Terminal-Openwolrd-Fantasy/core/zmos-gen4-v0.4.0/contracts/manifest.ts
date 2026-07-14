export type ManifestRepository = {
  name: string;
  framework: string;
  version: string;
};

export type ManifestWorkspace = {
  root: string;
  stateDir: string;
  traceDir: string;
};

export type ManifestRuntime = {
  platform: string;
  moduleSystem: string;
  entryCommand: string;
};

export type ManifestStatus = {
  stage: string;
  aiCli: string;
};

export type ManifestLifecycleStatus =
  | "active"
  | "freeze"
  | "archived"
  | "stabilized"
  | "unknown";

export type ManifestLifecycle = {
  status: ManifestLifecycleStatus;
  updatedAt: string;
  reason: string;
};

export type ManifestScope = {
  mutation: {
    mode: "strict" | "warn";
    allowedPaths: string[];
    protectedPaths: string[];
  };
};

export type ZmosManifestContract = {
  repository: ManifestRepository;
  workspace: ManifestWorkspace;
  runtime: ManifestRuntime;
  status: ManifestStatus;
  lifecycle: ManifestLifecycle;
  scope: ManifestScope;
};
