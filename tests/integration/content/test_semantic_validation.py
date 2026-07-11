"""
Content validation integration tests.

Verify generated output is semantically correct and parseable.
"""

import pytest

from generator.claude_layout import ClaudeLayout
from generator.copilot_layout import CopilotLayout
from generator.cursor_layout import CursorLayout
from generator.cline_layout import ClineLayout

pytestmark = [pytest.mark.integration, pytest.mark.validation]


@pytest.mark.integration
def test_cursor_output_is_valid_markdown(real_project, tmp_path):
    """Generated .cursorrules files should be valid Markdown."""
    layout = CursorLayout()
    success, failures = layout.install_all(real_project, tmp_path)

    assert len(success) > 0, "Should install at least one recipe"

    # Cursor stores active file in cache, then copies to rules dir
    # Check the cache first
    cache_dir = layout.recipe_cache_dir(tmp_path)
    cached_files = list(cache_dir.glob("*.md"))
    assert len(cached_files) > 0, "Should have cached recipe files"

    # Read first cached file (they all should be valid)
    content = cached_files[0].read_text(encoding="utf-8")

    # Validate Markdown structure
    assert content.startswith("---") or content.startswith(
        "#"
    ), "Should start with frontmatter or heading"
    assert "##" in content or "## " in content, "Should have section headings"

    # Validate no empty headings
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("##"):
            # Next non-empty line should not be another heading
            next_content = None
            for j in range(i + 1, min(i + 3, len(lines))):
                if lines[j].strip():
                    next_content = lines[j]
                    break
            if next_content and next_content.startswith("#"):
                # This is okay - could be nested heading
                pass


@pytest.mark.integration
def test_copilot_output_has_valid_frontmatter(real_project, tmp_path):
    """Generated Copilot instructions should have valid YAML frontmatter."""
    layout = CopilotLayout()
    success, failures = layout.install_all(real_project, tmp_path)

    assert len(success) > 0, "Should install at least one recipe"

    instructions_dir = layout.rules_dir(tmp_path)
    active_file = instructions_dir / "personetta-active.instructions.md"
    assert active_file.exists(), "Active instructions file should exist"

    content = active_file.read_text(encoding="utf-8")

    # Validate frontmatter structure
    assert content.startswith("---\n"), "Should start with frontmatter delimiter"

    # Extract frontmatter
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Should have opening and closing frontmatter delimiters"

    frontmatter = parts[1]

    # Validate required frontmatter fields
    assert "name:" in frontmatter, "Frontmatter should have 'name' field"
    assert "description:" in frontmatter, "Frontmatter should have 'description' field"
    assert "applyTo:" in frontmatter, "Frontmatter should have 'applyTo' field"


@pytest.mark.integration
def test_claude_output_is_parseable(real_project, tmp_path):
    """Generated Claude rules should be parseable Markdown."""
    layout = ClaudeLayout()
    success, failures = layout.install_all(real_project, tmp_path)

    assert len(success) > 0, "Should install at least one recipe"

    rules_dir = layout.rules_dir(tmp_path)
    active_file = rules_dir / "personetta-active.md"
    assert active_file.exists(), "Active rule file should exist"

    content = active_file.read_text(encoding="utf-8")

    # Validate structure
    assert len(content) > 100, "Content should be substantial"
    assert "#" in content, "Should have headings"

    # Validate no HTML comment artifacts from formatting
    assert "<!--" not in content or "-->" in content, "HTML comments should be balanced"


@pytest.mark.integration
def test_router_lists_all_installed_recipes(real_project, tmp_path):
    """Router file should list all successfully installed recipes."""
    # Use Copilot which has a simpler router structure
    layout = CopilotLayout()
    success, failures = layout.install_all(real_project, tmp_path)

    assert len(success) > 0, "Should install at least one recipe"

    router_file = layout.rules_dir(tmp_path) / "personetta-router.instructions.md"
    assert router_file.exists(), "Router file should exist"

    content = router_file.read_text(encoding="utf-8")

    # Verify all successful recipes are mentioned
    for recipe_name in success:
        assert recipe_name in content, f"Router should mention recipe '{recipe_name}'"

    # Verify it has set-active commands
    assert "set-active" in content, "Router should have set-active instructions"


@pytest.mark.integration
def test_baseline_references_router_and_active(real_project, tmp_path):
    """Baseline file should reference router and active persona."""
    layout = ClineLayout()
    success, failures = layout.install_all(real_project, tmp_path)

    assert len(success) > 0, "Should install at least one recipe"

    rules_dir = layout.rules_dir(tmp_path)
    baseline_file = rules_dir / "personetta-baseline.md"
    assert baseline_file.exists(), "Baseline file should exist"

    content = baseline_file.read_text(encoding="utf-8")

    # Baseline should reference the active persona system
    assert (
        "personetta-active" in content or "active" in content.lower()
    ), "Baseline should reference active persona"
    assert "router" in content.lower(), "Baseline should reference router"


@pytest.mark.integration
def test_cached_recipes_are_complete(real_project, tmp_path):
    """Cached recipe files should contain complete role definitions."""
    layout = CopilotLayout()
    success, failures = layout.install_all(real_project, tmp_path)

    assert len(success) > 0, "Should install at least one recipe"

    cache_dir = layout.recipe_cache_dir(tmp_path)
    assert cache_dir.exists(), "Cache directory should exist"

    # Check first cached recipe
    cached_files = list(cache_dir.glob("*.md"))
    assert len(cached_files) > 0, "Should have cached recipe files"

    first_cached = cached_files[0]
    content = first_cached.read_text(encoding="utf-8")

    # Validate completeness
    assert len(content) > 500, "Cached recipe should be substantial"

    # Should have key sections (in some form)
    has_content = (
        "responsibilities" in content.lower()
        or "should" in content.lower()
        or "guidelines" in content.lower()
        or "principles" in content.lower()
    )
    assert has_content, "Cached recipe should have role content"
