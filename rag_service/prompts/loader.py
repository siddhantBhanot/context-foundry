import os
from pathlib import Path
from typing import Any, Dict


class PromptLoader:
    """
    Centralized, version-controlled prompt manager.
    Loads and caches Markdown prompt templates with parameter interpolation.
    """

    def __init__(self, prompts_dir: Path | str | None = None) -> None:
        if prompts_dir is None:
            current_dir = Path(__file__).resolve().parent
            parent_prompts = current_dir.parent / "prompts"
            if (current_dir / "system.md").exists():
                self.prompts_dir = current_dir
            elif parent_prompts.is_dir():
                self.prompts_dir = parent_prompts
            else:
                self.prompts_dir = current_dir
        else:
            self.prompts_dir = Path(prompts_dir)

        self._cache: Dict[str, str] = {}

    def get_template(self, prompt_name: str) -> str:
        """
        Load a prompt template by filename (with or without .md extension).
        """
        filename = prompt_name if prompt_name.endswith(".md") else f"{prompt_name}.md"
        if filename in self._cache:
            return self._cache[filename]

        file_path = self.prompts_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {file_path}")

        template = file_path.read_text(encoding="utf-8")
        self._cache[filename] = template
        return template

    def render(self, prompt_name: str, **kwargs: Any) -> str:
        """
        Render a template by replacing `{{key}}` placeholders with corresponding values.
        """
        template = self.get_template(prompt_name)
        rendered = template
        for key, value in kwargs.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        return rendered

    def clear_cache(self) -> None:
        """Clear cached prompt templates."""
        self._cache.clear()


_default_loader: PromptLoader | None = None


def get_prompt_loader(prompts_dir: Path | str | None = None) -> PromptLoader:
    """Singleton getter for PromptLoader."""
    global _default_loader
    if _default_loader is None or prompts_dir is not None:
        _default_loader = PromptLoader(prompts_dir)
    return _default_loader
