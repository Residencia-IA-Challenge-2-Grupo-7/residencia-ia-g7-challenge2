/* Service worker mínimo do PWA (RNF-09): faz cache só dos arquivos estáticos das telas,
   nunca de respostas da API (que podem conter perfil secreto). */
'use strict';

const CACHE = 'orquestrador-telas-v1';
const ESTATICOS = [
  '/static/telas/app.css',
  '/static/telas/comum.js',
  '/static/telas/app.js',
  '/static/telas/perfil.js',
  '/static/telas/sala.js',
  '/static/telas/demo.js',
  '/static/telas/icone.svg',
];

self.addEventListener('install', (ev) => {
  ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(ESTATICOS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (ev) => {
  ev.waitUntil(
    caches.keys().then((chaves) =>
      Promise.all(chaves.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (ev) => {
  const url = new URL(ev.request.url);
  if (ev.request.method !== 'GET' || !url.pathname.startsWith('/static/telas/')) return;
  ev.respondWith(
    caches.match(ev.request).then((emCache) => emCache || fetch(ev.request))
  );
});
