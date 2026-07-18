"""Jinja2 TemplateEngine with custom template directory override."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

from githubbench_delta.reports.assets import DEFAULT_TEMPLATES
from githubbench_delta.reports.models import ReportDocument, ReportType


class TemplateEngine:
    """Render HTML/Markdown report shells from ReportDocument + assets context."""

    def __init__(self, template_dir: Path | None = None) -> None:
        loaders = []
        if template_dir is not None:
            loaders.append(FileSystemLoader(str(template_dir)))
        loaders.append(FileSystemLoader(str(DEFAULT_TEMPLATES)))
        self.env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(enabled_extensions=("html", "xml")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        doc: ReportDocument,
        *,
        fmt: str,
        asset_context: dict[str, Any] | None = None,
        print_mode: bool = False,
    ) -> str:
        """Render a report type template for html or markdown."""

        suffix = "html" if fmt in {"html", "pdf"} else "md"
        type_name = doc.report_type.value
        candidates = [
            f"types/{type_name}.{suffix}",
            f"base.{suffix}",
        ]
        template = None
        for name in candidates:
            try:
                template = self.env.get_template(name)
                break
            except Exception:
                continue
        if template is None:
            raise FileNotFoundError(f"No template found for {type_name} ({suffix})")

        ctx = {
            "doc": doc,
            "sections": doc.sections,
            "charts": doc.charts,
            "brand": doc.brand,
            "print_mode": print_mode or fmt == "pdf",
            "recommendations": doc.recommendations,
            "warnings": doc.warnings,
            **(asset_context or {}),
        }
        return template.render(**ctx)


def default_template_exists(report_type: ReportType, fmt: str) -> bool:
    suffix = "html" if fmt in {"html", "pdf"} else "md"
    path = DEFAULT_TEMPLATES / "types" / f"{report_type.value}.{suffix}"
    return path.is_file() or (DEFAULT_TEMPLATES / f"base.{suffix}").is_file()
