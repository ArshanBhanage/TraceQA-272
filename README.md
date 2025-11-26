# TraceQA

Full-stack application with Next.js frontend and FastAPI backend, integrated with LangChain, LangGraph, Pinecone, OpenRouter, and Landing AI.

## Project Structure

```
TraceQA-272/
├── frontend/          # Next.js frontend application
└── backend/           # FastAPI backend application
```

## Quick Start

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Run the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Activate the virtual environment:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Create environment file and add your API keys:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the development server:
```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Technologies

### Frontend
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS

### Backend
- FastAPI
- Python 3.13
- LangChain & LangGraph
- Pinecone Vector Database
- OpenAI/OpenRouter API
- Landing AI

## Development

Both frontend and backend support hot-reloading during development.

### Frontend Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

### Backend
The backend uses `uvicorn --reload` for automatic reloading on code changes.

## Environment Variables

### Frontend (.env)
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

### Backend (.env)
- `OPENAI_API_KEY` - OpenAI API key
- `OPENROUTER_API_KEY` - OpenRouter API key
- `PINECONE_API_KEY` - Pinecone API key
- `PINECONE_ENVIRONMENT` - Pinecone environment
- `PINECONE_INDEX_NAME` - Pinecone index name
- `LANDINGAI_API_KEY` - Landing AI API key

## License

MIT
