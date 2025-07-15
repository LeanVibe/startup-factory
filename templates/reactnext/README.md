# ReactNext Template - Next.js + React + FastAPI Startup Template

A production-ready template for AI-powered startups using **Next.js 14**, **React 18**, **TypeScript**, and **FastAPI** backend.

## Features

- ⚡ **Next.js 14** with App Router and Server Components
- ⚛️ **React 18** with TypeScript support
- 🎨 **Tailwind CSS** for modern styling
- 🔒 **NextAuth.js** for authentication
- 🐍 **FastAPI** backend with async/await
- 🗄️ **PostgreSQL** with SQLAlchemy ORM
- 🐳 **Docker** containerization 
- 🧪 **Testing** with Jest, Playwright, and pytest
- 📊 **Monitoring** with Prometheus and Grafana
- 🚀 **Production-ready** deployment configuration

## Architecture

```
{{cookiecutter.project_slug}}/
├── frontend/          # Next.js React application
│   ├── app/          # Next.js App Router
│   ├── components/   # React components
│   ├── lib/          # Utilities and configurations
│   └── public/       # Static assets
├── backend/          # FastAPI application  
│   ├── app/          # FastAPI application code
│   ├── alembic/      # Database migrations
│   └── tests/        # Backend tests
├── docker-compose.yml # Multi-service deployment
└── docs/             # Documentation
```

## Technology Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context + useReducer
- **Authentication**: NextAuth.js
- **Testing**: Jest + Playwright
- **Build Tool**: Built-in Next.js tooling

### Backend  
- **Framework**: FastAPI with async/await
- **Language**: Python 3.11+
- **Database ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: JWT tokens
- **Testing**: pytest with async support
- **API Documentation**: Automatic OpenAPI/Swagger

### Infrastructure
- **Database**: PostgreSQL 15
- **Caching**: Redis (optional)
- **Containerization**: Docker & Docker Compose
- **Process Management**: Supervisor (production)
- **Monitoring**: Prometheus + Grafana
- **Reverse Proxy**: Nginx (production)

## Quick Start

1. **Generate Project**:
   ```bash
   cookiecutter templates/reactnext/
   ```

2. **Start Development**:
   ```bash
   cd {{cookiecutter.project_slug}}
   docker-compose up --build
   ```

3. **Access Services**:
   - Frontend: http://localhost:{{cookiecutter.base_port}}
   - Backend API: http://localhost:{{cookiecutter.api_port}}/docs
   - Database: localhost:{{cookiecutter.db_port}}

## Port Configuration

- **Frontend**: {{cookiecutter.base_port}} (Next.js dev server)
- **Backend**: {{cookiecutter.api_port}} (FastAPI application)
- **Database**: {{cookiecutter.db_port}} (PostgreSQL)
- **Redis**: {{cookiecutter.base_port|int + 10}} (if enabled)

## Development Commands

### Frontend
```bash
cd frontend
npm install
npm run dev        # Development server
npm run build      # Production build
npm test          # Run tests
npm run lint      # ESLint
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload  # Development server
pytest                         # Run tests
alembic upgrade head          # Database migrations
```

### Full Stack
```bash
docker-compose up --build     # Full development stack
docker-compose -f docker-compose.prod.yml up  # Production stack
```

## Environment Configuration

### Frontend (.env.local)
```env
NEXTAUTH_URL=http://localhost:{{cookiecutter.base_port}}
NEXTAUTH_SECRET=your-secret-key
NEXT_PUBLIC_API_URL=http://localhost:{{cookiecutter.api_port}}
```

### Backend (.env)
```env
DATABASE_URL=postgresql://user:pass@localhost:{{cookiecutter.db_port}}/{{cookiecutter.project_slug}}
SECRET_KEY=your-secret-key
CORS_ORIGINS=["http://localhost:{{cookiecutter.base_port}}"]
```

## Testing Strategy

### Frontend Testing
- **Unit Tests**: Jest + React Testing Library
- **Integration Tests**: Jest with API mocking
- **E2E Tests**: Playwright for full user workflows
- **Type Checking**: TypeScript strict mode

### Backend Testing
- **Unit Tests**: pytest with async support
- **Integration Tests**: pytest with test database
- **API Tests**: pytest with httpx client
- **Performance Tests**: pytest-benchmark

## Deployment Options

### Development
```bash
docker-compose up --build
```

### Production  
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Deployment
- **Vercel**: Frontend deployment (recommended)
- **Railway/Render**: Full-stack deployment
- **AWS/GCP/Azure**: Container deployment
- **DigitalOcean**: App platform deployment

## Security Features

- **Authentication**: NextAuth.js with JWT tokens
- **Authorization**: Role-based access control
- **CORS**: Configurable cross-origin requests
- **Input Validation**: Pydantic models + Zod schemas
- **SQL Injection**: SQLAlchemy ORM protection
- **XSS Protection**: React built-in protections
- **CSRF Protection**: NextAuth.js built-in

## Performance Optimizations

- **Next.js**: Server-side rendering + static generation
- **React**: Automatic code splitting and lazy loading
- **FastAPI**: Async/await for high concurrency
- **Database**: Connection pooling and query optimization
- **Caching**: Redis for session and data caching
- **CDN**: Static asset optimization

## Monitoring & Observability

- **Application Metrics**: Prometheus metrics collection
- **Performance Monitoring**: Next.js analytics
- **Error Tracking**: Built-in error boundaries
- **Logging**: Structured logging with correlation IDs
- **Health Checks**: Automated service health monitoring

## Customization

### Adding New Components
```bash
# Frontend component
mkdir -p frontend/components/MyComponent
touch frontend/components/MyComponent/index.tsx
touch frontend/components/MyComponent/MyComponent.module.css

# Backend endpoint
touch backend/app/api/routes/my_endpoint.py
```

### Database Modifications
```bash
cd backend
alembic revision --autogenerate -m "Add new table"
alembic upgrade head
```

### Styling Customization
- Modify `frontend/tailwind.config.js` for theme customization
- Add custom CSS in `frontend/app/globals.css`
- Use CSS modules for component-specific styles

## Support & Documentation

- **API Documentation**: Available at `/docs` endpoint
- **Component Storybook**: `npm run storybook`
- **Architecture Decision Records**: `docs/adr/`
- **Deployment Guide**: `docs/deployment.md`
- **Contributing Guide**: `CONTRIBUTING.md`

## License

MIT License - see LICENSE file for details.

---

**Generated with Startup Factory - AI-Accelerated MVP Development Platform**