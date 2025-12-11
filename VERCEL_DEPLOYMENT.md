# Vercel Deployment Guide

This guide will help you deploy Nexus Core v2.0 on Vercel.

## Prerequisites

1. A Vercel account (sign up at [vercel.com](https://vercel.com))
2. Google Gemini API Key (get one from [Google AI Studio](https://makersuite.google.com/app/apikey))
3. Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### 1. Push Your Code to Git

Make sure your code is in a Git repository:

```bash
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### 2. Import Project to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your Git repository
3. Vercel will automatically detect the project structure

### 3. Configure Environment Variables

In the Vercel project settings, add the following environment variable:

- **Name:** `GEMINI_API_KEY`
- **Value:** Your Google Gemini API key

**To add environment variables:**
1. Go to your project settings in Vercel
2. Navigate to "Environment Variables"
3. Add `GEMINI_API_KEY` with your API key value
4. Make sure it's available for Production, Preview, and Development

### 4. Configure Build Settings

Vercel should automatically detect the build configuration from `vercel.json`, but verify:

- **Framework Preset:** Other
- **Build Command:** `cd frontend && npm install && npm run build`
- **Output Directory:** `frontend/dist`
- **Install Command:** `cd frontend && npm install`

### 5. Deploy

Click "Deploy" and wait for the build to complete.

## Important Notes

### File Storage Limitations

⚠️ **Vercel serverless functions use ephemeral storage (`/tmp`). Data stored in `/tmp` will be lost between function invocations.**

For production use, you have several options:

#### Option 1: Vercel Blob Storage (Recommended)

1. Install Vercel Blob:
   ```bash
   npm install @vercel/blob
   ```

2. Get your Blob Store token from Vercel dashboard

3. Update the storage adapter to use Vercel Blob (see `backend/core/storage_adapter.py`)

#### Option 2: External Database

Use MongoDB, PostgreSQL, or another database service:
- MongoDB Atlas (free tier available)
- Supabase (PostgreSQL)
- PlanetScale (MySQL)

Update `backend/core/graph_logic.py` to use database instead of file storage.

#### Option 3: External File Storage

Use services like:
- AWS S3
- Cloudflare R2
- Google Cloud Storage

### Current Storage Behavior

- **Local Development:** Uses `data/` directory (persistent)
- **Vercel Deployment:** Uses `/tmp/nexus_data` (ephemeral)

Data will persist during a single function execution but will be lost when:
- Function times out
- New deployment occurs
- Function is cold-started

## Troubleshooting

### Build Fails

1. Check that all dependencies are in `requirements.txt` (root level)
2. Verify Node.js version (requires 16+)
3. Check build logs in Vercel dashboard

### API Routes Not Working

1. Verify `api/[...path].py` exists
2. Check that `mangum` is in `requirements.txt`
3. Ensure Python runtime is set to 3.9+

### Environment Variables Not Loading

1. Verify `GEMINI_API_KEY` is set in Vercel project settings
2. Redeploy after adding environment variables
3. Check function logs for errors

## Post-Deployment

After successful deployment:

1. Visit your Vercel deployment URL
2. Test the application functionality
3. Monitor function logs for any errors
4. Consider setting up persistent storage (see options above)

## Development vs Production

- **Local Development:** Run `start_nexus.bat` (Windows) or use `uvicorn` and `vite` separately
- **Vercel Production:** Automatically handles routing and serverless functions

## Support

For issues or questions:
1. Check Vercel function logs
2. Review build logs
3. Verify all environment variables are set correctly

