// AI helper: POST /api/ask
// Body: { messages: [{role: "user"|"assistant", content: string}], lang: "en"|"he", services: [TMDB provider ids the user has] }
// Header: Authorization: Bearer <Supabase access token of a signed-in user>
// Returns: { message: string, ids: [title ids] }
//
// Claude answers by searching the real catalog through tools that call the Supabase database,
// so it can only recommend titles that exist on the site. Needs ANTHROPIC_API_KEY in Vercel.

const SB_URL = "https://prnfnqvjirwuyafvsulk.supabase.co";
const SB_KEY = "sb_publishable_mxaPvh6JxrmWlaOuR4LVkA_q0ll9ESM"; // public key; row-level security protects user data
const MODEL = process.env.AI_MODEL || "claude-sonnet-5-5";
const DAILY_LIMIT = Number(process.env.AI_DAILY_LIMIT || 40);
const MAX_ROUNDS = 6;

// Streaming services in Israel the catalog knows (TMDB / JustWatch provider ids)
// Disney+ comes from its US catalog (not tracked for Israel)
const SERVICES = { "Netflix": 8, "HBO Max": 1899, "Amazon Prime Video": 119, "Apple TV": 350, "Disney+": 337 };
const SERVICE_NAME = Object.fromEntries(Object.entries(SERVICES).map(([n, id]) => [id, n]));

const TOOLS = [
  {
    name: "find_titles",
    description:
      "Search the catalog of US and Israeli movies and TV series (1980–today) by any combination of filters. " +
      "Results are sorted by popularity (IMDb votes). Every filter is optional. Use several calls with different filters when helpful.",
    input_schema: {
      type: "object",
      properties: {
        person: { type: "string", description: "Actor, director, writer or creator name in English or Hebrew, e.g. 'James McAvoy'. Partial names work." },
        person_role: { type: "string", enum: ["cast", "director", "writer", "creator", "composer"] },
        genre: { type: "string", description: "One broad genre in English: Horror, Comedy, Drama, Thriller, Crime, Romance, Animation, Documentary, Science Fiction, Fantasy, Action, Adventure, Mystery, Family, War, Western, History, Music. TV series use TV genres instead: Drama, Comedy, Crime, Mystery, Reality, Sci-Fi & Fantasy, Action & Adventure, War & Politics, Kids — there is no 'Thriller' genre for TV, use tag 'thriller' or genre Mystery/Crime." },
        tag: { type: "string", description: "A subgenre, theme or keyword, matched inside each title's tags (detailed genres + TMDB keywords). Examples: 'psychological' (finds psychological horror/thriller/drama), 'psychological horror', 'thriller', 'time travel', 'heist', 'serial killer', 'twist ending', 'based on novel', 'coming of age', 'dystopia', 'mockumentary', 'true story'. One tag per call; combine with genre/type/scores." },
        title_type: { type: "string", enum: ["movie", "tv"] },
        min_year: { type: "integer" }, max_year: { type: "integer" },
        min_imdb: { type: "number", description: "Minimum IMDb rating, 0–10" },
        min_rt: { type: "integer", description: "Minimum Rotten Tomatoes score, 0–100 (mostly available for movies)" },
        min_mc: { type: "integer", description: "Minimum Metacritic score, 0–100 (mostly available for movies)" },
        israeli: { type: "boolean", description: "true for Israeli titles only, false for non-Israeli only" },
        min_votes: { type: "integer", description: "Minimum number of IMDb votes, to skip obscure titles (e.g. 5000)" },
        on_my_services: { type: "boolean", description: "true to return only titles streaming in Israel on the user's own streaming services" },
        service: { type: "string", enum: Object.keys(SERVICES), description: "Only titles streaming in Israel on this service" },
        limit: { type: "integer", description: "Max results, default 15, max 40" },
      },
    },
  },
  {
    name: "search_by_name",
    description: "Look up titles by their English or Hebrew name, e.g. to learn about a title the user mentions ('something like Fauda').",
    input_schema: { type: "object", properties: { name: { type: "string" } }, required: ["name"] },
  },
  {
    name: "present_results",
    description:
      "Give the user your answer. Always finish by calling this exactly once. 'message' is a short reply in the user's language " +
      "(a sentence or two of framing, plus one short line per pick saying why it fits). 'title_ids' are the ids of the titles you " +
      "recommend, best first, taken only from tool results. If nothing matches all the user's conditions, say so plainly and offer the closest matches.",
    input_schema: {
      type: "object",
      properties: { message: { type: "string" }, title_ids: { type: "array", items: { type: "string" }, maxItems: 12 } },
      required: ["message", "title_ids"],
    },
  },
];

const sbHeaders = token => ({ apikey: SB_KEY, Authorization: `Bearer ${token || SB_KEY}`, "Content-Type": "application/json" });

