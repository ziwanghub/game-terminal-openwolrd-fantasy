export type AiProvider = "external-code-agent" | "ollama" | "none";

const ALLOWED_PROVIDERS: AiProvider[] = ["external-code-agent", "ollama", "none"];

export function resolveAiProvider(): AiProvider {
  const raw = (process.env.AI_PROVIDER || "external-code-agent").trim().toLowerCase();
  if (ALLOWED_PROVIDERS.includes(raw as AiProvider)) {
    return raw as AiProvider;
  }
  return "external-code-agent";
}

export function isAiProviderConfigured(): boolean {
  return resolveAiProvider() !== "none";
}
