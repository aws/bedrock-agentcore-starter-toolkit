"""Defines a Base feature class for applying Jinja2-based templates to a target directory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from ..constants import TemplateDirSelection
from ..types import ProjectContext


class Feature(ABC):
    """Base feature class for applying Jinja2-based templates to a target directory."""

    feature_dir_name: Optional[str]
    python_dependencies: list[str] = []
    template_override_dir: Optional[Path] = None
    render_common_dir: bool = False

    def __init__(self) -> None:
        """Initialize the base feature."""
        if not (self.template_override_dir or self.feature_dir_name):
            raise Exception("Without template_override_parent_dir, feature_dir_name must be defined")
        self.template_dir: Optional[Path] = None

    def _resolve_template_dir(self, context: ProjectContext) -> Path:
        """Determine which template directory to use."""
        self.template_dir = self.template_override_dir or (
            Path(__file__).parent / self.feature_dir_name.lower() / "templates" / context.template_dir_selection
        )
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

    @abstractmethod
    def before_apply(self, context: ProjectContext) -> None:
        """This method is called before code is generated."""
        pass

    @abstractmethod
    def after_apply(self, context: ProjectContext) -> None:
        """This method is called after code is generated."""
        pass

    def apply(self, context: ProjectContext) -> None:
        """Prepare and apply the feature, automatically rendering common templates if enabled."""
        self._resolve_template_dir(context)
        self.before_apply(context)
        self.execute(context)
        self.after_apply(context)

    @abstractmethod
    def execute(self, context: ProjectContext) -> None:
        """Executes code generation and directory creation."""
        pass

    # --- core rendering helper ---
    def _render_from_template_src_dir(self, template_src_dir: Path, dest_dir: Path, context: ProjectContext) -> None:
        """Render all templates under a given source directory into dest_dir."""
        env = Environment(loader=FileSystemLoader(template_src_dir), autoescape=True)
        for src in template_src_dir.rglob("*.j2"):
            rel = src.relative_to(template_src_dir)
            dest = dest_dir / rel.with_suffix("")  # remove .j2 suffix
            dest.parent.mkdir(parents=True, exist_ok=True)
            template = env.get_template(rel.as_posix())
            dest.write_text(template.render(context.dict()))

    def render_dir(self, dest_dir: Path, context: ProjectContext) -> None:
        """Render templates for the variant only (common handled automatically in apply)."""
        common_dir = self.template_dir.parent / TemplateDirSelection.COMMON
        if self.render_common_dir and common_dir.exists():
            self._render_from_template_src_dir(common_dir, dest_dir, context)
        self._render_from_template_src_dir(self.template_dir, dest_dir, context)
