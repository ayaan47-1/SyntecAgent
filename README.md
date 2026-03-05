# Syntec Group AI Chatbot

An intelligent AI-powered chatbot for Syntec Group that provides document-based Q&A and general knowledge assistance. Built for both internal team reference and client-facing interactions on the Syntec website.

## Overview

This project consists of two main components:
- **Backend**: Flask-based API with OpenAI GPT-4o integration and ChromaDB vector database
- **Frontend**: React-based chat interface with document management

### Key Features

- Document-based Q&A using semantic search
- GPT-4o powered responses with source citations
- Dual-source mode (local documents + internet/general knowledge)
- Document management (upload, list, delete)
- Real-time chat interface
- Rate limiting and security features
- Docker support for easy deployment
- BuildUSA knowledge base integration

## Technology Stack

### Backend
- Python 3.12
- Flask 3.0 + Flask-CORS
- OpenAI GPT-4o API
- ChromaDB (vector database)
- LangChain (document processing)
- PyPDF2 (PDF parsing)
- Flask-Limiter (rate limiting)
- Gunicorn (production server)

### Frontend
- React 19.1
- Vite 7.0
- Modern CSS (dark theme)
- Error boundaries for stability

## Prerequisites

- Python 3.12 or higher
- Node.js 20 or higher
- OpenAI API key
- Docker and Docker Compose (optional, for containerized deployment)

## Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   cd /Users/ayaan/Projects/AI_Chatbot
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost:5001

### Option 2: Manual Setup

#### Backend Setup

1. **Create virtual environment**
   ```bash
   python3.12 -m venv chatbot_env
   source chatbot_env/bin/activate  # On Windows: chatbot_env\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

4. **Run the backend**
   ```bash
   python app2.py
   ```
   The backend will start on http://localhost:5001

#### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd chatbot-frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment (optional)**
   ```bash
   cp .env.example .env
   # Edit if you need to change the API URL
   ```

4. **Run the development server**
   ```bash
   npm run dev
   ```
   The frontend will start on http://localhost:5176

5. **Build for production**
   ```bash
   npm run build
   npm run preview
   ```

## Usage

### Document Ingestion

#### Via API - Single Document
```bash
curl -X POST http://localhost:5001/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/document.pdf"
  }'
```

#### Via API - Folder of Documents
```bash
curl -X POST http://localhost:5001/api/ingest-folder \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/path/to/documents"
  }'
```

### Chat Interface

1. Open the web interface
2. Select source mode:
   - **Documents**: Search through uploaded documents
   - **Internet (GPT-4o)**: Use general knowledge
3. Type your question and press Enter or click Send
4. View responses with source citations

### Document Management

1. Click the "Manage" button in the header
2. View all uploaded documents with statistics
3. Delete documents as needed

## API Endpoints

### Health Check
```
GET /api/health
```
Returns system status and database count.

### Document Ingestion
```
POST /api/ingest
Body: { "file_path": "path/to/file.pdf" }
```

```
POST /api/ingest-folder
Body: { "folder_path": "path/to/folder" }
```

### Chat
```
POST /api/chat
Body: {
  "question": "Your question here",
  "source": "documents" | "internet"
}
```

### Statistics
```
GET /api/stats
```
Returns document and chunk counts.

### Document Management
```
GET /api/documents
```
List all documents.

```
DELETE /api/documents/:document_name
```
Delete a specific document.

## Configuration

### Backend Environment Variables

Create a `.env` file in the root directory:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
PORT=5001
FLASK_ENV=development  # or production

# CORS Configuration (comma-separated origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:5176

# Optional: File size limit (default: 50MB)
MAX_CONTENT_LENGTH=52428800
```

### Frontend Environment Variables

Create a `.env` file in `chatbot-frontend/`:

```env
# Backend API URL
VITE_API_URL=http://localhost:5001/api

# For production
# VITE_API_URL=https://your-api-domain.com/api
```

## Rate Limits

The API implements the following rate limits:

- Health check: 10 requests per minute
- Chat: 30 requests per minute
- Document ingestion: 10 requests per hour
- Folder ingestion: 5 requests per hour
- Stats & Documents list: 30 requests per minute
- Document deletion: 10 requests per hour
- Global: 200 requests per day, 50 per hour

