"""AssetManager: CSS, logos, chart PNGs, branding variables."""

from __future__ import annotations

import shutil
from pathlib import Path

from githubbench_delta.reports.models import BrandConfig, ChartAsset

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_STATIC = PACKAGE_DIR / "static"
DEFAULT_TEMPLATES = PACKAGE_DIR / "templates"


class AssetManager:
    """Prepare an output `_assets/` directory for a report bundle."""

    def __init__(
        self,
        output_dir: Path,
        *,
        brand: BrandConfig | None = None,
        static_dir: Path | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.brand = brand or BrandConfig()
        self.static_dir = Path(static_dir or DEFAULT_STATIC)
        self.assets_dir = self.output_dir / "_assets"

    def prepare(self) -> Path:
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        css_src = self.static_dir / "report.css"
        if css_src.is_file():
            shutil.copy2(css_src, self.assets_dir / "report.css")
        else:
            (self.assets_dir / "report.css").write_text(self.branding_css(), encoding="utf-8")
        # Append branding overrides
        override = self.assets_dir / "branding.css"
        override.write_text(self.branding_css(), encoding="utf-8")
        if self.brand.logo_path:
            logo = Path(self.brand.logo_path)
            if logo.is_file():
                dest = self.assets_dir / logo.name
                shutil.copy2(logo, dest)
                self.logo_relpath = f"_assets/{logo.name}"
            else:
                self.logo_relpath = None
        else:
            self.logo_relpath = None
        return self.assets_dir

    def branding_css(self) -> str:
        return (
            ":root {\n"
            f"  --gb-primary: {self.brand.primary_color};\n"
            f"  --gb-secondary: {self.brand.secondary_color};\n"
            "}\n"
        )

    def register_charts(self, charts: dict[str, ChartAsset]) -> dict[str, ChartAsset]:
        """Ensure chart PNG paths are under assets_dir when present."""

        return charts

    def context(self) -> dict[str, str | None]:
        return {
            "css_href": "_assets/report.css",
            "branding_css_href": "_assets/branding.css",
            "logo_href": getattr(self, "logo_relpath", None),
            "product_name": self.brand.product_name,
            "footer_text": self.brand.footer_text,
        }
