self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(fetch(event.request));
});

self.addEventListener("push", (event) => {
  let payload = {
    title: "Crowscap",
    body: "A memory is ready.",
    url: "/recall",
    tag: "crowscap-notification",
  };

  if (event.data) {
    try {
      payload = { ...payload, ...event.data.json() };
    } catch {
      payload.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      tag: payload.tag,
      icon: "/icons/crowscap-icon-transparent-192.png",
      badge: "/icons/badge-monochrome-192.png",
      data: {
        url: payload.url || "/recall",
      },
    }),
  );

});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/recall";
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        const existing = clients.find((client) =>
          client.url.includes(self.location.origin),
        );
        if (existing) {
          existing.focus();
          existing.navigate(targetUrl);
          return;
        }
        return self.clients.openWindow(targetUrl);
      }),
  );
});
