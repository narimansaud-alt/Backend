const secretPatterns = [
  /(?:bearer|token|api[_-]?key|password|cookie|authorization)[=: ]+[^\s,;]+/gi,
  /[?&](?:token|key|secret|email)=[^&#\s]+/gi,
  /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g,
];

export function sanitizeText(input: string) {
  return secretPatterns.reduce((value, pattern) => value.replace(pattern, "[REDACTED]"), input).slice(0, 4000);
}

export function sanitizeError(value: unknown) {
  const error = value instanceof Error ? value : new Error(typeof value === "string" ? value : "Неизвестная ошибка клиента");
  return { message: sanitizeText(error.message), stack: error.stack ? sanitizeText(error.stack) : undefined, browser: typeof navigator === "undefined" ? "server" : navigator.userAgent.slice(0, 300) };
}
