# Deployment Guide for CBFC Cutlists Explorer

## Prerequisites
- Your SQLite database (`cbfc_cutlists.db`) should be built and ready
- All your data files should be in the `data/` directory

## Option 1: Railway (Recommended - Easiest)

1. **Prepare your repository:**
   ```bash
   git add .
   git commit -m "Add deployment configuration"
   git push origin main
   ```

2. **Deploy to Railway:**
   - Go to [railway.app](https://railway.app)
   - Sign up/login with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will automatically detect it's a Python app and deploy

3. **Configure environment (if needed):**
   - The app will be available at a generated URL
   - Railway handles the database and static files automatically

## Option 2: Render

1. **Prepare your repository:**
   ```bash
   git add .
   git commit -m "Add deployment configuration"
   git push origin main
   ```

2. **Deploy to Render:**
   - Go to [render.com](https://render.com)
   - Sign up/login with GitHub
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Use these settings:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`

## Option 3: Fly.io

1. **Install Fly CLI:**
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. **Initialize and deploy:**
   ```bash
   fly auth login
   fly launch
   fly deploy
   ```

## Option 4: Google Cloud Run

1. **Enable Cloud Run API and install gcloud CLI**

2. **Build and deploy:**
   ```bash
   gcloud builds submit --tag gcr.io/[PROJECT-ID]/cbfc-cutlists
   gcloud run deploy --image gcr.io/[PROJECT-ID]/cbfc-cutlists --platform managed
   ```

## Option 5: Traditional VPS (DigitalOcean, Linode, etc.)

1. **Set up a VPS with Ubuntu**

2. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip nginx
   ```

3. **Clone and setup:**
   ```bash
   git clone [your-repo-url]
   cd cbfc-cutlists-2018-2022
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run with systemd:**
   ```bash
   sudo nano /etc/systemd/system/cbfc-cutlists.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=CBFC Cutlists API
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/cbfc-cutlists-2018-2022
   Environment=PATH=/home/ubuntu/cbfc-cutlists-2018-2022/.venv/bin
   ExecStart=/home/ubuntu/cbfc-cutlists-2018-2022/.venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

5. **Start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable cbfc-cutlists
   sudo systemctl start cbfc-cutlists
   ```

## Important Notes

### Database Considerations
- Your SQLite database file (`cbfc_cutlists.db`) needs to be included in deployment
- For production, consider using PostgreSQL instead of SQLite for better concurrent access
- Make sure the database file has proper permissions

### Static Files
- The `static/` directory contains your frontend files
- Make sure these are included in your deployment

### Environment Variables
- Most platforms will automatically set `PORT`
- You can set custom environment variables if needed

### Domain Setup
- Most platforms provide a free subdomain
- You can configure custom domains in platform settings

### SSL/HTTPS
- Most modern platforms provide automatic SSL certificates
- Your app will be accessible via HTTPS

## Troubleshooting

### Common Issues:
1. **Database not found**: Ensure `cbfc_cutlists.db` is in the root directory
2. **Static files not served**: Check that `static/` directory is included
3. **Port issues**: Make sure your app uses the `PORT` environment variable
4. **Large file limits**: Some platforms have file size limits for databases

### Performance Tips:
- Enable gzip compression in production
- Consider using a CDN for static assets
- Monitor database performance under load 