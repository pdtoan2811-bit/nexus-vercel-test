# Vercel Deployment Troubleshooting

## "No Production Deployment" Issue

If you see "No Production Deployment" in Vercel, follow these steps:

### 1. Check Build Logs

1. Go to your Vercel project dashboard
2. Click on the failed deployment
3. Review the build logs for errors

### 2. Common Issues and Fixes

#### Issue: Build Command Fails
**Symptoms:** Build fails during `npm install` or `npm run build`

**Solutions:**
- Check Node.js version (should be 16+)
- Verify `frontend/package.json` has all dependencies
- Check if `frontend/node_modules` is in `.gitignore` (it should be)

#### Issue: Python Function Not Found
**Symptoms:** API routes return 404 or 500 errors

**Solutions:**
- Verify `api/[...path].py` exists
- Check that `requirements.txt` includes `mangum`
- Ensure Python runtime is set to 3.9 in `vercel.json`

#### Issue: Frontend Not Loading
**Symptoms:** Blank page or 404 on root URL

**Solutions:**
- Verify `outputDirectory` is set to `frontend/dist` in `vercel.json`
- Check that `frontend/dist/index.html` exists after build
- Ensure rewrites are configured correctly

#### Issue: Environment Variables Missing
**Symptoms:** API returns errors about missing API keys

**Solutions:**
- Go to Vercel Project Settings → Environment Variables
- Add `GEMINI_API_KEY` with your API key
- Redeploy after adding variables

### 3. Manual Deployment Steps

If automatic deployment fails:

1. **Check Git Connection:**
   ```bash
   git remote -v
   # Should show your Vercel-connected repo
   ```

2. **Verify Build Locally:**
   ```bash
   cd frontend
   npm install
   npm run build
   # Check if dist/ folder is created
   ```

3. **Test Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   python -c "from mangum import Mangum; print('OK')"
   ```

### 4. Vercel Configuration Checklist

- [ ] `vercel.json` exists in root
- [ ] `outputDirectory` points to `frontend/dist`
- [ ] `buildCommand` is `cd frontend && npm install && npm run build`
- [ ] `api/[...path].py` exists
- [ ] `requirements.txt` exists in root
- [ ] `GEMINI_API_KEY` is set in Vercel environment variables

### 5. Debugging Python Functions

Add logging to `api/[...path].py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Handler initialized")
```

Check function logs in Vercel dashboard under "Functions" tab.

### 6. Force Redeploy

1. Go to Vercel dashboard
2. Click on your project
3. Go to "Deployments"
4. Click "Redeploy" on the latest deployment
5. Or trigger a new deployment by pushing to your main branch

### 7. Contact Support

If issues persist:
1. Check [Vercel Community Forums](https://community.vercel.com)
2. Review [Vercel Documentation](https://vercel.com/docs)
3. Contact Vercel Support with:
   - Deployment logs
   - Error messages
   - Your `vercel.json` configuration

