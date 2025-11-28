# Environment Variables Configuration

This document describes all environment variables used throughout the TraceQA project.

## Backend Environment Variables

Location: `/backend/.env`

### API Keys

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key for AI model access | Yes | - |
| `LANDINGAI_API_KEY` | Landing AI API key for document parsing | Yes | - |
| `POSTMAN_API_KEY` | Postman API key (optional) | No | - |

### API Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENROUTER_BASE_URL` | Base URL for OpenRouter API | No | `https://openrouter.ai/api/v1` |
| `DEFAULT_MODEL` | Default AI model to use | No | `nvidia/nemotron-nano-12b-v2-vl:free` |
| `LANDINGAI_BASE_URL` | Base URL for Landing AI API | No | `https://api.va.landing.ai/v1/ade` |

### Application URLs

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BACKEND_URL` | Backend server URL | No | `http://localhost:8000` |
| `FRONTEND_URL` | Frontend application URL | No | `http://localhost:3000` |

### Legacy Variables (Not Currently Used)

| Variable | Description |
|----------|-------------|
| `PINECONE_API_KEY` | Pinecone vector database API key (replaced by FAISS) |
| `PINECONE_ENVIRONMENT` | Pinecone environment (replaced by FAISS) |
| `PINECONE_INDEX_NAME` | Pinecone index name (replaced by FAISS) |

## Frontend Environment Variables

Location: `/frontend/.env.local`

### API Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL for client-side requests | Yes | `http://localhost:8000` |

> **Note:** In Next.js, environment variables must be prefixed with `NEXT_PUBLIC_` to be accessible in the browser.

## Setup Instructions

### Backend Setup

1. Copy the example environment file:
   ```bash
   cd backend
   cp .env.example .env
   ```

2. Edit `.env` and fill in your API keys:
   ```bash
   OPENROUTER_API_KEY=your_actual_api_key_here
   LANDINGAI_API_KEY=your_actual_api_key_here
   ```

3. (Optional) Customize URLs for deployment:
   ```bash
   BACKEND_URL=https://your-backend-domain.com
   FRONTEND_URL=https://your-frontend-domain.com
   ```

### Frontend Setup

1. Copy the example environment file:
   ```bash
   cd frontend
   cp .env.example .env.local
   ```

2. Edit `.env.local` if needed (default points to local backend):
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. For production deployment, update to production backend URL:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend-domain.com
   ```

## Development vs Production

### Local Development
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Both `.env` files use localhost URLs

### Production Deployment
- Update `BACKEND_URL` and `FRONTEND_URL` in backend `.env`
- Update `NEXT_PUBLIC_API_URL` in frontend `.env.local`
- Ensure CORS settings allow your frontend domain
- Use HTTPS URLs for production

## Security Notes

⚠️ **Important Security Practices:**

1. **Never commit `.env` files to version control**
   - `.env` files are listed in `.gitignore`
   - Use `.env.example` files as templates

2. **Rotate API keys regularly**
   - Especially if keys are exposed or shared

3. **Use different keys for development and production**
   - Avoid using production keys in development

4. **Restrict API key permissions**
   - Use minimum required permissions for each service

5. **Environment-specific configurations**
   - Use separate `.env` files for different environments
   - Never mix development and production credentials

## Troubleshooting

### Backend can't find environment variables
- Ensure `.env` file exists in `/backend` directory
- Check file permissions (should be readable)
- Verify no typos in variable names (case-sensitive)

### Frontend can't access API
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Remember to restart Next.js dev server after changing `.env.local`
- Check browser console for CORS errors

### API calls failing
- Verify API keys are valid and active
- Check base URLs are accessible
- Ensure no trailing slashes in URLs
