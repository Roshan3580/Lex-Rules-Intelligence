/**
 * Lex Intelligence API — browser client stub (Brief §4.7).
 * Point `baseUrl` at your FastAPI origin.
 */
export type ClientOptions = { baseUrl?: string };

export async function validateSubmission(
  baseUrl: string,
  body: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const r = await fetch(`${baseUrl.replace(/\/$/, "")}/api/validate-submission`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as Record<string, unknown>;
}

export async function submissionPath(
  baseUrl: string,
  q: { state: string; tax_category: string; workflow_stage?: string },
): Promise<Record<string, unknown>> {
  const p = new URLSearchParams(q as Record<string, string>);
  const r = await fetch(`${baseUrl.replace(/\/$/, "")}/api/submission-path?${p}`);
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as Record<string, unknown>;
}
