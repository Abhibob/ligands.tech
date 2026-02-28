import type { LlmParsedQuery } from '../types/resolution.ts';

const MODAL_ENDPOINT =
  'https://scott-steele--gpt-oss-120b-serve.modal.run/v1/chat/completions';

const SYSTEM_PROMPT = `You are a molecular biology query parser. Given a natural language question about proteins, ligands, or drug binding, extract structured information.

Respond with ONLY a JSON object (no markdown, no explanation):
{
  "intent": "bind" | "view_protein" | "view_ligand" | "unknown",
  "proteinName": "<gene name or null>",
  "ligandName": "<drug/compound name or null>"
}

Examples:
- "Does erlotinib bind EGFR?" → {"intent":"bind","proteinName":"EGFR","ligandName":"erlotinib"}
- "Show me the p53 structure" → {"intent":"view_protein","proteinName":"TP53","ligandName":null}
- "What does aspirin look like?" → {"intent":"view_ligand","proteinName":null,"ligandName":"aspirin"}`;

/**
 * Send a natural language query to the LLM endpoint and parse the structured response.
 */
export async function parseLlmQuery(
  userQuery: string,
  apiKey: string,
): Promise<LlmParsedQuery> {
  const resp = await fetch(MODAL_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'gpt-oss-120b',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: userQuery },
      ],
      temperature: 0,
      max_tokens: 200,
    }),
  });

  if (!resp.ok) {
    const status = resp.status;
    if (status === 503) {
      throw new Error('LLM endpoint is cold-starting. Please wait 1-2 minutes and try again.');
    }
    throw new Error(`LLM request failed (${status})`);
  }

  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content ?? '';

  try {
    const parsed = JSON.parse(content);
    return {
      intent: parsed.intent ?? 'unknown',
      proteinName: parsed.proteinName ?? null,
      ligandName: parsed.ligandName ?? null,
      raw: userQuery,
    };
  } catch {
    throw new Error(`Could not parse LLM response: ${content.slice(0, 200)}`);
  }
}
