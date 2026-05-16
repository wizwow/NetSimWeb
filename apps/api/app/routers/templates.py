from fastapi import APIRouter, Depends, HTTPException

from app.core.exceptions import NotFoundError
from app.schemas.topology import TemplateSummarySchema, TopologyBase
from app.services.templates import TemplateService

router = APIRouter(prefix="/templates", tags=["Templates"])


def get_template_service() -> TemplateService:
    return TemplateService()


@router.get("/", response_model=list[TemplateSummarySchema])
async def list_templates(
    svc: TemplateService = Depends(get_template_service),
) -> list[TemplateSummarySchema]:
    return svc.list_templates()


@router.post("/{template_id}/instantiate", response_model=TopologyBase)
async def instantiate_template(
    template_id: str,
    svc: TemplateService = Depends(get_template_service),
) -> TopologyBase:
    try:
        return svc.instantiate(template_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
