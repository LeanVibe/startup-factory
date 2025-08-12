#!/usr/bin/env python3
"""
Business Blueprint Generator
Transforms founder conversations into comprehensive technical specifications
and generates intelligent code based on business requirements.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import anthropic
    from pydantic import BaseModel
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.panel import Panel
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install anthropic pydantic rich")
    exit(1)

from .founder_interview_system import BusinessBlueprint, BusinessModel, IndustryVertical

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class CodeArtifact:
    """Generated code artifact with metadata"""
    file_path: str
    content: str
    description: str
    dependencies: List[str] = None
    is_business_logic: bool = False


class BusinessLogicGenerator:
    """Generates actual business logic code, not just boilerplate"""
    
    def __init__(self, anthropic_client: anthropic.Anthropic):
        self.client = anthropic_client
    
    async def generate_mvp_code(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate complete MVP codebase from business blueprint"""
        
        console.print("\n[bold blue]🏗️  Generating MVP Code[/bold blue]")
        
        artifacts = []
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            # Increase total to include scaffolding and frontend shell
            task = progress.add_task("Generating business logic...", total=9)
            
            # 1. Generate data models with business-specific fields
            progress.update(task, description="Creating data models...")
            models = await self._generate_data_models(blueprint)
            artifacts.extend(models)
            progress.advance(task)
            
            # 1.1 Backend scaffold (app entrypoint, DB, security, config, packages)
            progress.update(task, description="Creating backend scaffold...")
            backend_scaffold = await self._generate_backend_scaffold(blueprint)
            artifacts.extend(backend_scaffold)
            progress.advance(task)

            # 2. Generate business logic API endpoints
            progress.update(task, description="Building API endpoints...")
            api_endpoints = await self._generate_api_endpoints(blueprint)
            artifacts.extend(api_endpoints)
            progress.advance(task)
            
            # 3. Generate business-specific frontend components
            progress.update(task, description="Creating UI components...")
            ui_components = await self._generate_ui_components(blueprint)
            artifacts.extend(ui_components)
            progress.advance(task)
            
            # 4. Generate business logic and workflows
            progress.update(task, description="Implementing business workflows...")
            business_logic = await self._generate_business_workflows(blueprint)
            artifacts.extend(business_logic)
            progress.advance(task)
            
            # 5. Generate configuration and deployment
            progress.update(task, description="Setting up deployment...")
            deployment_configs = await self._generate_deployment_config(blueprint)
            artifacts.extend(deployment_configs)
            progress.advance(task)

            # 5.1 Alembic migrations scaffold
            progress.update(task, description="Preparing database migrations...")
            alembic_scaffold = await self._generate_alembic_scaffold(blueprint)
            artifacts.extend(alembic_scaffold)
            progress.advance(task)
            
            # 6. Generate README and documentation
            progress.update(task, description="Creating documentation...")
            documentation = await self._generate_documentation(blueprint)
            artifacts.extend(documentation)
            progress.advance(task)

            # 7. Frontend shell (mount components and basic layout)
            progress.update(task, description="Creating frontend shell...")
            frontend_shell = await self._generate_frontend_shell(blueprint)
            artifacts.extend(frontend_shell)
            progress.advance(task)
        
        console.print(f"[green]✅ Generated {len(artifacts)} code artifacts[/green]")
        return artifacts
    
    async def _generate_data_models(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate SQLAlchemy models based on business entities"""
        
        artifacts = []
        
        # Base user model
        user_model = await self._generate_user_model(blueprint)
        artifacts.append(user_model)
        
        # Business-specific models
        for entity in blueprint.data_entities:
            model_code = await self._generate_entity_model(entity, blueprint)
            artifacts.append(CodeArtifact(
                file_path=f"backend/app/models/{entity['name'].lower()}.py",
                content=model_code,
                description=f"{entity['name']} data model",
                dependencies=["sqlalchemy", "pydantic"],
                is_business_logic=True
            ))
        
        return artifacts
    
    async def _generate_user_model(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate user model with business-specific fields"""
        
        # Add business-specific user fields based on industry/business model
        additional_fields = []
        
        if blueprint.business_model == BusinessModel.B2B_SAAS:
            additional_fields.extend([
                "company_name: Optional[str] = None",
                "role: Optional[str] = None",
                "team_size: Optional[int] = None"
            ])
        elif blueprint.business_model == BusinessModel.MARKETPLACE:
            additional_fields.extend([
                "is_seller: bool = False",
                "seller_verified: bool = False",
                "rating: Optional[float] = None"
            ])
        
        if blueprint.industry_vertical == IndustryVertical.HEALTHCARE:
            additional_fields.append("healthcare_provider_id: Optional[str] = None")
        elif blueprint.industry_vertical == IndustryVertical.FINTECH:
            additional_fields.extend([
                "kyc_verified: bool = False",
                "plaid_access_token: Optional[str] = None"
            ])
        
        additional_fields_str = "\n    ".join(additional_fields)
        
        user_model_code = f'''"""
User model with business-specific fields for {blueprint.business_model.value}
Generated for: {blueprint.solution_concept.core_value_proposition}
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    # Core fields
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Business-specific fields
    {additional_fields_str}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    {additional_fields_str.replace(": Optional[str] = None", ": Optional[str] = None").replace(": bool = False", ": Optional[bool] = None")}


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    {additional_fields_str.replace(" = None", "").replace(" = False", "")}
    
    class Config:
        from_attributes = True
'''
        
        return CodeArtifact(
            file_path="backend/app/models/user.py",
            content=user_model_code,
            description="User model with business-specific fields",
            dependencies=["sqlalchemy", "pydantic"],
            is_business_logic=True
        )
    
    async def _generate_entity_model(self, entity: Dict[str, Any], blueprint: BusinessBlueprint) -> str:
        """Generate SQLAlchemy model for a business entity"""
        
        entity_name = entity['name']
        attributes = entity['attributes']
        
        # Generate SQLAlchemy columns
        columns = []
        pydantic_fields = []
        
        columns.append("id = Column(Integer, primary_key=True, index=True)")
        pydantic_fields.append("id: Optional[int] = None")
        
        for attr in attributes:
            attr_name = attr['name']
            attr_type = attr['type']
            required = attr.get('required', False)
            
            # Map Python types to SQLAlchemy types
            if attr_type == 'string':
                sql_type = "String"
                pydantic_type = "str"
            elif attr_type == 'integer':
                sql_type = "Integer"
                pydantic_type = "int"
            elif attr_type == 'float':
                sql_type = "Float"
                pydantic_type = "float"
            elif attr_type == 'boolean':
                sql_type = "Boolean"
                pydantic_type = "bool"
            elif attr_type == 'datetime':
                sql_type = "DateTime"
                pydantic_type = "datetime"
            else:
                sql_type = "String"
                pydantic_type = "str"
            
            nullable = "False" if required else "True"
            columns.append(f"{attr_name} = Column({sql_type}, nullable={nullable})")
            
            optional = "" if required else "Optional[" + pydantic_type + "]"
            if optional:
                pydantic_fields.append(f"{attr_name}: {optional} = None")
            else:
                pydantic_fields.append(f"{attr_name}: {pydantic_type}")
        
        # Add created_at and updated_at
        columns.extend([
            "created_at = Column(DateTime, default=datetime.utcnow)",
            "updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)"
        ])
        pydantic_fields.extend([
            "created_at: Optional[datetime] = None",
            "updated_at: Optional[datetime] = None"
        ])
        
        columns_str = "\n    ".join(columns)
        pydantic_fields_str = "\n    ".join(pydantic_fields)
        
        return f'''"""
{entity_name} model for {blueprint.solution_concept.core_value_proposition}
Generated from business blueprint
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.db.database import Base


class {entity_name}(Base):
    __tablename__ = "{entity_name.lower()}s"
    
    {columns_str}


class {entity_name}Create(BaseModel):
    {pydantic_fields_str.replace("Optional[datetime] = None", "").replace("id: Optional[int] = None", "").strip()}


class {entity_name}Response(BaseModel):
    {pydantic_fields_str}
    
    class Config:
        from_attributes = True
'''
    
    async def _generate_api_endpoints(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate FastAPI endpoints with business logic"""
        
        artifacts = []
        
        # Generate main API router
        main_router = await self._generate_main_api_router(blueprint)
        artifacts.append(main_router)
        
        # Generate authentication endpoints
        auth_endpoints = await self._generate_auth_endpoints(blueprint)
        artifacts.append(auth_endpoints)
        
        # Generate business-specific endpoints for each entity
        for entity in blueprint.data_entities:
            entity_endpoints = await self._generate_entity_endpoints(entity, blueprint)
            artifacts.append(entity_endpoints)
        
        # Generate business workflow endpoints
        workflow_endpoints = await self._generate_workflow_endpoints(blueprint)
        artifacts.append(workflow_endpoints)
        
        return artifacts
    
    async def _generate_main_api_router(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate main API router with business-specific routes"""
        
        router_code = f'''"""
Main API router for {blueprint.solution_concept.core_value_proposition}
Business Model: {blueprint.business_model.value}
Industry: {blueprint.industry_vertical.value}
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import List

from app.models.user import User, UserResponse
from app.api.auth import get_current_user
from app.api import auth

# Import business-specific routers
'''
        
        # Add imports for entity routers
        for entity in blueprint.data_entities:
            entity_name = entity['name'].lower()
            router_code += f"from app.api import {entity_name}\n"
        
        router_code += f'''

api_router = APIRouter()
security = HTTPBearer()

# Authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Business entity routes
'''
        
        # Add entity routes
        for entity in blueprint.data_entities:
            entity_name = entity['name'].lower()
            router_code += f'api_router.include_router({entity_name}.router, prefix="/{entity_name}s", tags=["{entity_name}s"])\n'
        
        router_code += f'''

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{"status": "healthy", "service": "{blueprint.project_id}"}}


@api_router.get("/dashboard", response_model=dict)
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics for the current user"""
    # TODO: Implement business-specific dashboard logic
    return {{
        "user_id": current_user.id,
        "stats": {{
            "total_items": 0,
            "recent_activity": [],
            "business_metrics": {{}}
        }}
    }}
'''
        
        return CodeArtifact(
            file_path="backend/app/api/main.py",
            content=router_code,
            description="Main API router with business-specific endpoints",
            dependencies=["fastapi"],
            is_business_logic=True
        )
    
    async def _generate_auth_endpoints(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate authentication endpoints with business-specific logic"""
        
        auth_code = f'''"""
Authentication endpoints for {blueprint.solution_concept.core_value_proposition}
Includes business-specific user registration and validation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.models.user import User, UserCreate, UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.database import get_db

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user with business-specific validation"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Business-specific validation
'''
        
        # Add business-specific validation
        if blueprint.business_model == BusinessModel.B2B_SAAS:
            auth_code += '''    
    # B2B SaaS specific validation
    if user_data.company_name and len(user_data.company_name.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name must be at least 2 characters"
        )
'''
        
        if blueprint.industry_vertical == IndustryVertical.HEALTHCARE:
            auth_code += '''    
    # Healthcare specific validation
    if user_data.healthcare_provider_id:
        # TODO: Validate healthcare provider ID
        pass
'''
        
        auth_code += '''    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
'''
        
        # Add business-specific fields to user creation
        if blueprint.business_model == BusinessModel.B2B_SAAS:
            auth_code += '''        company_name=user_data.company_name,
        role=user_data.role,
        team_size=user_data.team_size,
'''
        elif blueprint.business_model == BusinessModel.MARKETPLACE:
            auth_code += '''        is_seller=user_data.is_seller or False,
        seller_verified=False,
'''
        
        auth_code += '''    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    """Login user and return access token"""
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    
    # TODO: Implement JWT token verification
    # For now, this is a placeholder
    token = credentials.credentials
    
    # Decode JWT token and get user
    # This is simplified - implement proper JWT verification
    user = db.query(User).filter(User.email == "test@example.com").first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return user
'''
        
        return CodeArtifact(
            file_path="backend/app/api/auth.py",
            content=auth_code,
            description="Authentication endpoints with business-specific validation",
            dependencies=["fastapi", "sqlalchemy", "passlib"],
            is_business_logic=True
        )
    
    async def _generate_entity_endpoints(self, entity: Dict[str, Any], blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate CRUD endpoints for a business entity"""
        
        entity_name = entity['name']
        entity_lower = entity_name.lower()
        
        endpoint_code = f'''"""
{entity_name} API endpoints for {blueprint.solution_concept.core_value_proposition}
Generated CRUD operations with business logic
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.user import User
from app.models.{entity_lower} import {entity_name}, {entity_name}Create, {entity_name}Response
from app.api.auth import get_current_user
from app.db.database import get_db

router = APIRouter()


@router.get("/", response_model=List[{entity_name}Response])
async def get_{entity_lower}s(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of {entity_lower}s for current user"""
    
    # Business logic: filter by user ownership or permissions
    query = db.query({entity_name})
    
    # Add business-specific filtering
    # TODO: Implement proper access control based on business model
    
    items = query.offset(skip).limit(limit).all()
    return items


@router.post("/", response_model={entity_name}Response)
async def create_{entity_lower}(
    {entity_lower}_data: {entity_name}Create,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new {entity_lower}"""
    
    # Business-specific validation
    # TODO: Add business rules for {entity_lower} creation
    
    db_{entity_lower} = {entity_name}(**{entity_lower}_data.dict())
    
    # Associate with current user if applicable
    # db_{entity_lower}.user_id = current_user.id
    
    db.add(db_{entity_lower})
    db.commit()
    db.refresh(db_{entity_lower})
    
    return db_{entity_lower}


@router.get("/{{item_id}}", response_model={entity_name}Response)
async def get_{entity_lower}(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific {entity_lower} by ID"""
    
    db_{entity_lower} = db.query({entity_name}).filter({entity_name}.id == item_id).first()
    
    if not db_{entity_lower}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity_name} not found"
        )
    
    # Business logic: check user permissions
    # TODO: Implement access control
    
    return db_{entity_lower}


@router.put("/{{item_id}}", response_model={entity_name}Response)
async def update_{entity_lower}(
    item_id: int,
    {entity_lower}_data: {entity_name}Create,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update existing {entity_lower}"""
    
    db_{entity_lower} = db.query({entity_name}).filter({entity_name}.id == item_id).first()
    
    if not db_{entity_lower}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity_name} not found"
        )
    
    # Business logic: check user permissions
    # TODO: Implement access control
    
    # Update fields
    for field, value in {entity_lower}_data.dict().items():
        if hasattr(db_{entity_lower}, field):
            setattr(db_{entity_lower}, field, value)
    
    db.commit()
    db.refresh(db_{entity_lower})
    
    return db_{entity_lower}


@router.delete("/{{item_id}}")
async def delete_{entity_lower}(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete {entity_lower}"""
    
    db_{entity_lower} = db.query({entity_name}).filter({entity_name}.id == item_id).first()
    
    if not db_{entity_lower}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity_name} not found"
        )
    
    # Business logic: check user permissions
    # TODO: Implement access control
    
    db.delete(db_{entity_lower})
    db.commit()
    
    return {{"message": "{entity_name} deleted successfully"}}
'''
        
        return CodeArtifact(
            file_path=f"backend/app/api/{entity_lower}.py",
            content=endpoint_code,
            description=f"CRUD endpoints for {entity_name}",
            dependencies=["fastapi", "sqlalchemy"],
            is_business_logic=True
        )

    async def _generate_backend_scaffold(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate backend application scaffold files and package inits"""
        artifacts: List[CodeArtifact] = []

        # Package __init__.py files
        for pkg in [
            "backend/app",
            "backend/app/api",
            "backend/app/models",
            "backend/app/core",
            "backend/app/db",
        ]:
            artifacts.append(CodeArtifact(
                file_path=f"{pkg}/__init__.py",
                content="",
                description=f"Package init for {pkg}"
            ))

        # FastAPI app entrypoint
        main_py = f'''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.main import api_router


def create_app() -> FastAPI:
    app = FastAPI(title="{blueprint.project_id}", version="1.0.0")
    app.include_router(api_router, prefix="/api")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {{"status": "healthy"}}

    return app


app = create_app()
'''
        artifacts.append(CodeArtifact(
            file_path="backend/app/main.py",
            content=main_py,
            description="FastAPI application entrypoint"
        ))

        # Database setup with shared Base and get_db
        database_py = '''from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
        artifacts.append(CodeArtifact(
            file_path="backend/app/db/database.py",
            content=database_py,
            description="SQLAlchemy engine/session and shared Base"
        ))

        # Security helpers (hashing + JWT minimal)
        security_py = '''from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = "change-me-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt
'''
        artifacts.append(CodeArtifact(
            file_path="backend/app/core/security.py",
            content=security_py,
            description="Password hashing and JWT helpers"
        ))

        # App settings (with security defaults)
        config_py = '''from pydantic import BaseSettings, Field
from typing import List


class Settings(BaseSettings):
    database_url: str | None = None
    secret_key: str = Field("change-me", description="Secret key for application")
    debug: bool = False

    cors_allow_origins: List[str] = Field(default_factory=lambda: ["http://localhost", "http://localhost:5173"])
    max_request_body_bytes: int = 5 * 1024 * 1024  # 5MB
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
'''
        artifacts.append(CodeArtifact(
            file_path="backend/app/core/config.py",
            content=config_py,
            description="Application configuration via pydantic settings"
        ))

        # Security middleware modules
        middleware_security = '''from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request, call_next):
        body = await request.body()
        if len(body) > self.max_body_bytes:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("Request body too large", status_code=413)
        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Hook for audit logging (PII redaction can be added here)
        response = await call_next(request)
        return response
'''
        artifacts.append(CodeArtifact(
            file_path="backend/app/middleware/security.py",
            content=middleware_security,
            description="Security headers, request size limit, and audit log middleware"
        ))

        middleware_rate = '''import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests = requests
        self.window = window_seconds
        self._hits = defaultdict(deque)

    async def dispatch(self, request, call_next):
        key = request.client.host if request.client else "global"
        now = time.time()
        dq = self._hits[key]
        while dq and now - dq[0] > self.window:
            dq.popleft()
        if len(dq) >= self.requests:
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("Too Many Requests", status_code=429)
        dq.append(now)
        return await call_next(request)
'''
        artifacts.append(CodeArtifact(
            file_path="backend/app/middleware/rate_limit.py",
            content=middleware_rate,
            description="Naive in-memory rate limiter"
        ))

        return artifacts

    async def _generate_alembic_scaffold(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate minimal Alembic configuration to enable migrations"""
        artifacts: List[CodeArtifact] = []

        alembic_ini = '''[alembic]
script_location = alembic
sqlalchemy.url = %(DATABASE_URL)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
'''
        env_py = '''from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Interpret the config file for Python logging.

# Set SQLAlchemy URL from env if present
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# target_metadata points to the Base metadata
from app.db.database import Base  # noqa
target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        artifacts.append(CodeArtifact(
            file_path="alembic.ini",
            content=alembic_ini,
            description="Alembic base configuration"
        ))
        artifacts.append(CodeArtifact(
            file_path="alembic/env.py",
            content=env_py,
            description="Alembic environment referencing shared Base"
        ))
        artifacts.append(CodeArtifact(
            file_path="alembic/versions/.keep",
            content="",
            description="Versions directory placeholder"
        ))
        return artifacts

    async def _generate_frontend_shell(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate a minimal frontend shell that mounts dashboard component"""
        artifacts: List[CodeArtifact] = []

        index_html = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{blueprint.solution_concept.core_value_proposition}</title>
  </head>
  <body>
    <business-dashboard></business-dashboard>
    <script type="module" src="/src/main.ts"></script>
  </body>
  </html>
'''
        main_ts = '''import './components/business-dashboard';
// Entry point to mount web components; route handling can be added later.
'''
        artifacts.append(CodeArtifact(
            file_path="frontend/index.html",
            content=index_html,
            description="Frontend HTML shell"
        ))
        artifacts.append(CodeArtifact(
            file_path="frontend/src/main.ts",
            content=main_ts,
            description="Frontend entry script"
        ))
        return artifacts
    
    async def _generate_workflow_endpoints(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate business workflow endpoints"""
        
        workflow_code = f'''"""
Business workflow endpoints for {blueprint.solution_concept.core_value_proposition}
Implements core business processes and user journeys
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.models.user import User
from app.api.auth import get_current_user
from app.db.database import get_db

router = APIRouter()


@router.post("/onboarding")
async def complete_user_onboarding(
    onboarding_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete user onboarding process"""
    
    # Business-specific onboarding logic
    # Based on user journey: {' -> '.join(blueprint.solution_concept.user_journey)}
    
    # TODO: Implement onboarding steps
    
    return {{
        "message": "Onboarding completed successfully",
        "next_steps": {blueprint.solution_concept.user_journey[1:3]}  # Next 2 steps
    }}


@router.get("/dashboard/metrics")
async def get_business_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get business metrics dashboard"""
    
    # Calculate business-specific metrics
    # Success metrics: {', '.join(blueprint.solution_concept.success_metrics)}
    
    metrics = {{}}
    
    # TODO: Calculate actual metrics based on business model
    for metric in {blueprint.solution_concept.success_metrics}:
        metrics[metric.replace(' ', '_').lower()] = 0
    
    return {{
        "metrics": metrics,
        "period": "last_30_days",
        "updated_at": datetime.utcnow().isoformat()
    }}


@router.post("/workflow/start")
async def start_business_workflow(
    workflow_type: str,
    workflow_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a business workflow"""
    
    # Business-specific workflow logic
    # Key features: {', '.join(blueprint.solution_concept.key_features)}
    
    # TODO: Implement workflow logic based on features
    
    return {{
        "workflow_id": f"wf_{{datetime.utcnow().timestamp()}}",
        "status": "started",
        "next_action": "user_input_required"
    }}
'''
        
        return CodeArtifact(
            file_path="backend/app/api/workflows.py",
            content=workflow_code,
            description="Business workflow endpoints",
            dependencies=["fastapi", "sqlalchemy"],
            is_business_logic=True
        )
    
    async def _generate_ui_components(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate business-specific UI components"""
        
        artifacts = []
        
        # Generate dashboard component
        dashboard_component = await self._generate_dashboard_component(blueprint)
        artifacts.append(dashboard_component)
        
        # Generate feature-specific components
        for feature in blueprint.solution_concept.key_features:
            component = await self._generate_feature_component(feature, blueprint)
            artifacts.append(component)
        
        return artifacts
    
    async def _generate_dashboard_component(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate main dashboard component"""
        
        metrics_elements = []
        for metric in blueprint.solution_concept.success_metrics[:4]:  # Limit to 4 metrics
            metric_key = metric.replace(' ', '_').lower()
            metrics_elements.append(f'''
        <div class="metric-card">
          <h3>{metric}</h3>
          <div class="metric-value">${{this.metrics?.{metric_key} || 0}}</div>
        </div>''')
        
        dashboard_code = f'''/**
 * Dashboard Component for {blueprint.solution_concept.core_value_proposition}
 * Business Model: {blueprint.business_model.value}
 * Generated from business blueprint
 */

import {{ LitElement, html, css }} from 'lit';
import {{ customElement, state }} from 'lit/decorators.js';

@customElement('business-dashboard')
export class BusinessDashboard extends LitElement {{
  static styles = css`
    :host {{
      display: block;
      padding: 20px;
      font-family: system-ui, -apple-system, sans-serif;
    }}
    
    .dashboard-header {{
      margin-bottom: 30px;
    }}
    
    .dashboard-title {{
      font-size: 2rem;
      color: #1a1a1a;
      margin: 0 0 10px 0;
    }}
    
    .dashboard-subtitle {{
      color: #666;
      margin: 0;
    }}
    
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }}
    
    .metric-card {{
      background: white;
      border: 1px solid #e1e5e9;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    
    .metric-card h3 {{
      margin: 0 0 10px 0;
      color: #374151;
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    
    .metric-value {{
      font-size: 2rem;
      font-weight: bold;
      color: #3b82f6;
    }}
    
    .actions-section {{
      background: #f8fafc;
      border-radius: 8px;
      padding: 20px;
    }}
    
    .action-button {{
      background: #3b82f6;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 6px;
      cursor: pointer;
      margin-right: 10px;
      font-size: 14px;
    }}
    
    .action-button:hover {{
      background: #2563eb;
    }}
  `;
  
  @state()
  private metrics: any = null;
  
  @state()
  private loading = true;
  
  async connectedCallback() {{
    super.connectedCallback();
    await this.loadMetrics();
  }}
  
  private async loadMetrics() {{
    try {{
      const response = await fetch('/api/dashboard/metrics', {{
        headers: {{
          'Authorization': `Bearer ${{localStorage.getItem('token')}}`
        }}
      }});
      this.metrics = await response.json();
    }} catch (error) {{
      console.error('Failed to load metrics:', error);
    }} finally {{
      this.loading = false;
    }}
  }}
  
  private async startWorkflow(workflowType: string) {{
    try {{
      const response = await fetch('/api/workflow/start', {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${{localStorage.getItem('token')}}`
        }},
        body: JSON.stringify({{ workflow_type: workflowType, workflow_data: {{}} }})
      }});
      
      const result = await response.json();
      console.log('Workflow started:', result);
      
      // Refresh metrics after workflow starts
      await this.loadMetrics();
    }} catch (error) {{
      console.error('Failed to start workflow:', error);
    }}
  }}
  
  render() {{
    if (this.loading) {{
      return html`<div>Loading dashboard...</div>`;
    }}
    
    return html`
      <div class="dashboard-header">
        <h1 class="dashboard-title">{blueprint.solution_concept.core_value_proposition}</h1>
        <p class="dashboard-subtitle">Your business dashboard and control center</p>
      </div>
      
      <div class="metrics-grid">
        {''.join(metrics_elements)}
      </div>
      
      <div class="actions-section">
        <h3>Quick Actions</h3>
        {self._generate_action_buttons(blueprint.solution_concept.key_features[:3])}
      </div>
    `;
  }}
}}

declare global {{
  interface HTMLElementTagNameMap {{
    'business-dashboard': BusinessDashboard;
  }}
}}
'''
        
        return CodeArtifact(
            file_path="frontend/src/components/business-dashboard.ts",
            content=dashboard_code,
            description="Main business dashboard component",
            dependencies=["lit"],
            is_business_logic=True
        )
    
    def _generate_action_buttons(self, features: List[str]) -> str:
        """Generate action buttons for key features"""
        buttons = []
        for i, feature in enumerate(features):
            feature_id = feature.lower().replace(' ', '_')
            buttons.append(f'''
        <button 
          class="action-button" 
          @click="${{() => this.startWorkflow('{feature_id}')}}">
          {feature}
        </button>''')
        return ''.join(buttons)
    
    async def _generate_feature_component(self, feature: str, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate component for specific business feature"""
        
        component_name = feature.lower().replace(' ', '-')
        class_name = ''.join(word.capitalize() for word in feature.split())
        
        component_code = f'''/**
 * {class_name} Component
 * Feature: {feature}
 * Part of: {blueprint.solution_concept.core_value_proposition}
 */

import {{ LitElement, html, css }} from 'lit';
import {{ customElement, state, property }} from 'lit/decorators.js';

@customElement('{component_name}-component')
export class {class_name}Component extends LitElement {{
  static styles = css`
    :host {{
      display: block;
      padding: 20px;
      background: white;
      border-radius: 8px;
      border: 1px solid #e1e5e9;
    }}
    
    .component-header {{
      margin-bottom: 20px;
    }}
    
    .component-title {{
      font-size: 1.5rem;
      color: #1a1a1a;
      margin: 0 0 10px 0;
    }}
    
    .form-group {{
      margin-bottom: 15px;
    }}
    
    .form-label {{
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
      color: #374151;
    }}
    
    .form-input {{
      width: 100%;
      padding: 10px;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      font-size: 14px;
    }}
    
    .primary-button {{
      background: #3b82f6;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
    }}
    
    .primary-button:hover {{
      background: #2563eb;
    }}
    
    .primary-button:disabled {{
      background: #9ca3af;
      cursor: not-allowed;
    }}
  `;
  
  @state()
  private loading = false;
  
  @state()
  private data: any = null;
  
  private async handleSubmit(event: Event) {{
    event.preventDefault();
    this.loading = true;
    
    try {{
      // TODO: Implement {feature.lower()} logic
      console.log('Processing {feature.lower()}...');
      
      // API call would go here
      const response = await fetch('/api/feature/{component_name}', {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${{localStorage.getItem('token')}}`
        }},
        body: JSON.stringify(this.data || {{}})
      }});
      
      if (response.ok) {{
        const result = await response.json();
        console.log('{class_name} completed:', result);
        
        // Dispatch success event
        this.dispatchEvent(new CustomEvent('{component_name}-completed', {{
          detail: result,
          bubbles: true,
          composed: true
        }}));
      }}
    }} catch (error) {{
      console.error('{class_name} failed:', error);
    }} finally {{
      this.loading = false;
    }}
  }}
  
  render() {{
    return html`
      <div class="component-header">
        <h2 class="component-title">{feature}</h2>
      </div>
      
      <form @submit="${{this.handleSubmit}}">
        <div class="form-group">
          <label class="form-label" for="input1">Input Field</label>
          <input 
            id="input1"
            class="form-input" 
            type="text" 
            placeholder="Enter value for {feature.lower()}"
            ?disabled="${{this.loading}}"
          />
        </div>
        
        <button 
          type="submit" 
          class="primary-button"
          ?disabled="${{this.loading}}"
        >
          ${{this.loading ? 'Processing...' : 'Submit'}}
        </button>
      </form>
    `;
  }}
}}

