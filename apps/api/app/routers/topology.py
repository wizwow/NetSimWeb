import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.auth import CurrentUser, get_current_user
from app.core.exceptions import NotFoundError
from app.schemas.topology import (
    TopologyBase,
    TopologyCreate,
    TopologyExportSchema,
    TopologyImportSchema,
    TopologyRead,
    TopologyUpdate,
)
from app.services.topology import TopologyService

router = APIRouter(prefix="/topology", tags=["Topologies"])


def get_topology_service(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TopologyService:
    return TopologyService(db, owner_id=user.id)


@router.post("/", response_model=TopologyRead, status_code=status.HTTP_201_CREATED)
async def create_topology(
    topo_in: TopologyCreate,
    svc: TopologyService = Depends(get_topology_service),
) -> dict:
    topo = await svc.create(topo_in)
    return TopologyService.to_response(topo)


@router.post("/import", response_model=TopologyRead, status_code=status.HTTP_201_CREATED)
async def import_topology(
    import_data: TopologyImportSchema,
    svc: TopologyService = Depends(get_topology_service),
) -> dict:
    topo = await svc.import_topology(import_data)
    return TopologyService.to_response(topo)


@router.get("/", response_model=List[TopologyRead])
async def list_topologies(
    svc: TopologyService = Depends(get_topology_service),
) -> list:
    topologies = await svc.list_all()
    return [TopologyService.to_response(t) for t in topologies]


@router.get("/{topology_id}", response_model=TopologyRead)
async def get_topology(
    topology_id: uuid.UUID,
    svc: TopologyService = Depends(get_topology_service),
) -> dict:
    try:
        topo = await svc.get(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return TopologyService.to_response(topo)


@router.get("/{topology_id}/export", response_model=TopologyExportSchema)
async def export_topology(
    topology_id: uuid.UUID,
    svc: TopologyService = Depends(get_topology_service),
) -> TopologyExportSchema:
    try:
        return await svc.export_topology(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)


@router.get("/{topology_id}/report.md", response_class=Response)
async def export_topology_report(
    topology_id: uuid.UUID,
    svc: TopologyService = Depends(get_topology_service),
) -> Response:
    try:
        markdown = await svc.export_report_markdown(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return Response(content=markdown, media_type="text/markdown")


@router.get("/{topology_id}/report.pdf", response_class=Response)
async def export_topology_report_pdf(
    topology_id: uuid.UUID,
    svc: TopologyService = Depends(get_topology_service),
) -> Response:
    try:
        pdf = await svc.export_report_pdf(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return Response(content=pdf, media_type="application/pdf")


@router.get("/{topology_id}/report.doc", response_class=Response)
async def export_topology_report_doc(
    topology_id: uuid.UUID,
    svc: TopologyService = Depends(get_topology_service),
) -> Response:
    try:
        doc = await svc.export_report_doc(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return Response(content=doc, media_type="application/msword")


@router.put("/{topology_id}", response_model=TopologyRead)
async def update_topology(
    topology_id: uuid.UUID,
    topo_in: TopologyUpdate,
    svc: TopologyService = Depends(get_topology_service),
) -> dict:
    try:
        topo = await svc.update(topology_id, topo_in)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
    return TopologyService.to_response(topo)


@router.delete("/{topology_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topology(
    topology_id: uuid.UUID,
    svc: TopologyService = Depends(get_topology_service),
) -> None:
    try:
        await svc.delete(topology_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.detail)
