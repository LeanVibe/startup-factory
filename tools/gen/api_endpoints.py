"""
Generator helpers for API endpoints (extracted from BusinessLogicGenerator).
This first slice exposes pure functions used by the main generator to assemble
entity routers with consistent conventions (pagination clamp, security imports).
"""
from typing import Dict


def generate_entity_router(entity_name: str, project_name: str) -> str:
    name = entity_name
    entity_lower = name.lower()
    return f'''"""
{name} API endpoints for {project_name}
Generated CRUD operations with business logic
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.user import User
from app.models.{entity_lower} import {name}, {name}Create, {name}Response
from app.api.auth import get_current_user
from app.db.database import get_db
from app.core.rbac import require_roles
from app.core.billing import require_active_subscription, require_plan_features
from app.core.tenancy import require_tenant
from app.core.feature_flags import require_feature_flag

router = APIRouter()
security = HTTPBearer()


@router.get("/", response_model=List[{name}Response])
async def get_{entity_lower}s(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    current_tenant: int = Depends(require_tenant)
):
    """Get list of {entity_lower}s for current user"""
    query = db.query({name})
    if hasattr({name}, 'tenant_id'):
        query = query.filter({name}.tenant_id == current_tenant)
    # Pagination clamp
    limit = min(limit, 500)
    items = query.offset(skip).limit(limit).all()
    return items
'''
