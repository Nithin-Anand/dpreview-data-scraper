"""YAML output writer."""

from pathlib import Path
from typing import Any, Dict
import yaml

from dpreview_scraper.models.camera import Camera
from dpreview_scraper.utils.logging import logger


class YAMLWriter:
    """Write camera data to YAML files."""

    def __init__(self, output_dir: Path):
        """Initialize YAML writer.

        Args:
            output_dir: Directory to write YAML files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_camera(self, camera: Camera) -> Path:
        """Write camera data to YAML file.

        Args:
            camera: Camera object to write

        Returns:
            Path to written file
        """
        filename = f"{camera.ProductCode}.yaml"
        filepath = self.output_dir / filename

        # Convert to dict with proper ordering
        data = camera.to_yaml_dict()

        # Write YAML with custom formatting
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=1000,  # Prevent line wrapping
                indent=4,
            )

        logger.info(f"Wrote YAML file: {filepath}")
        return filepath

    def camera_exists(self, product_code: str) -> bool:
        """Check if camera YAML file already exists.

        Args:
            product_code: Product code to check

        Returns:
            True if file exists
        """
        filepath = self.output_dir / f"{product_code}.yaml"
        return filepath.exists()


# Custom YAML representer for better formatting
def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.Node:
    """Custom string representer for multiline strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Register custom representer
yaml.add_representer(str, _str_representer)
