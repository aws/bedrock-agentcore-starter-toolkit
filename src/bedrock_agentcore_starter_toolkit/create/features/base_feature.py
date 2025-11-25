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
        self.base_path: Optional[Path] = None
        self.model_provider_name: Optional[str] = None

    def _resolve_template_dir(self, context: ProjectContext) -> Path:
        """Determine which template directory to use."""
        if self.template_override_dir:
            self.template_dir = self.template_override_dir
        else:
            self.base_path = (
                Path(__file__).parent / self.feature_dir_name.lower() / "templates" / context.template_dir_selection
            )
            # Only append model provider name if it's set (SDK features have it, IaC features don't)
            # For monorepo, templates are directly in the template_dir_selection folder (no model provider subdirs)
            # For runtime_only, templates are in model provider subdirectories

            if self.model_provider_name:
                self.template_dir = self.base_path / self.model_provider_name
            else:
                self.template_dir = self.base_path
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
        self.before_apply(context)
        self._resolve_template_dir(context)
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
            rendered_content = template.render(context.dict())
            # Only write the file if it has content (skip empty files)
            if rendered_content.strip():
                dest.write_text(rendered_content)

    def _render_model_provider_templates(self, dest_dir: Path, context: ProjectContext) -> None:
        """Render model provider templates based on SDK and model provider.

        This method renders templates from:
        create/templates/model_provider/{sdk_provider}/{model_provider}/

        These templates were previously under SDK-specific runtime_only directories,
        but now apply to both runtime_only and monorepo modes.
        """
        # Construct path to model provider templates
        # e.g., create/templates/model_provider/strands/bedrock/
        model_provider_base = Path(__file__).parent.parent / "templates" / "model_provider"
        model_provider_template_dir = (
            model_provider_base / context.sdk_provider.lower() / context.model_provider.lower()
        )

        # Only render if the directory exists
        if model_provider_template_dir.exists():
            self._render_from_template_src_dir(model_provider_template_dir, dest_dir, context)

    def render_dir(self, dest_dir: Path, context: ProjectContext) -> None:
        """Render templates for the variant only (common handled automatically in apply)."""
        # Case 1: global 'common' directory
        if self.base_path:
            global_common_dir = self.base_path / TemplateDirSelection.COMMON
            if self.render_common_dir and global_common_dir.exists():
                self._render_from_template_src_dir(global_common_dir, dest_dir, context)

        # Case 2: feature-local 'common' directory within the resolved template_dir
        # e.g., strands/templates/runtime_only/common/
        local_common_dir = self.template_dir / TemplateDirSelection.COMMON
        if local_common_dir.exists():
            self._render_from_template_src_dir(local_common_dir, dest_dir, context)
        else:
            # If no common directory, render the template_dir directly
            self._render_from_template_src_dir(self.template_dir, dest_dir, context)

        # Case 3: model_provider templates (SDK-specific, model-specific)
        # Render model provider templates if both sdk_provider and model_provider are set
        # Only SDK features (not baseline features) should render model provider templates
        if (
            context.sdk_provider
            and context.model_provider
            and hasattr(self, "feature_dir_name")
            and self.feature_dir_name
        ):
            self._render_model_provider_templates(dest_dir, context)
