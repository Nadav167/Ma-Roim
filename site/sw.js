// Offline helper for the installed app.
// The page and catalog: network first (always the newest version online), cached copy when offline.
// Library and icons: cached. Posters and photos: cached as you browse, capped at 400 images.
// Never touches the database, the AI or anything else.
const SHELL = "w2w-shell-v4", IMG = "w2w-img-v1", IMG_MAX = 400;
self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(["./", "vendor/supabase.js", "manifest.webmanifest", "icons/icon-192.png"])).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => ![SHELL, IMG].includes(k)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
async function networkFirst(req) {
  const c = await caches.open(SHELL);
  try { const r = await fetch(req); if (r.ok) c.put(req, r.clone()); return r; }
  catch (e) { return (await c.match(req, { ignoreSearch: true })) || (await c.match("./")) || Response.error(); }
}
async function cacheFirst(req, name, max) {
  const c = await caches.open(name), hit = await c.match(req);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok || r.type === "opaque") {
    c.put(req, r.clone());
    if (max) c.keys().then(ks => { if (ks.length > max) ks.slice(0, ks.length - max).forEach(k => c.delete(k)); });
  }
  return r;
}
self.addEventListener("fetch", e => {
  const req = e.request; if (req.method !== "GET") return;
  const u = new URL(req.url);
  if (u.origin === location.origin) {
    if (u.pathname.startsWith("/api/")) return;
    if (req.mode === "navigate" || u.pathname.endsWith(".html") || u.pathname.endsWith(".json") || u.pathname.endsWith("sw.js")) return e.respondWith(networkFirst(req));
    if (u.pathname.includes("/vendor/") || u.pathname.includes("/icons/")) return e.respondWith(cacheFirst(req, SHELL));
    return e.respondWith(networkFirst(req));
  }
  if (u.hostname === "image.tmdb.org") return e.respondWith(cacheFirst(req, IMG, IMG_MAX));
});
