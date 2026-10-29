// Shared title links: GET /t/<Wikidata id>?l=he|en  (vercel.json rewrites it to /api/t?id=…)
// WhatsApp and other apps read the preview (name, year, synopsis, poster) from the meta tags here;
// people who open the link are sent straight on to the title in the site.

const SB_URL = "https://prnfnqvjirwuyafvsulk.supabase.co";
const SB_KEY = "sb_publishable_mxaPvh6JxrmWlaOuR4LVkA_q0ll9ESM"; // public key; row-level security protects user data

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clip = (s, n) => (s && s.length > n ? s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…" : s || "");

module.exports = async function handler(req, res) {
  const id = String((req.query && req.query.id) || "");
  const lang = req.query && req.query.l === "en" ? "en" : "he";
  if (!/^[QMS]\d{1,12}$/.test(id)) { res.statusCode = 302; res.setHeader("Location", "/"); return res.end(); }
  const app = `/?t=${id}`;

  let t = null;
  try {
    const cols = "id,type,title,title_he,year,end_year,overview_en,overview_he,poster_en,poster_he,backdrop,imdb_rating";
    const r = await fetch(`${SB_URL}/rest/v1/titles?select=${cols}&id=eq.${id}`, { headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` } });
    if (r.ok) t = (await r.json())[0] || null;
  } catch (e) { /* no preview; the redirect still works */ }

  const he = lang === "he";
  const site = he ? "מה רואים · Ma Roim" : "Ma Roim · מה רואים";
  let title = site, desc = he ? "סרטים וסדרות אמריקאיים וישראליים, עם עוזר AI שממליץ מה לראות." : "US and Israeli movies and series, with an AI helper that suggests what to watch.", image = "";
  if (t) {
    const name = he ? (t.title_he || t.title) : t.title;
    const years = t.type === "tv" && t.year ? (t.end_year && t.end_year !== t.year ? `${t.year}–${t.end_year}` : t.end_year ? `${t.year}` : `${t.year}–`) : (t.year || "");
    const kind = t.type === "tv" ? (he ? "סדרה" : "Series") : (he ? "סרט" : "Movie");
    const score = t.imdb_rating ? ` · IMDb ${Number(t.imdb_rating).toFixed(1)}` : "";
    title = `${name}${years ? ` (${years})` : ""}`;
    desc = `${kind}${score} · ${clip(he ? (t.overview_he || t.overview_en) : (t.overview_en || t.overview_he), 190)}`;
    image = (he ? (t.poster_he || t.poster_en) : t.poster_en) || t.backdrop || "";
  }
  const host = `https://${req.headers["x-forwarded-host"] || req.headers.host}`;
  if (!image) image = `${host}/icons/icon-512.png?v=2`;

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "public, max-age=300, s-maxage=86400");
  res.end(`<!doctype html>
<html lang="${lang}" dir="${he ? "rtl" : "ltr"}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} · ${esc(site)}</title>
<meta name="description" content="${esc(desc)}">
<meta property="og:site_name" content="${esc(site)}">
<meta property="og:type" content="${t && t.type === "tv" ? "video.tv_show" : "video.movie"}">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${esc(image)}">
<meta property="og:url" content="${esc(`${host}/t/${id}?l=${lang}`)}">
<meta property="og:locale" content="${he ? "he_IL" : "en_US"}">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#0e0c18">
<meta http-equiv="refresh" content="0;url=${esc(app)}">
<script>location.replace(${JSON.stringify(app)})</script>
</head><body style="background:#0e0c18;color:#fff;font-family:system-ui;padding:24px"><a style="color:#b49cff" href="${esc(app)}">${esc(title)}</a></body></html>`);
};
