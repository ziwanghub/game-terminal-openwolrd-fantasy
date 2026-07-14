function isObjectLike(value: unknown): value is Record<string, unknown> | unknown[] {
  return (typeof value === "object" && value !== null) || Array.isArray(value);
}

export function deepFreeze<T>(value: T): T {
  if (!isObjectLike(value) || Object.isFrozen(value)) {
    return value;
  }

  Object.freeze(value);
  for (const nested of Object.values(value as Record<string, unknown>)) {
    if (isObjectLike(nested) && !Object.isFrozen(nested)) {
      deepFreeze(nested);
    }
  }

  return value;
}
