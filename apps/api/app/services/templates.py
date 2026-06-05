import json
from pathlib import Path
from typing import List

from app.core.exceptions import NotFoundError
from app.schemas.topology import TemplateSchema, TemplateSummarySchema, TopologyBase


class TemplateService:
    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or Path(__file__).resolve().parents[1] / "data" / "templates"

    def list_templates(self) -> List[TemplateSummarySchema]:
        return [
            TemplateSummarySchema(
                id=template.id,
                name=template.name,
                description=template.description,
                tags=template.tags,
                abstractionLevel=template.abstractionLevel,
            )
            for template in self._load_all()
        ]

    def instantiate(self, template_id: str) -> TopologyBase:
        template = self._load(template_id)
        return TopologyBase(
            name=template.name,
            description=template.description,
            abstractionLevel=template.abstractionLevel,
            status="draft",
            nodes=template.nodes,
            edges=template.edges,
        )

    def _load_all(self) -> List[TemplateSchema]:
        templates = [self._load_file(path) for path in sorted(self.template_dir.glob("*.json"))]
        return sorted(templates, key=lambda template: template.name)

    def _load(self, template_id: str) -> TemplateSchema:
        path = self.template_dir / f"{template_id}.json"
        if not path.exists():
            raise NotFoundError("Template", template_id)
        return self._load_file(path)

    @staticmethod
    def _load_file(path: Path) -> TemplateSchema:
        with path.open("r", encoding="utf-8") as file:
            return TemplateSchema.model_validate(json.load(file))
