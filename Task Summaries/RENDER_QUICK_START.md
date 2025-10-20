# Render Quick Start - Analytics Dashboard

## 🚀 Deploy in 5 Minutes

### Step 1: Test Locally (Optional but Recommended)
```bash
python test_render_deployment.py
```

### Step 2: Push to GitHub
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### Step 3: Deploy on Render
1. Go to [render.com](https://render.com) and sign up
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Render auto-detects `render.yaml` ✨
5. Click **"Create Web Service"**
6. Wait 2-3 minutes for deployment

### Step 4: Access Your Dashboard
Your dashboard will be live at:
```
https://your-app-name.onrender.com
```

## 🎯 What Gets Deployed

- **Analytics Dashboard** with real-time charts
- **WebSocket support** for live updates
- **All API endpoints** for fraud detection analytics
- **Auto-scaling** and health checks

## 💰 Cost

**Free Tier:**
- 750 hours/month free
- Spins down after 15 min inactivity
- Perfect for demos!

**Paid Tier (Optional):**
- $7/month for always-on service
- No spin-down delays

## 🔧 Files Created

- ✅ `render.yaml` - Deployment configuration
- ✅ `RENDER_DEPLOYMENT_GUIDE.md` - Full guide
- ✅ `test_render_deployment.py` - Pre-deployment tests
- ✅ Updated `analytics_server.py` - Production-ready

## 📊 Features Available

Once deployed, you get:
- Real-time fraud detection metrics
- Pattern detection heatmaps
- Decision accuracy tracking
- WebSocket live streaming
- Stress test metrics
- Interactive charts

## 🐛 Troubleshooting

**Build fails?**
```bash
# Check dependencies are in pyproject.toml
pip install -e .
```

**Can't access dashboard?**
- Wait 30 seconds for free tier spin-up
- Check Render logs in dashboard

**WebSocket not working?**
- CORS is already configured
- Check browser console for errors

## 📚 Need More Help?

See `RENDER_DEPLOYMENT_GUIDE.md` for:
- Detailed configuration options
- Security best practices
- Monitoring and logging
- Custom domain setup
- Production considerations

## ✅ Checklist

- [ ] Code tested locally
- [ ] Pushed to GitHub
- [ ] Render account created
- [ ] Web service created
- [ ] Deployment successful
- [ ] Dashboard accessible
- [ ] WebSocket working

---

**That's it!** Your analytics dashboard is now live on Render! 🎉
