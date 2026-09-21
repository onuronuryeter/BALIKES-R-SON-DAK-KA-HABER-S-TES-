import os
import sys

# Proje dizinini Python yoluna ekleyin (Hostinger sunucusundaki tam yolu bulur)
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app as asgi_app

try:
    # Hostinger Passenger (cPanel/hPanel) genellikle standart WSGI bekler.
    # FastAPI ise ASGI'dır. Bu yüzden a2wsgi kütüphanesi ile dönüştürüyoruz.
    from a2wsgi import ASGIMiddleware
    application = ASGIMiddleware(asgi_app)
except ImportError:
    # Eğer a2wsgi kurulu değilse (veya Passenger ASGI destekliyorsa) doğrudan app kullanılır
    application = asgi_app
