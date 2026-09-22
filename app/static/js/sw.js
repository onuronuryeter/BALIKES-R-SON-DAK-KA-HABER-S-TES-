self.addEventListener('push', function(event) {
    console.log('[Service Worker] Push Received.');
    let data = { title: "Yeni Haber", body: "Sitemizde yeni bir haber var!", url: "/" };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch(e) {
            console.log("Push data is not JSON", e);
        }
    }

    const title = data.title || "Balıkesir Son Dakika";
    const options = {
        body: data.body || "",
        icon: '/static/images/favicon.ico',
        badge: '/static/images/favicon.ico',
        data: {
            url: data.url || "/"
        }
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.');
    event.notification.close();
    
    if (event.notification.data && event.notification.data.url) {
        event.waitUntil(
            clients.openWindow(event.notification.data.url)
        );
    } else {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});