function slim(t) {
  return {
    id: t.id, title: t.title, title_he: t.title_he || undefined, type: t.type, year: t.year, end_year: t.end_year || undefined,
    israeli: t.israeli || undefined, genres: (t.genres || []).slice(0, 4), imdb: t.imdb_rating, votes: t.imdb_votes,
    rotten_tomatoes: t.rt_score ?? undefined, metacritic: t.mc_score ?? undefined, seasons: t.seasons || undefined,
    runtime_min: t.runtime_min || undefined, overview: (t.overview_en || t.overview_he || "").slice(0, 220) || undefined,
    tags: (t.tags || []).slice(0, 8),
  };
}

async function rpc(fn, args, token) {
  const r = await fetch(`${SB_URL}/rest/v1/rpc/${fn}`, { method: "POST", headers: sbHeaders(token), body: JSON.stringify(args) });
  if (!r.ok) throw new Error(`${fn} failed: ${r.status} ${(await r.text()).slice(0, 200)}`);
  return r.json();
}

async function runTool(name, input, token, myServices) {
  if (name === "find_titles") {
    const args = {};
    for (const k of ["person", "person_role", "genre", "tag", "title_type", "min_year", "max_year", "min_imdb", "min_rt", "min_mc", "israeli", "min_votes"])
      if (input[k] !== undefined && input[k] !== null && input[k] !== "") args[k] = input[k];
    const svc = [];
    if (input.on_my_services) svc.push(...myServices);
    if (input.service && SERVICES[input.service]) svc.push(SERVICES[input.service]);
    if (svc.length) args.on_services = [...new Set(svc)];
    else if (input.on_my_services) return { count: 0, results: [], note: "The user hasn't picked their services. Search without this filter and tell them they can pick services under Where to watch on any title." };
    args.lim = Math.min(Math.max(Number(input.limit) || 15, 1), 40);
    const rows = (await rpc("find_titles", args, token)).filter(t => t.poster_en || t.poster_he);   // the site doesn't show titles without a poster
    return { count: rows.length, results: rows.map(slim) };
  }
  if (name === "search_by_name") {
    const rows = (await rpc("search_titles", { q: String(input.name || ""), lim: 8 }, token)).filter(t => t.poster_en || t.poster_he);
    return { count: rows.length, results: rows.map(slim) };
  }
  return { error: "unknown tool" };
}

async function getUser(token) {
  if (!token) return null;
  const r = await fetch(`${SB_URL}/auth/v1/user`, { headers: { apikey: SB_KEY, Authorization: `Bearer ${token}` } });
  return r.ok ? r.json() : null;
}

async function usedToday(token, userId) {
  const since = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  const r = await fetch(`${SB_URL}/rest/v1/ai_suggestions?select=id&user_id=eq.${userId}&created_at=gte.${since}`,
    { headers: { ...sbHeaders(token), Prefer: "count=exact", Range: "0-0" } });
  const m = /\/(\d+)$/.exec(r.headers.get("content-range") || "");
  return m ? Number(m[1]) : 0;
}

async function callClaude(body) {
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": process.env.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw Object.assign(new Error(`Claude API ${r.status}: ${(await r.text()).slice(0, 300)}`), { status: r.status });
  return r.json();
}

