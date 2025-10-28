from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from .features.types import BootstrapFeature

@dataclass
class ProjectContext:
    name: str
    output_dir: Path
    src_dir: Path
    features: List[BootstrapFeature]
    python_dependencies: List[str]
    iac_dir: Optional[Path] = None
    
    def dict(self):
        return asdict(self)
