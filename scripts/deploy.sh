#!/bin/bash
set -e

echo "=========================================="
echo "Balikesir Son Dakika - VPS Deployment"
echo "=========================================="

echo "1. System Updates and Dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx git certbot python3-certbot-nginx sqlite3 curl

echo "2. Setting up Directory & Cloning Repository..."
sudo mkdir -p /var/www
sudo chown -R $USER:$USER /var/www
cd /var/www

if [ -d "balikesirsondakikahaber" ]; then
    echo "Directory exists, pulling latest changes..."
    cd balikesirsondakikahaber
    git pull origin main
else
    echo "Cloning repository..."
    git clone https://github.com/onuronuryeter/BALIKES-R-SON-DAK-KA-HABER-S-TES-.git balikesirsondakikahaber
    cd balikesirsondakikahaber
fi

echo "3. Setting up Python Virtual Environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install uvicorn gunicorn

echo "4. Initializing Database (if not exists)..."
python scripts/init_db.py

echo "5. Fixing Permissions for SQLite Database..."
# SQLite needs the directory to be writable by the user running the app
mkdir -p data/media/articles
mkdir -p data/media/districts
chmod 777 data
chmod 666 data/database.sqlite3 || true

echo "6. Setting up Systemd Service..."
sudo bash -c 'cat > /etc/systemd/system/fastapi.service << EOF
[Unit]
Description=FastAPI application for Balikesir Son Dakika
After=network.target

[Service]
User='"$USER"'
Group=www-data
WorkingDirectory=/var/www/balikesirsondakikahaber
Environment="PATH=/var/www/balikesirsondakikahaber/venv/bin"
ExecStart=/var/www/balikesirsondakikahaber/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl restart fastapi

echo "7. Configuring Nginx..."
sudo bash -c 'cat > /etc/nginx/sites-available/balikesirsondakika << EOF
server {
    listen 80;
    server_name _;

    # Increase upload size for images
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Support for SSE (Server-Sent Events) / Canli Yayin
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 24h;
    }
}
EOF'

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/balikesirsondakika /etc/nginx/sites-enabled/
sudo systemctl restart nginx

echo "=========================================="
echo "Deployment Complete!"
echo "Your Website should now be accessible at: http://$(curl -s ifconfig.me)"
echo "To link your domain and set up SSL/HTTPS, point your domain to $(curl -s ifconfig.me)"
echo "and run: sudo certbot --nginx"
echo "=========================================="
