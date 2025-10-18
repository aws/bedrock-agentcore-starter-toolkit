# Deploy Analytics Dashboard to Render

## Quick Deploy Steps

### 1️⃣ Test Locally First
```bash
# From project root
python test_render_deployment.py
```

### 2️⃣ Push to GitHub
```bash
git add .
git commit -m "Deploy analytics dashboard to Render"
git push origin main
```

### 3️⃣ Create Render Service

**Option A: Automatic (Recommended)**
1. Go to [render.com](https://render.com)
2. New + → Web Service
3. Connect GitHub repo
4. Render detects `render.yaml` automatically
5. Click "Create Web Service"

**Option B: Manual**
1. Go to [render.com](https://render.com)
2. New + → Web Service
3. Configure:
   - **Build Command:** `pip install -e . && pip install python-socketio`
   - **Start Command:** `python web_interface/analytics_server.py`
   - **Health Check:** `/api/analytics/summary`

### 4️⃣ Access Dashboard
```
https://your-app-name.onrender.com
```

## What You Get

✅ Real-time analytics dashboard
✅ WebSocket live updates
✅ All fraud detection metrics
✅ Free SSL certificate
✅ Auto-deploy on git push
✅ Health monitoring

## Configuration

The server automatically uses Render's environment:
- `PORT` - Set by Render (usually 10000)
- `HOST` - Set to `0.0.0.0` for external access
- `DEBUG` - Set to `False` for production

## Free Tier Notes

- Spins down after 15 minutes of inactivity
- Takes ~30 seconds to spin up when accessed
- 750 hours/month free
- Perfect for demos and testing

## Upgrade to Paid ($7/month)

Benefits:
- Always on (no spin down)
- Instant response
- Better for production use

## Monitoring

View logs in Render dashboard:
1. Click your service
2. Go to "Logs" tab
3. See real-time server logs

## Troubleshooting

**Server won't start?**
- Check logs in Render dashboard
- Verify all dependencies in `pyproject.toml`

**Can't connect?**
- Free tier: Wait 30 seconds for spin-up
- Check health check endpoint is responding

**WebSocket issues?**
- CORS already configured for all origins
- Check browser console for errors

## Next Steps

After deployment:
1. Test all features
2. Enable live streaming
3. Monitor performance
4. Consider custom domain
5. Set up monitoring alerts

---

Need detailed help? See `../RENDER_DEPLOYMENT_GUIDE.md`