## Security Features

- Input sanitization (HTML stripping, control character removal)
- Path traversal prevention
- Rate limiting on all endpoints
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- CORS restrictions
- Environment variable validation
- Error boundaries in React

## Project Structure

```
AI_Chatbot/
├── app2.py                 # Main backend application
├── main.py                 # Legacy ingestion script
├── requirements.txt        # Python dependencies
├── Dockerfile             # Backend Docker configuration
├── docker-compose.yml     # Multi-container setup
├── .env.example          # Environment template
├── .gitignore            # Git ignore rules
├── .dockerignore         # Docker ignore rules
├── chroma_db/            # Vector database storage
├── data/                 # Document storage
│   ├── BuildUSA_Master_Knowledge_Document.pdf
│   ├── Proforma.pdf
│   └── testpage.pdf
└── chatbot-frontend/
    ├── src/
    │   ├── App.jsx           # Main app component
    │   ├── ChatWidget.jsx    # Chat interface
    │   ├── DocumentManager.jsx # Document management
    │   ├── ErrorBoundary.jsx  # Error handling
    │   └── App.css           # Styles
    ├── package.json          # Node dependencies
    ├── vite.config.js        # Vite configuration
    ├── Dockerfile            # Frontend Docker config
    ├── nginx.conf            # Nginx configuration
    └── .env.example          # Frontend env template
```

## Development

### Running Tests

```bash
# Backend (when test suite is added)
pytest

# Frontend
npm test
```

### Code Quality

```bash
# Frontend linting
npm run lint
```

### Building for Production

#### Backend with Gunicorn
```bash
gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 120 app2:app
```

#### Frontend Production Build
```bash
cd chatbot-frontend
npm run build
# Serve the dist/ folder with your web server
```

## Deployment

### Docker Production Deployment

1. **Update environment variables for production**
   ```bash
   # Update .env with production API key
   # Update CORS_ORIGINS with production domain
   ```

2. **Build and deploy**
   ```bash
   docker-compose up -d --build
   ```

3. **Monitor logs**
   ```bash
   docker-compose logs -f
   ```

### Traditional Deployment

1. **Backend**: Deploy using Gunicorn + Nginx
2. **Frontend**: Build and serve static files with Nginx
3. **Database**: Ensure ChromaDB persistence directory is backed up

## Troubleshooting

### Backend Issues

**Problem**: OpenAI API key error
```
Solution: Ensure OPENAI_API_KEY is set in .env file
```

**Problem**: ChromaDB connection issues
```
Solution: Check that ./chroma_db directory exists and has write permissions
```

**Problem**: Rate limit errors
```
Solution: Reduce request frequency or adjust rate limits in app2.py
```

### Frontend Issues

**Problem**: Cannot connect to backend
```
Solution: Verify VITE_API_URL points to correct backend URL
Check that backend is running on port 5001
```

**Problem**: CORS errors
```
Solution: Add frontend URL to CORS_ORIGINS in backend .env
```

## Contributing

This is an internal Syntec Group project. For contributions:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit for review

## About Syntec Group

Syntec Group is focused on innovative building solutions through BuildUSA (BUSA), which implements a modular approach to construction.

- Website: https://syntecgroup.com/
- BuildUSA Blog: https://build.syntecgroup.com/

### BuildUSA Overview

BuildUSA is built on the **Prototype Initiative** framework:
- **Research**: Understanding modular building approaches
- **Process**: Developing efficient construction workflows
- **Execution**: Implementing scalable building solutions

## License

Internal use only - Syntec Group

## Support

For issues or questions:
- Internal team: Contact the development team
- Technical issues: Check logs and troubleshooting section

## Roadmap

Future improvements planned:
- [ ] User authentication and role-based access
- [ ] Multi-user chat sessions
- [ ] Advanced analytics dashboard
- [ ] Integration with Syntec website
- [ ] Support for additional document formats (Word, Excel, etc.)
- [ ] Webhook notifications for document updates
- [ ] API key management interface
- [ ] Enhanced search filters
- [ ] Export chat history

---

Built with Claude Code for Syntec Group
