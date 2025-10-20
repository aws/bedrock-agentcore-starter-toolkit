# Render Deployment Guide - Analytics Dashboard

This guide will help you deploy the fraud detection analytics dashboard to Render.

## 🚀 Quick Deploy

### Option 1: Deploy from GitHub (Recommended)

1. **Push your code to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Create a Render account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub

3. **Create a new Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect the `render.yaml` configuration

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your app
   - Your dashboard will be live at: `https://your-app-name.onrender.com`

### Option 2: Manual Configuration

If you prefer manual setup or the auto-detection doesn't work:

1. **Create New Web Service** on Render

2. **Configure Build Settings:**
   - **Name:** `fraud-detection-analytics` (or your choice)
   - **Runtime:** `Python 3`
   - **Build Command:** 
     ```bash
     pip install -e . && pip install python-socketio
     ```
   - **Start Command:**
     ```bash
     python web_interface/analytics_server.py
     ```

3. **Environment Variables:**
   - `PYTHON_VERSION`: `3.11`
   - `PORT`: `10000` (Render will set this automatically)
   - `HOST`: `0.0.0.0`
   - `DEBUG`: `False`

4. **Health Check:**
   - Path: `/api/analytics/summary`

5. **Click "Create Web Service"**

## 📋 Pre-Deployment Checklist

- [ ] Code is pushed to GitHub
- [ ] `render.yaml` exists in root directory
- [ ] `pyproject.toml` has all required dependencies
- [ ] Analytics server uses environment variables for host/port
- [ ] CORS is configured to allow all origins (already set)

## 🔧 Configuration Files

### render.yaml
The `render.yaml` file in the root directory contains the deployment configuration:

```yaml
services:
  - type: web
    name: fraud-detection-analytics
    runtime: python
    buildCommand: pip install -e . && pip install python-socketio
    startCommand: python web_interface/analytics_server.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      - key: PORT
        value: 10000
    healthCheckPath: /api/analytics/summary
```

## 🌐 Accessing Your Deployed Dashboard

Once deployed, your dashboard will be available at:
```
https://your-app-name.onrender.com
```

### API Endpoints
All endpoints will be accessible at your Render URL:
- `https://your-app-name.onrender.com/api/analytics/summary`
- `https://your-app-name.onrender.com/api/analytics/patterns`
- etc.

### WebSocket Connection
The WebSocket will automatically connect to your deployed URL for real-time updates.

## 💰 Pricing

### Free Tier
- Perfect for demos and testing
- Spins down after 15 minutes of inactivity
- Spins up automatically when accessed (takes ~30 seconds)
- 750 hours/month free

### Paid Tiers
- Starter: $7/month - Always on, no spin down
- Standard: $25/month - More resources
- Pro: $85/month - High performance

## 🐛 Troubleshooting

### Build Fails
**Issue:** Dependencies not installing
**Solution:** Check that `pyproject.toml` includes all required packages:
```bash
flask>=3.1.2
flask-cors>=6.0.1
flask-socketio>=5.5.1
python-socketio>=5.9.0
```

### App Crashes on Start
**Issue:** Port binding error
**Solution:** Ensure the server uses `os.environ.get('PORT', 5001)`

### WebSocket Not Connecting
**Issue:** CORS or WebSocket configuration
**Solution:** Verify CORS is set to allow all origins:
```python
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
```

### Health Check Failing
**Issue:** `/api/analytics/summary` endpoint not responding
**Solution:** 
- Check logs in Render dashboard
- Verify the endpoint works locally first
- Ensure all dependencies are installed

## 📊 Monitoring

### View Logs
1. Go to your Render dashboard
2. Click on your service
3. Click "Logs" tab
4. View real-time logs

### Metrics
Render provides:
- CPU usage
- Memory usage
- Request count
- Response times

## 🔄 Updates and Redeployment

### Automatic Deploys
Render automatically redeploys when you push to your main branch:
```bash
git add .
git commit -m "Update analytics dashboard"
git push origin main
```

### Manual Deploy
1. Go to Render dashboard
2. Click your service
3. Click "Manual Deploy" → "Deploy latest commit"

## 🔒 Security Considerations

### For Production:
1. **Restrict CORS origins:**
   ```python
   CORS(app, resources={r"/*": {"origins": "https://yourdomain.com"}})
   ```

2. **Add authentication:**
   - Implement API key authentication
   - Use Render's environment variables for secrets

3. **Enable HTTPS:**
   - Render provides free SSL certificates automatically

4. **Rate limiting:**
   - Add rate limiting to prevent abuse
   - Use Flask-Limiter

## 📱 Testing Your Deployment

### 1. Test the Dashboard
Visit: `https://your-app-name.onrender.com`

### 2. Test API Endpoints
```bash
curl https://your-app-name.onrender.com/api/analytics/summary
```

### 3. Test WebSocket
Open the dashboard and click "📡 Start Live Stream"

### 4. Test Health Check
```bash
curl https://your-app-name.onrender.com/api/analytics/summary
```

## 🎯 Next Steps

After deployment:
1. ✅ Test all features
2. ✅ Monitor logs for errors
3. ✅ Set up custom domain (optional)
4. ✅ Configure environment variables for production
5. ✅ Enable auto-deploy from GitHub

## 📚 Additional Resources

- [Render Documentation](https://render.com/docs)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/latest/deploying/)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)

## 💡 Tips

- **Free tier spin-down:** Keep your app warm by pinging it every 10 minutes
- **Custom domain:** Add your own domain in Render settings
- **Environment variables:** Use Render's dashboard to manage secrets
- **Logs:** Check logs regularly during initial deployment
- **Scaling:** Upgrade to paid tier for production workloads

## 🆘 Need Help?

- Check Render's [Community Forum](https://community.render.com/)
- Review [Render Status](https://status.render.com/)
- Contact Render Support (paid plans)

---

**Ready to deploy?** Follow the Quick Deploy steps above! 🚀
