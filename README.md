# BALIKESİR SON DAKİKA HABER

Balıkesir ve ilçelerinden son dakika haberleri, güncel gelişmeler.

**Alan Adı:** balikesirsondakikahaber.com  
**Lokal URL:** http://127.0.0.1:8000  

---

## 🚀 Hızlı Başlangıç (Windows)

### 1. Gereksinimler

- Python 3.12+
- pip (Python ile birlikte gelir)

Python sürümünüzü kontrol edin:
```cmd
python --version
```

### 2. Projeyi İndirin / Klonlayın

```cmd
cd "C:\Users\baban\Desktop"
cd "BALIKESİR SON DAKİKA WEB\balikesirsondakikahaber"
```

### 3. Virtual Environment Oluşturun

```cmd
python -m venv venv
venv\Scripts\activate
```

> Aktivasyon sonrası komut satırı başında `(venv)` görünmeli.

### 4. Bağımlılıkları Yükleyin

```cmd
pip install -r requirements.txt
```

### 5. Ortam Değişkenlerini Ayarlayın

```cmd
copy .env.example .env
```

`.env` dosyasını bir metin editörüyle açıp düzenleyin:

```env
SECRET_KEY=cok-guclu-bir-anahtar-buraya-yazin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=guclu-sifreniz
ADMIN_EMAIL=admin@balikesirsondakikahaber.com
```

Güçlü secret key oluşturmak için:
```cmd
python -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Veritabanını Başlatın

```cmd
python scripts/init_db.py
python scripts/seed_categories.py
```

### 7. Uygulamayı Başlatın

```cmd
run.bat
```

veya terminal üzerinden:

```cmd
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 8. Tarayıcıda Açın

| Sayfa | URL |
|-------|-----|
| Ana Sayfa | http://127.0.0.1:8000 |
| Admin Paneli | http://127.0.0.1:8000/admin |
| API Docs | http://127.0.0.1:8000/api/docs |
| Health Check | http://127.0.0.1:8000/health |

---

## 📁 Proje Yapısı

```
balikesirsondakikahaber/
│
├── app/
│   ├── main.py                 # FastAPI ana uygulama
│   ├── config/
│   │   └── settings.py         # Ayar yönetimi (.env)
│   ├── database/
│   │   ├── database.py         # DB bağlantısı & session
│   │   └── models.py           # SQLAlchemy modelleri
│   ├── api/                    # API endpoint'leri
│   ├── services/               # İş mantığı servisleri
│   ├── templates/              # Jinja2 HTML şablonları
│   └── static/                 # CSS, JS, images
│
├── data/
│   ├── database.sqlite3        # SQLite veritabanı
│   └── media/                  # Yüklenen görseller
│
├── scripts/
│   ├── init_db.py              # DB kurulumu
│   ├── seed_categories.py      # Kategori seed
│   └── run_scheduler.py        # Scheduler
│
├── logs/                       # Uygulama logları
├── .env                        # Ortam değişkenleri (GIT'E EKLEMEYİN!)
├── .env.example                # Örnek ortam değişkenleri
├── requirements.txt            # Python bağımlılıkları
└── run.bat                     # Windows başlatma scripti
```

---

## 📦 Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Backend | FastAPI + Uvicorn |
| ORM | SQLAlchemy (Async) |
| Veritabanı | SQLite → PostgreSQL (ileride) |
| Şablon | Jinja2 |
| Güvenlik | passlib (bcrypt) + JWT |
| RSS | feedparser + httpx |
| Scheduler | APScheduler |
| Doğrulama | Pydantic v2 |
| Logging | loguru |

---

## 🔧 Geliştirme Komutları

```cmd
# Veritabanını sıfırla ve yeniden kur
python scripts/init_db.py

# Kategorileri yükle
python scripts/seed_categories.py

# Scheduler'ı manuel çalıştır (Aşama 11'de tamamlanacak)
python scripts/run_scheduler.py

# Sunucuyu başlat (hot-reload ile)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🗂️ Geliştirme Aşamaları

| Aşama | Durum | Açıklama |
|-------|-------|----------|
| 1 | ✅ Tamamlandı | Proje yapısı, DB modelleri, temel FastAPI |
| 2 | 🔄 Sırada | FastAPI backend API'leri |
| 3 | 🔄 Sırada | Admin authentication |
| 4 | 🔄 Sırada | Admin panel |
| 5 | 🔄 Sırada | Frontend |
| 6 | 🔄 Sırada | SEO |
| 7 | 🔄 Sırada | RSS Collector |
| 8 | 🔄 Sırada | Duplicate Detection |
| 9 | 🔄 Sırada | AI Provider |
| 10 | 🔄 Sırada | Scheduler |
| 11 | 🔄 Sırada | Sitemap & Robots |
| 12 | 🔄 Sırada | Testing |

---

## 🔒 Güvenlik Notları

- `.env` dosyasını **asla** Git'e eklemeyin
- `SECRET_KEY`'i güçlü ve benzersiz yapın
- Production için `DEBUG=false` yapın
- Admin şifresini düzenli değiştirin

---

## 🌐 Production'a Geçiş

1. `.env` dosyasında `APP_ENV=production` yapın
2. `DATABASE_URL`'i PostgreSQL'e geçirin
3. `SITE_URL`'i gerçek domain ile güncelleyin
4. Reverse proxy (Nginx) kurun
5. SSL sertifikası (Let's Encrypt) alın

---

## 📞 Destek

Herhangi bir sorun için uygulama loglarını kontrol edin:
```cmd
type logs\app.log
```

veya terminal çıktısına bakın.
