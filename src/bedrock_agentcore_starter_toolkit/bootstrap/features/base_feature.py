from __future__ import annotations
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from ..types import ProjectContext


class Feature(ABC):
    """Base feature class for applying Jinja2-based templates to a target directory."""

    name: str  # subclasses must override
    python_dependencies: list[str] = []
    template_override_dir: Optional[Path] = None

    def __init__(self) -> None:
        if not getattr(self, "name", None):
            raise ValueError(f"{self.__class__.__name__} must define a 'name' attribute")

        self.template_dir = self.template_override_dir or Path(__file__).parent / self.name.lower() / "templates"

        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        self.env = Environment(loader=FileSystemLoader(self.template_dir))


    def before_apply(self, context: ProjectContext) -> None:
        """Hook for implementing additional logic before templates are applied"""
        pass

    def after_apply(self, context: ProjectContext) -> None:
        """Hook for implementing any additional logic after templates are applied."""
        pass

    def apply(self, context: ProjectContext) -> None:
        """Render all Jinja2 templates in the feature’s directory into the target directory."""
        self.before_apply(context)
        self.execute(context)
        self.after_apply(context)

    @abstractmethod
    def execute(self, context: ProjectContext) -> None:
        pass

    def render_dir(self, dest_dir: Path, context: ProjectContext) -> None:
        """Render all .j2 templates under self.template_dir into dest_dir, preserving structure."""
        for src in self.template_dir.rglob("*.j2"):
            rel = src.relative_to(self.template_dir)
            dest = dest_dir / rel.with_suffix("") # remove .j2 from output filename
            dest.parent.mkdir(parents=True, exist_ok=True)

            template_rel = src.relative_to(self.template_dir).as_posix()
            template = self.env.get_template(template_rel)
            dest.write_text(template.render(context.dict()))
