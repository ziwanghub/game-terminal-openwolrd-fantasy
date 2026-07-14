export type ZmosSessionContract = {
  workspace: string;
  framework: string;
  sessionState: string;
  activeCommand: string | null;
  lastReport: string | null;
};
