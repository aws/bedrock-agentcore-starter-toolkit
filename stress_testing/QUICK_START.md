# Quick Start Guide - Stress Testing Framework

## 🚀 Get Started in 2 Minutes

### Option 1: Run Complete Demo (Recommended)

Run the investor presentation demo with live dashboard:

```bash
python -m stress_testing.demo
```

This will:
1. Start the dashboard server
2. Open the investor dashboard in your browser
3. Run a 10-minute stress test with live metrics
4. Generate a complete report

### Option 2: Dashboard Only

Just want to see the dashboard?

```bash
python -m stress_testing.cli --dashboard-only
```

Then open: http://localhost:5000/investor

### Option 3: Run Specific Scenarios

```bash
# Investor presentation (10 minutes)
python -m stress_testing.cli --scenario investor

# Peak load test (30 minutes)
python -m stress_testing.cli --scenario peak-load
```

## 📊 What You'll See

### Investor Dashboard
- **Hero Metrics**: Total transactions, fraud blocked, money saved, ROI
- **Real-time Updates**: Live TPS, response times, accuracy
- **Business Value**: Cost savings, competitive advantages
- **Transaction Flow**: Visual representation of AI agent coordination

### Console Output
- Real-time progress updates every 10 seconds
- Current TPS and transaction counts
- Fraud detection statistics
- Money saved calculations

## 📁 Results

After running a test, find results in:
- `stress_testing/results/test_results/` - JSON test results
- `stress_testing/results/reports/` - Markdown and HTML reports

## 🎯 Key Features Demonstrated

1. **High-Volume Load Generation**
   - Realistic transaction data
   - Configurable TPS (up to 10,000+)
   - Multiple load patterns (ramp-up, sustained, burst)

2. **Real-Time Metrics**
   - System performance metrics
   - Business value metrics
   - Agent coordination metrics

3. **Failure Injection** (in investor scenario)
   - Simulated Lambda crashes
   - Automatic recovery demonstration
   - Resilience validation

4. **Investor-Grade Presentation**
   - Beautiful, animated dashboard
   - Business-focused narratives
   - Competitive benchmarks
   - ROI calculations

## 🛠️ Requirements

```bash
pip install flask flask-cors
```

That's it! The framework uses mostly standard library.

## 💡 Tips

1. **For Presentations**: Use `--scenario investor` for a 10-minute impressive demo
2. **For Testing**: Use `--scenario peak-load` for comprehensive performance testing
3. **Dashboard Port**: Change port with `--port 8080` if 5000 is busy
4. **Multiple Runs**: Each test generates a unique ID and separate results

## 🎬 Demo Flow

The investor presentation scenario:
1. **0-60s**: Ramp up from 0 to 8,000 TPS
2. **60-300s**: Sustained load at 5,000 TPS
3. **300-330s**: Failure injection (Lambda crash)
4. **330-600s**: Recovery and continued operation

Watch the dashboard to see:
- Metrics climbing during ramp-up
- Steady performance during sustained load
- Brief degradation during failure
- Automatic recovery
- Final impressive numbers

## 📈 Expected Results

After a successful investor presentation run:
- **Total Transactions**: ~150,000+
- **Fraud Detected**: ~3,000 (2% fraud rate)
- **Money Saved**: ~$900,000 (at $300/fraud)
- **ROI**: 180%+
- **Accuracy**: 95%
- **Response Time**: <200ms average

## 🆘 Troubleshooting

**Port already in use?**
```bash
python -m stress_testing.cli --dashboard-only --port 8080
```

**Dashboard not updating?**
- Refresh the browser page
- Check console for errors
- Ensure stress test is running

**Want to stop early?**
- Press `Ctrl+C` in the terminal
- Test will gracefully shut down
- Results will still be saved

## 🎯 Next Steps

1. Review generated reports in `stress_testing/results/reports/`
2. Customize scenarios in `stress_testing/config.py`
3. Integrate with your fraud detection API
4. Add custom metrics collection
5. Extend dashboard with your branding

## 📚 More Information

- Full documentation: `stress_testing/README.md`
- Architecture: `.kiro/specs/stress-testing-framework/design.md`
- Task completion: `stress_testing/TASK_*_SUMMARY.md`

---

**Ready to impress investors? Run the demo now!**

```bash
python -m stress_testing.demo
```
