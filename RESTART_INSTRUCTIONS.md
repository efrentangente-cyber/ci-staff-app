# How to Restart Your Secured App

## Quick Start

### Step 1: Stop Current Server
If your Flask app is running, press `Ctrl + C` in the terminal to stop it.

### Step 2: Restart the Server
Run this command:
```bash
python app.py
```

Or if you're using a specific port:
```bash
python app.py
```

The app will start on `http://0.0.0.0:5000` (accessible from other devices on your network)

---

## What Changed?

Your app now has:
- ✅ CSRF protection (automatic)
- ✅ Rate limiting (automatic)
- ✅ Stronger passwords required
- ✅ File upload validation
- ✅ Path traversal protection
- ✅ Secure secret key

---

## First Time Testing

### Test Login Rate Limiting:
1. Go to login page
2. Try wrong password 6 times
3. After 5 attempts, you'll see: "429 Too Many Requests"
4. Wait 1 minute, then try again

### Test Password Strength:
1. Go to signup or change password
2. Try weak password like "test123" → Rejected
3. Try strong password like "MyPass123" → Accepted

### Test File Upload:
1. Try uploading a .txt or .exe file → Rejected
2. Upload .pdf or .jpg → Accepted

---

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'flask_wtf'"
**Solution**: Run `python -m pip install -r requirements.txt`

### Error: "CSRF token missing"
**Solution**: This is normal for API endpoints. The app handles this automatically.

### Error: "429 Too Many Requests"
**Solution**: You hit the rate limit. Wait 1 minute and try again.

---

## For Production Deployment

When you're ready to deploy to a real server:

1. **Get a domain name** (e.g., dccco-loans.com)
2. **Get SSL certificate** (free from Let's Encrypt)
3. **Update .env**:
   ```
   FLASK_ENV=production
   FLASK_DEBUG=False
   ```
4. **Update WebSocket CORS in app.py**:
   ```python
   socketio = SocketIO(app, cors_allowed_origins=[
       "https://yourdomain.com"
   ])
   ```
5. **Use Gunicorn**:
   ```bash
   gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 app:app
   ```

---

## Need Help?

Check these files:
- **SECURITY.md** - Complete security documentation
- **SECURITY_FIXES_APPLIED.md** - What was changed and why

Your app is now secure and ready to use! 🚀
