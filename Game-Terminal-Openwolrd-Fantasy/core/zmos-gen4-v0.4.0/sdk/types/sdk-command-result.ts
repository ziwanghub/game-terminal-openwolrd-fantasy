export interface SdkCommandResult<T = void> {
  success: boolean;
  exitCode: number;
  output: string;
  error?: string;
  data?: T;
}
