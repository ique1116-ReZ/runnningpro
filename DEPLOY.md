# ReLab Backend Deploy

## 1) Push to GitHub

```bash
git add .
git commit -m "chore: prepare backend for github deploy"
git push origin main
```

## 2) Server setup (Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx
```

## 3) Pull code

```bash
sudo mkdir -p /opt/relab-backend
sudo chown -R $USER:$USER /opt/relab-backend
git clone https://github.com/<your-user>/<your-repo>.git /opt/relab-backend
cd /opt/relab-backend
```

## 4) Install Python deps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-server.txt
```

## 5) Start by Gunicorn (manual test)

```bash
source .venv/bin/activate
gunicorn --workers 2 --threads 2 --timeout 120 --bind 127.0.0.1:5000 wsgi:app
```

## 6) Configure systemd

```bash
sudo cp deploy/systemd/relab-backend.service /etc/systemd/system/relab-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now relab-backend
sudo systemctl status relab-backend
```

## 7) Configure Nginx

```bash
sudo cp deploy/nginx/relab-backend.conf /etc/nginx/sites-available/relab-backend
sudo ln -sf /etc/nginx/sites-available/relab-backend /etc/nginx/sites-enabled/relab-backend
sudo nginx -t
sudo systemctl reload nginx
```

## 8) Test API

```bash
curl http://127.0.0.1/api/status
```

