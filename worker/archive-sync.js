/*
 * archive-sync — a Cloudflare Worker holding the catalogue's records so the
 * site can save edits instead of only downloading them.
 *
 * It stores one opaque blob and never sees the collection. The records are
 * encrypted in the browser under the same passphrase that unlocks the site, so
 * this Worker, its KV store and Cloudflare itself hold nothing but ciphertext.
 *
 * Two tokens, so that reading and writing are separate privileges:
 *
 *   GET  /records  -> {version, updated, blob} | 404 when nothing is stored yet
 *                     accepts either token
 *   PUT  /records  <- {version, blob}          -> {version, updated}
 *                     accepts only WRITE_TOKEN
 *
 * The read token is carried inside the site, so unlocking with the everyday
 * passphrase is enough to see other people's edits. The write token is sealed
 * again under a second, randomly generated passphrase, so someone who can read
 * the archive still cannot save to it without being given that separately.
 *
 * PUT is a compare-and-set: `version` must match what is stored, or 0 for the
 * first write. A mismatch returns 409 so a second device cannot silently
 * clobber edits it never saw.
 *
 * Bindings: ARCHIVE (KV namespace), READ_TOKEN and WRITE_TOKEN (secrets),
 * ORIGIN (site URL).
 */

const KEY = "records";
const MAX_BLOB = 8 * 1024 * 1024; // generous for the records; plates never come here

const json = (body, status, origin, extra) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
      ...cors(origin),
      ...extra,
    },
  });

const cors = origin => ({
  "access-control-allow-origin": origin,
  "access-control-allow-methods": "GET,PUT,OPTIONS",
  "access-control-allow-headers": "authorization,content-type",
  "access-control-max-age": "86400",
  vary: "origin",
});

/*
 * A token reaches the Worker either as a plain string (a Worker secret set in
 * Settings -> Variables and Secrets) or as a Secrets Store binding, which hands
 * the value back through .get(). Accept both, so how it was wired up in the
 * dashboard does not change whether this works.
 */
async function secret(binding) {
  if (!binding) return null;
  if (typeof binding === "string") return binding;
  if (typeof binding.get === "function") return await binding.get();
  return null;
}

/* Length-independent comparison, so a wrong token leaks nothing by timing. */
function tokenOk(given, expected) {
  if (typeof given !== "string" || typeof expected !== "string") return false;
  const a = new TextEncoder().encode(given);
  const b = new TextEncoder().encode(expected);
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a[i] ?? 0) ^ (b[i] ?? 0);
  }
  return diff === 0;
}

export default {
  async fetch(request, env) {
    const origin = env.ORIGIN || "*";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors(origin) });
    }

    const url = new URL(request.url);
    if (url.pathname !== "/records") {
      return json({ error: "not found" }, 404, origin);
    }

    const [readToken, writeToken] = await Promise.all([
      secret(env.READ_TOKEN),
      secret(env.WRITE_TOKEN),
    ]);
    if (!readToken || !writeToken) {
      return json({ error: "worker is missing its tokens" }, 500, origin);
    }
    if (readToken === writeToken) {
      // Otherwise the read token would silently grant writing, which is the one
      // thing this split exists to prevent.
      return json({ error: "read and write tokens must differ" }, 500, origin);
    }

    const auth = request.headers.get("authorization") || "";
    const given = auth.startsWith("Bearer ") ? auth.slice(7) : "";
    const canWrite = tokenOk(given, writeToken);
    const canRead = canWrite || tokenOk(given, readToken);
    if (!canRead) {
      return json({ error: "unauthorized" }, 401, origin);
    }

    if (request.method === "GET") {
      const stored = await env.ARCHIVE.get(KEY, { type: "json" });
      if (!stored) return json({ error: "empty" }, 404, origin);
      return json(stored, 200, origin);
    }

    if (request.method === "PUT") {
      // Reading is not enough to save. This is the whole point of the second
      // passphrase, so it is checked before anything is parsed.
      if (!canWrite) {
        return json({ error: "read-only token" }, 403, origin);
      }

      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "malformed json" }, 400, origin);
      }

      if (typeof body?.blob !== "string" || !body.blob) {
        return json({ error: "missing blob" }, 400, origin);
      }
      if (body.blob.length > MAX_BLOB) {
        return json({ error: "blob too large" }, 413, origin);
      }
      if (!Number.isInteger(body.version) || body.version < 0) {
        return json({ error: "missing version" }, 400, origin);
      }

      const stored = await env.ARCHIVE.get(KEY, { type: "json" });
      const current = stored ? stored.version : 0;
      if (body.version !== current) {
        // Somebody else saved since this tab loaded. Say so rather than
        // overwriting work this client never saw.
        return json(
          { error: "stale", version: current, updated: stored?.updated ?? null },
          409,
          origin
        );
      }

      const next = {
        version: current + 1,
        updated: new Date().toISOString(),
        blob: body.blob,
      };
      await env.ARCHIVE.put(KEY, JSON.stringify(next));
      return json({ version: next.version, updated: next.updated }, 200, origin);
    }

    return json({ error: "method not allowed" }, 405, origin);
  },
};
