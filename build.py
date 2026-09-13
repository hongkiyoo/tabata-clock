#!/usr/bin/env python3
"""Build a self-hosted, standalone copy of the timer into dist/.

The artifact host supplies <!doctype>/<head>/<body> and owns the page's
origin; a self-hosted copy has to supply them itself. Running outside a
cross-origin iframe is the whole point: it restores the Screen Wake Lock
permission that claude.ai's frame denies (NotAllowedError).
"""
import io, os, re, hashlib, subprocess

SRC, OUT = "tabata.html", "docs"
src = io.open(SRC, encoding="utf-8").read()

# The artifact shell injected these at runtime; standalone gets real tags.
src = re.sub(
    r"/\* Home-screen install hints.*?\}\);\n",
    """/* Service worker: makes the home-screen app open instantly and work
   with no signal — a gym basement is a realistic place to need this. */
if("serviceWorker" in navigator){
  window.addEventListener("load", function(){
    navigator.serviceWorker.register("sw.js").then(null, function(){});
  });
}
""", src, flags=re.S)

split = src.index('<main class="setup"')
head, body = src[:split].rstrip(), src[split:].rstrip()

HEAD_EXTRA = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="타바타 인터벌 타이머 — 20초 운동 / 10초 휴식 × 8라운드.">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0E1116">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Tabata">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png" sizes="192x192">
<link rel="apple-touch-icon" href="icon-180.png">
<style>
/* Baseline the artifact shell used to provide. */
:root{color-scheme:dark}
html,body{margin:0}
img,video{max-width:100%}
[hidden]{display:none !important}
</style>"""

page = ("<!doctype html>\n<html lang=\"ko\">\n<head>\n"
        + HEAD_EXTRA + "\n" + head
        + "\n</head>\n<body>\n" + body + "\n</body>\n</html>\n")

os.makedirs(OUT, exist_ok=True)
io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)

io.open(os.path.join(OUT, "manifest.webmanifest"), "w", encoding="utf-8").write("""{
  "name": "Tabata Clock",
  "short_name": "Tabata",
  "description": "타바타 인터벌 타이머",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0E1116",
  "theme_color": "#0E1116",
  "icons": [
    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
""")

# Cache name carries a build hash, so redeploying installs a fresh worker.
ver = hashlib.sha256(page.encode("utf-8")).hexdigest()[:10]
io.open(os.path.join(OUT, "sw.js"), "w", encoding="utf-8").write("""const CACHE = "tabata-%s";
const ASSETS = ["./", "./index.html", "./manifest.webmanifest",
                "./icon-180.png", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;

  // Page itself: network first, so a redeploy is picked up when online.
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put("./index.html", copy));
          return res;
        })
        .catch(() => caches.match("./index.html").then(hit => hit || Response.error()))
    );
    return;
  }

  // Everything else: cache first, fill the cache on the way past.
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res && res.ok && new URL(req.url).origin === location.origin) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
      }
      return res;
    }))
  );
});
""" % ver)

for n, s in (("icon-180.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
    p = os.path.join(OUT, n)
    if not os.path.exists(p):
        subprocess.run(["python3", "make_icon.py", p, str(s)], check=True)

print("build %s -> %s/" % (ver, OUT))
for f in sorted(os.listdir(OUT)):
    print("  %-24s %7d B" % (f, os.path.getsize(os.path.join(OUT, f))))
