// ZazaSync Service Worker — PWA offline support + push notifications
const CACHE = 'zazasync-v1';
const STATIC = [
  '/',
  '/inventory',
  '/zazasync-mobile.html',
  '/zazasync-mobile-auth.html',
  '/zazasync-mobile-onboarding.html',
  '/zazasync-mobile-product.html',
];

// INSTALL — cache static assets
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

// ACTIVATE — clear old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// FETCH — network first, cache fallback
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

// PUSH NOTIFICATIONS — fires when Supabase/Resend sends a push
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  const title = data.title || '🟢 ZazaSync Alert';
  const options = {
    body: data.body || 'A product on your watchlist is back in stock.',
    icon: '/icons/icon-192.png',
    badge: '/icons/badge-72.png',
    tag: data.tag || 'zazasync-alert',
    data: { url: data.url || '/watchlist' },
    actions: [
      { action: 'view', title: 'View product' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

// NOTIFICATION CLICK — open product page
self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'dismiss') return;
  const url = e.notification.data.url || '/';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
