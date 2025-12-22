Draft a lesson entry based on the following information.

Requirements:
- Output ONLY Markdown (no code fences).
- Start with a single entry heading: `## <specific rule derived from the user correction>`.
- Then include 3 sections in order: `### Problem`, `### Cause`, `### Correct Approach`.
- Focus on what the USER suggested to fix/avoid the mistake; that is the key reusable lesson.
- Keep it concise (prefer bullets; avoid long prose; avoid generic “interrupted task” style titles).
- The `### Correct Approach` section MUST include the user correction verbatim as a short quote block.
- If the user correction is not actionable, rewrite it into a short actionable rule and put it as the first bullet in `### Correct Approach`.
- Do not include secrets or tokens.

Context:
- Incident status: {incident_status}
- Incident summary/reason:
{incident_summary}

- User correction / what should be done instead:
{user_correction}
