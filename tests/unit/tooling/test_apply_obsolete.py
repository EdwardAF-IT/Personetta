from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tooling.apply_obsolete import merge_proposed_obsolete
from tooling.models import Evidence, ProposedObsolete


@pytest.mark.audit_tooling
def test_merge_proposed_obsolete_appends_and_dedupes(tmp_path: Path) -> None:
    path = tmp_path / "obsolete.yaml"
    path.write_text("entries:\n  - name: Existing\n    reason: old\n", encoding="utf-8")
    proposed = [
        ProposedObsolete(
            name="existing",
            reason="dup",
            superseded_by=None,
            evidence=[Evidence("s", "f", "v", "t")],
        ),
        ProposedObsolete(
            name="NewTool",
            reason="PyPI yanked",
            superseded_by=None,
            evidence=[],
        ),
    ]
    out = merge_proposed_obsolete(path, proposed)
    path.write_text(out, encoding="utf-8")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    names = [e["name"] for e in data["entries"]]
    assert names == ["Existing", "NewTool"]
