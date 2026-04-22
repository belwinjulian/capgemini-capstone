export const runtime = "nodejs";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const body = await req.json();
  const upstream = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(
      JSON.stringify({ error: `backend error ${upstream.status}` }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
    },
  });
}