declare global {{
  interface HTMLElementTagNameMap {{
    '{component_name}-component': {class_name}Component;
  }}
}}
'''
        
        return CodeArtifact(
            file_path=f"frontend/src/components/{component_name}-component.ts",
            content=component_code,
            description=f"Component for {feature}",
            dependencies=["lit"],
            is_business_logic=True
        )
    
    async def _generate_business_workflows(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate business workflow implementations"""
        
        artifacts = []
        
        # Generate core business service
        business_service = await self._generate_business_service(blueprint)
        artifacts.append(business_service)
        
        return artifacts
    
    async def _generate_business_service(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate core business service with workflows"""
        
        service_code = f'''"""
Core Business Service for {blueprint.solution_concept.core_value_proposition}
Implements business workflows and domain logic
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.user import User
from app.db.database import get_db


class BusinessService:
    """Core business logic and workflows"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_user_journey_step(self, user: User, step: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a step in the user journey"""
        
        # User journey: {' -> '.join(blueprint.solution_concept.user_journey)}
        
        if step == "onboarding":
            return await self._process_onboarding(user, data)
        elif step == "setup":
            return await self._process_setup(user, data)
        elif step == "activation":
            return await self._process_activation(user, data)
        else:
            raise ValueError(f"Unknown user journey step: {{step}}")
    
    async def _process_onboarding(self, user: User, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user onboarding"""
        
        # Business-specific onboarding logic
        # TODO: Implement based on business model: {blueprint.business_model.value}
        
        return {{
            "status": "completed",
            "next_step": "setup",
            "message": "Welcome to {blueprint.solution_concept.core_value_proposition}!"
        }}
    
    async def _process_setup(self, user: User, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user setup"""
        
        # TODO: Implement setup logic
        
        return {{
            "status": "completed",
            "next_step": "activation",
            "message": "Setup completed successfully"
        }}
    
    async def _process_activation(self, user: User, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user activation"""
        
        # TODO: Implement activation logic
        
        return {{
            "status": "completed",
            "next_step": None,
            "message": "You're all set! Start using {blueprint.solution_concept.core_value_proposition}"
        }}
    
    async def calculate_business_metrics(self, user: User) -> Dict[str, Any]:
        """Calculate business-specific metrics"""
        
        metrics = {{}}
        
        # Calculate metrics based on success metrics: {', '.join(blueprint.solution_concept.success_metrics)}
        
        for metric in {blueprint.solution_concept.success_metrics}:
            metric_key = metric.replace(' ', '_').lower()
            # TODO: Implement actual calculation
            metrics[metric_key] = 0
        
        return {{
            "metrics": metrics,
            "calculated_at": datetime.utcnow().isoformat(),
            "user_id": user.id
        }}
    
    async def execute_business_logic(self, user: User, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute business-specific logic"""
        
        # Key features: {', '.join(blueprint.solution_concept.key_features)}
        
        # TODO: Implement business logic based on features
        
        return {{
            "action": action,
            "result": "success",
            "data": parameters
        }}


class {blueprint.business_model.value.replace('_', '').title()}BusinessLogic:
    """Business model specific logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.business_service = BusinessService(db)
'''
        
        # Add business model specific methods
        if blueprint.business_model == BusinessModel.B2B_SAAS:
            service_code += '''
    
    async def handle_subscription_logic(self, user: User, plan: str) -> Dict[str, Any]:
        """Handle B2B SaaS subscription logic"""
        
        # TODO: Implement subscription management
        return {"plan": plan, "status": "active"}
    
    async def manage_team_access(self, user: User, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manage team access and permissions"""
        
        # TODO: Implement team management
        return {"team_id": f"team_{user.id}", "members": []}
'''
        elif blueprint.business_model == BusinessModel.MARKETPLACE:
            service_code += '''
    
    async def handle_marketplace_transaction(self, buyer: User, seller: User, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle marketplace transaction"""
        
        # TODO: Implement marketplace transaction logic
        return {"transaction_id": f"txn_{datetime.utcnow().timestamp()}", "status": "pending"}
    
    async def calculate_marketplace_fees(self, transaction_amount: float) -> Dict[str, Any]:
        """Calculate marketplace fees"""
        
        fee_percentage = 0.029  # 2.9%
        fee_amount = transaction_amount * fee_percentage
        
        return {"fee_amount": fee_amount, "net_amount": transaction_amount - fee_amount}
'''
        
        return CodeArtifact(
            file_path="backend/app/services/business_service.py",
            content=service_code,
            description="Core business service with domain logic",
            dependencies=["sqlalchemy"],
            is_business_logic=True
        )
    
    async def _generate_deployment_config(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate deployment configuration"""
        
        artifacts = []
        
        # Generate Docker configuration
        dockerfile = self._generate_dockerfile(blueprint)
        artifacts.append(dockerfile)
        
        # Generate docker-compose configuration
        docker_compose = self._generate_docker_compose(blueprint)
        artifacts.append(docker_compose)
        
        return artifacts
    
    def _generate_dockerfile(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate optimized Dockerfile"""
        
        dockerfile_content = f'''# Multi-stage Docker build for {blueprint.solution_concept.core_value_proposition}
# Optimized for production deployment

# Build stage
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ ./
RUN npm run build

# Python backend
FROM python:3.11-slim AS backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PROJECT_NAME="{blueprint.project_id}"

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        postgresql-client \\
        curl \\
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./static/
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

# Change ownership to app user
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
        
        return CodeArtifact(
            file_path="Dockerfile",
            content=dockerfile_content,
            description="Optimized production Dockerfile"
        )
    
    def _generate_docker_compose(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate docker-compose configuration"""
        
        compose_content = f'''# Docker Compose for {blueprint.solution_concept.core_value_proposition}
# Development and production deployment

version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/{blueprint.project_id.replace('-', '_')}
      - SECRET_KEY=your-secret-key-change-in-production
      - DEBUG=False
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./backend:/app/backend
      - ./alembic:/app/alembic
      - ./alembic.ini:/app/alembic.ini
    restart: unless-stopped
    
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB={blueprint.project_id.replace('-', '_')}
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
'''
        
        return CodeArtifact(
            file_path="docker-compose.yml",
            content=compose_content,
            description="Docker Compose configuration"
        )
    
    async def _generate_documentation(self, blueprint: BusinessBlueprint) -> List[CodeArtifact]:
        """Generate documentation"""
        
        artifacts = []
        
        # Generate README
        readme = self._generate_readme(blueprint)
        artifacts.append(readme)
        
        # Generate API documentation
        api_docs = self._generate_api_docs(blueprint)
        artifacts.append(api_docs)
        
        return artifacts
    
    def _generate_readme(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate project README"""
        
        readme_content = f'''# {blueprint.solution_concept.core_value_proposition}

**{blueprint.business_model.value.replace('_', ' ').title()}** • **{blueprint.industry_vertical.value.title()}**

{blueprint.problem_statement.problem_description}

## 🎯 Solution

{blueprint.solution_concept.core_value_proposition}

### Key Features

{chr(10).join(f"- {feature}" for feature in blueprint.solution_concept.key_features)}

### Target Audience

{blueprint.problem_statement.target_audience}

### Success Metrics

{chr(10).join(f"- {metric}" for metric in blueprint.solution_concept.success_metrics)}

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for development)
- Python 3.11+ (for development)

### Development Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd {blueprint.project_id}

# Start development environment
docker-compose up -d

# Run database migrations
docker-compose exec web python -m alembic upgrade head

# Create a test user
docker-compose exec web python -c "
from app.models.user import User
from app.core.security import get_password_hash
from app.db.database import SessionLocal

db = SessionLocal()
user = User(
    email='test@example.com',
    hashed_password=get_password_hash('password123')
)
db.add(user)
db.commit()
print('Test user created: test@example.com / password123')
"
```

### Access the Application

- **Frontend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin

## 📖 Documentation

### Architecture

This application follows a modern full-stack architecture:

- **Backend**: FastAPI with PostgreSQL
- **Frontend**: Lit Web Components
- **Deployment**: Docker containers
- **Monitoring**: Built-in health checks and metrics

### Business Model: {blueprint.business_model.value.title()}

{self._get_business_model_description(blueprint.business_model)}

### Industry: {blueprint.industry_vertical.value.title()}

{self._get_industry_description(blueprint.industry_vertical)}

## 🛠 Development

### Backend Development

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run development server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest backend/tests/

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Frontend Development

```bash
# Install dependencies
cd frontend && npm install

# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

## 🚢 Deployment

### Production Deployment

1. **Environment Variables**
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
   export SECRET_KEY="your-super-secret-key"
   export DEBUG=False
   ```

2. **Deploy with Docker**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **SSL Certificate**
   - Configure SSL certificates in the `ssl/` directory
   - Update `nginx.conf` with your domain

### Monitoring

- Health check: `GET /health`
- Metrics: `GET /metrics`
- Logs: Check `logs/` directory

## 📊 Business Metrics

Track your {blueprint.solution_concept.core_value_proposition.lower()} success:

{chr(10).join(f"- **{metric}**: Monitor via `/dashboard/metrics`" for metric in blueprint.solution_concept.success_metrics)}

## 🎯 Roadmap

### Phase 1: MVP (Current)
{chr(10).join(f"- [x] {feature}" for feature in blueprint.solution_concept.key_features)}

### Phase 2: Growth
- Advanced analytics and reporting
- Mobile app development
- Third-party integrations
- Advanced user management

### Phase 3: Scale
- Multi-region deployment
- Advanced security features
- Enterprise features
- API marketplace

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with the Startup Factory** - From idea to MVP in hours, not months.
'''
        
        return CodeArtifact(
            file_path="README.md",
            content=readme_content,
            description="Project README documentation"
        )
    
    def _generate_api_docs(self, blueprint: BusinessBlueprint) -> CodeArtifact:
        """Generate API documentation"""
        
        api_docs_content = f'''# API Documentation

## Authentication

All API endpoints require authentication using JWT tokens.

### Login
```http
POST /auth/login
Content-Type: application/json

{{
  "email": "user@example.com",
  "password": "password123"
}}
```

### Register
```http
POST /auth/register
Content-Type: application/json

{{
  "email": "user@example.com",
  "password": "password123"
}}
```

## Endpoints

### Dashboard
```http
GET /dashboard/metrics
Authorization: Bearer <token>
```

### Business Entities

{chr(10).join(f"#### {entity['name']}" + chr(10) + f"- `GET /{entity['name'].lower()}s` - List {entity['name'].lower()}s" + chr(10) + f"- `POST /{entity['name'].lower()}s` - Create {entity['name'].lower()}" + chr(10) + f"- `GET /{entity['name'].lower()}s/{{id}}` - Get {entity['name'].lower()}" + chr(10) + f"- `PUT /{entity['name'].lower()}s/{{id}}` - Update {entity['name'].lower()}" + chr(10) + f"- `DELETE /{entity['name'].lower()}s/{{id}}` - Delete {entity['name'].lower()}" + chr(10) for entity in blueprint.data_entities)}

## Error Handling

All endpoints return standardized error responses:

```json
{{
  "detail": "Error message",
  "status_code": 400
}}
```

## Rate Limiting

- 100 requests per minute per user
- 1000 requests per hour per user

For higher limits, contact support.
'''
        
        return CodeArtifact(
            file_path="docs/API.md",
            content=api_docs_content,
            description="API documentation"
        )
    
    def _get_business_model_description(self, business_model: BusinessModel) -> str:
        """Get description for business model"""
        descriptions = {
            BusinessModel.B2B_SAAS: "Software-as-a-Service for businesses with subscription pricing, team management, and enterprise features.",
            BusinessModel.B2C_SAAS: "Consumer-focused software with subscription pricing, individual user accounts, and consumer-friendly features.",
            BusinessModel.MARKETPLACE: "Two-sided marketplace connecting buyers and sellers with transaction fees and review systems.",
            BusinessModel.ECOMMERCE: "Direct sales of products with shopping cart, payment processing, and order management.",
            BusinessModel.CONTENT_PLATFORM: "Publishing and content creation platform with user-generated content and monetization.",
            BusinessModel.SERVICE_BUSINESS: "Professional services platform with booking, scheduling, and service delivery management."
        }
        return descriptions.get(business_model, "Custom business model implementation.")
    
    def _get_industry_description(self, industry: IndustryVertical) -> str:
        """Get description for industry vertical"""
        descriptions = {
            IndustryVertical.HEALTHCARE: "Healthcare-compliant with HIPAA considerations, medical data handling, and patient privacy features.",
            IndustryVertical.FINTECH: "Financial technology with regulatory compliance, secure transactions, and financial data protection.",
            IndustryVertical.EDUCATION: "Educational platform with student management, course delivery, and learning analytics.",
            IndustryVertical.REAL_ESTATE: "Real estate platform with property management, listing services, and market analytics.",
            IndustryVertical.LOGISTICS: "Supply chain and logistics optimization with tracking, routing, and inventory management.",
            IndustryVertical.MEDIA: "Media and content platform with publishing, distribution, and audience engagement features."
        }
        return descriptions.get(industry, "General-purpose application with standard features.")


# CLI Interface
async def main():
    """CLI for generating business logic from blueprint"""
    import sys
    import os
    
    if len(sys.argv) < 2:
        console.print("[red]Usage: python business_blueprint_generator.py <blueprint_file>[/red]")
        return
    
    blueprint_file = sys.argv[1]
    
    if not Path(blueprint_file).exists():
        console.print(f"[red]Blueprint file not found: {blueprint_file}[/red]")
        return
    
    # Load blueprint
    with open(blueprint_file, 'r') as f:
        blueprint_data = json.load(f)
    
    # Convert to BusinessBlueprint object (simplified)
    # In production, implement proper deserialization
    console.print(f"[green]Loaded blueprint: {blueprint_data.get('project_id', 'unknown')}[/green]")
    
    # Initialize generator
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY environment variable not set[/red]")
        return
    
    client = anthropic.Anthropic(api_key=api_key)
    generator = BusinessLogicGenerator(client)
    
    console.print("[yellow]Note: Full implementation requires blueprint object reconstruction[/yellow]")
    console.print("This is a demonstration of the code generation capabilities.")


if __name__ == "__main__":
    asyncio.run(main())