function system(lang, myServices) {
  const names = myServices.map(id => SERVICE_NAME[id]).filter(Boolean);
  const today = new Date().toISOString().slice(0, 10);
  return `You are the recommendation helper on "Ma Roim" (Hebrew for "what are we watching?"), a site listing US and Israeli movies and TV series from 1980 to today. Today is ${today}.
Find titles that fit what the user asks for, using only the catalog tools. Never recommend a title that did not come back from a tool.
- Be fast: make all the searches you need in ONE turn (several tool calls at once), then call present_results right after seeing the results. Don't search again unless the first results are empty.
- Turn the request into filters: person, genre, type, years, minimum IMDb / Rotten Tomatoes / Metacritic score, Israeli or not.
- Broad genres are coarse. For subgenres and themes ("psychological horror", "heist", "time travel", "slow burn", "based on a true story") use the tag filter, possibly in parallel with a genre search, e.g. tag "psychological" + genre "Horror", and tag "psychological" + title_type "tv".
- "After 2020" means min_year 2021. "Rated 8 or above on IMDb" means min_imdb 8.
- If the strict search finds nothing, loosen one condition at a time and say clearly which condition the suggestions don't meet.
- For "something like X", look X up with search_by_name, then search by its genres and similar filters.
- Streaming in Israel: the user's services are ${names.length ? names.join(", ") : myServices.length ? "set (smaller services)" : "not picked yet"}. When they ask for something they can watch now, on their services, or on a named service, use on_my_services or service. That data covers about 13,000 popular titles (Disney+ from its US catalog), so if it finds too little, also search without it and say which picks aren't on their services.
- Prefer well-known titles (use min_votes around 2000+) unless the user wants hidden gems.
- Reply in ${lang === "he" ? "Hebrew" : "English"} (or in the language the user writes in). Use Hebrew titles when replying in Hebrew if they exist.
- Keep the message short and concrete. No markdown headings or tables.
Finish by calling present_results exactly once.`;
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") return res.status(405).json({ error: "Use POST" });
  if (!process.env.ANTHROPIC_API_KEY) return res.status(503).json({ error: "not_configured" });
  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
    const token = (req.headers.authorization || "").replace(/^Bearer\s+/i, "");
    const user = await getUser(token);
    if (!user || !user.id) return res.status(401).json({ error: "sign_in" });
    if ((await usedToday(token, user.id)) >= DAILY_LIMIT) return res.status(429).json({ error: "limit" });

    const lang = body.lang === "he" ? "he" : "en";
    const myServices = (Array.isArray(body.services) ? body.services : []).map(Number).filter(n => Number.isInteger(n) && n > 0).slice(0, 30);
    const history = (Array.isArray(body.messages) ? body.messages : [])
      .filter(m => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && m.content.trim())
      .slice(-10).map(m => ({ role: m.role, content: m.content.slice(0, 2000) }));
    if (!history.length || history[history.length - 1].role !== "user") return res.status(400).json({ error: "empty" });

    // Discover sends the candidates itself (famous titles that fit the taste): one quick call that picks from them, no searching
    const pickFrom = (Array.isArray(body.pick_from) ? body.pick_from : []).map(String).filter(id => /^[QMS]\d+$/.test(id)).slice(0, 80);
    if (pickFrom.length) {
      const r = await fetch(`${SB_URL}/rest/v1/titles?select=*&id=in.(${pickFrom.join(",")})`, { headers: sbHeaders(token) });
      const rows = r.ok ? await r.json() : [];
      const ok = new Set(rows.map(t => t.id));
      const resp = await callClaude({
        model: MODEL, max_tokens: 1500, system: system(lang, myServices), tools: TOOLS.filter(t => t.name === "present_results"),
        tool_choice: { type: "tool", name: "present_results" },
        messages: [...history.slice(0, -1), { role: "user", content: `${history[history.length - 1].content}\n\nPick only from these titles (use their ids):\n${JSON.stringify(rows.map(slim))}` }],
      });
      const present = resp.content.find(b => b.type === "tool_use" && b.name === "present_results");
      const result = present ? { message: String(present.input.message || ""), ids: (present.input.title_ids || []).map(String).filter(id => ok.has(id)).slice(0, 12) } : { message: "", ids: [] };
      await fetch(`${SB_URL}/rest/v1/ai_suggestions`, {
        method: "POST", headers: { ...sbHeaders(token), Prefer: "return=minimal" },
        body: JSON.stringify({ user_id: user.id, prompt: history[history.length - 1].content.slice(0, 2000), title_ids: result.ids, answer: result.message.slice(0, 4000) }),
      }).catch(() => {});
      return res.status(200).json(result);
    }

    const messages = [...history];
    let result = null;
    for (let round = 0; round < MAX_ROUNDS && !result; round++) {
      const lastRound = round === MAX_ROUNDS - 1;
      const resp = await callClaude({
        model: MODEL, max_tokens: 1000, system: system(lang, myServices), tools: TOOLS, messages,
        tool_choice: lastRound ? { type: "tool", name: "present_results" } : { type: "auto" },
      });
      messages.push({ role: "assistant", content: resp.content });
      const uses = resp.content.filter(b => b.type === "tool_use");
      if (!uses.length) {   // answered in plain text without the tool
        const text = resp.content.filter(b => b.type === "text").map(b => b.text).join("\n").trim();
        result = { message: text, ids: [] };
        break;
      }
      const present = uses.find(u => u.name === "present_results");
      if (present) {
        result = { message: String(present.input.message || ""), ids: (present.input.title_ids || []).map(String).slice(0, 12) };
        break;
      }
      // Run all searches from this turn at the same time
      const outputs = await Promise.all(uses.map(async u => {
        let out;
        try { out = await runTool(u.name, u.input || {}, token, myServices); }
        catch (e) { out = { error: String(e.message || e) }; }
        return { type: "tool_result", tool_use_id: u.id, content: JSON.stringify(out) };
      }));
      if (!result) messages.push({ role: "user", content: outputs });
    }
    if (!result) result = { message: "", ids: [] };

    // Log the question (also counts toward the daily limit). Row-level security limits this to the user's own rows.
    await fetch(`${SB_URL}/rest/v1/ai_suggestions`, {
      method: "POST", headers: { ...sbHeaders(token), Prefer: "return=minimal" },
      body: JSON.stringify({ user_id: user.id, prompt: history[history.length - 1].content.slice(0, 2000), title_ids: result.ids, answer: result.message.slice(0, 4000) }),
    }).catch(() => {});

    return res.status(200).json(result);
  } catch (e) {
    console.error(e);
    return res.status(e.status === 429 || e.status === 529 ? 503 : 500).json({ error: "failed" });
  }
};
