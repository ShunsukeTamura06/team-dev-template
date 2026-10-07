from __future__ import annotations

from collections.abc import Iterator

import gitlab_admin
import pytest
from fake_gitlab import FakeGitLab, serve


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeGitLab]:
    fake = FakeGitLab()
    fake.add_project("grp/tool-a")
    url, shutdown = serve(fake)
    monkeypatch.setenv("GITLAB_URL", url)
    monkeypatch.setenv("GITLAB_TOKEN", "test-token")
    yield fake
    shutdown()


def test_protectでmain保護とパイプライン必須が設定される(fake: FakeGitLab) -> None:
    assert gitlab_admin.main(["protect", "grp/tool-a"]) == 0
    project = fake.projects["grp/tool-a"]
    assert project["protected"] == {
        "name": "main",
        "push_access_level": 0,
        "merge_access_level": 30,
        "allow_force_push": False,
    }
    assert project["pipeline_required"] is True


def test_既存の保護設定があっても付け直す(fake: FakeGitLab) -> None:
    fake.projects["grp/tool-a"]["protected"] = {"name": "main", "push_access_level": 40}
    assert gitlab_admin.main(["protect", "grp/tool-a"]) == 0
    assert fake.projects["grp/tool-a"]["protected"]["push_access_level"] == 0


def test_dry_runでは通信しない(fake: FakeGitLab) -> None:
    assert gitlab_admin.main(["protect", "grp/tool-a", "--dry-run"]) == 0
    assert fake.calls == []


def test_失敗したプロジェクトを報告し他は続ける(
    fake: FakeGitLab, capsys: pytest.CaptureFixture[str]
) -> None:
    assert gitlab_admin.main(["protect", "grp/unknown", "grp/tool-a"]) == 1
    assert "[NG] grp/unknown" in capsys.readouterr().err
    assert fake.projects["grp/tool-a"]["pipeline_required"] is True


def test_環境変数が無ければ止まる(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITLAB_URL", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    assert gitlab_admin.main(["protect", "grp/tool-a"]) == 1


def test_中央リポジトリはMaintainerだけがマージできる(fake: FakeGitLab) -> None:
    assert gitlab_admin.main(["protect", "grp/tool-a", "--merge-level", "maintainer"]) == 0
    assert fake.projects["grp/tool-a"]["protected"]["merge_access_level"] == 40
