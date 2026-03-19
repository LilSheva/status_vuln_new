"""Tests for matcher.core.pipeline.

Integration tests that exercise the full pipeline.
Requires sentence-transformers.
"""

from __future__ import annotations

import pytest

from shared.constants import SOURCE_AUTO_NO_MATCH, SOURCE_MANUAL, STATUS_EMPTY, STATUS_NO
from shared.types import PipelineSettings, Software, Vulnerability

try:
    from matcher.core.pipeline import Pipeline

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

pytestmark = pytest.mark.skipif(not HAS_DEPS, reason="sentence-transformers not installed")


@pytest.fixture(scope="module")
def software_list():
    return [
        Software(id="1", name="Apache HTTP Server 2.4", vendor="Apache", source="local_ppts"),
        Software(id="2", name="Nginx 1.21", vendor="Nginx", source="local_ppts"),
        Software(id="3", name="MySQL 8.0", vendor="Oracle", source="local_ppts"),
        Software(id="4", name="PostgreSQL 14", vendor="", source="local_ppts"),
        Software(id="5", name="Microsoft Windows 10 Pro", vendor="Microsoft", source="local_ppts"),
        Software(id="6", name="OpenSSH 8.9", vendor="", source="local_ppts"),
        Software(id="7", name="Oracle Java SE 17", vendor="Oracle", source="local_ppts"),
    ]


class TestPipeline:
    def test_basic_run(self, software_list):
        vulns = [
            Vulnerability("CVE-1", "Apache", "HTTP Server", "2.4", "Apache HTTP Server 2.4"),
            Vulnerability("CVE-2", "Unknown", "ZZZ_NoMatch", "", "ZZZ_NoMatch_Product_XYZ"),
        ]
        settings = PipelineSettings(top_n=5, vector_threshold=0.3)
        pipeline = Pipeline(settings)
        results = pipeline.run(vulns, software_list)

        assert len(results) == 2

        # First vuln should have candidates (Apache match)
        r1 = results[0]
        assert r1.vulnerability.cve_id == "CVE-1"
        assert len(r1.candidates) > 0 or r1.status == STATUS_NO

        # Second vuln — no real match expected
        r2 = results[1]
        assert r2.vulnerability.cve_id == "CVE-2"

    def test_no_match_gets_status_no(self, software_list):
        vulns = [
            Vulnerability("CVE-X", "", "XYZZY_NonexistentProduct_12345", "", "XYZZY_NonexistentProduct_12345"),
        ]
        settings = PipelineSettings(top_n=3, vector_threshold=0.9)
        pipeline = Pipeline(settings)
        results = pipeline.run(vulns, software_list)

        assert len(results) == 1
        assert results[0].status == STATUS_NO
        assert results[0].status_source == SOURCE_AUTO_NO_MATCH

    def test_candidates_get_empty_status(self, software_list):
        vulns = [
            Vulnerability("CVE-Y", "Apache", "HTTP Server", "2.4", "Apache HTTP Server 2.4"),
        ]
        settings = PipelineSettings(top_n=5, vector_threshold=0.3)
        pipeline = Pipeline(settings)
        results = pipeline.run(vulns, software_list)

        assert len(results) == 1
        r = results[0]
        if r.candidates:
            assert r.status == STATUS_EMPTY
            assert r.status_source == SOURCE_MANUAL
            # Candidates should be sorted by combined_score
            scores = [c.combined_score for c in r.candidates]
            assert scores == sorted(scores, reverse=True)

    def test_progress_callback(self, software_list):
        vulns = [
            Vulnerability("CVE-1", "Apache", "HTTP Server", "2.4", "Apache HTTP Server"),
        ]
        stages_seen = []

        def on_progress(stage: str, current: int, total: int) -> None:
            stages_seen.append(stage)

        pipeline = Pipeline(PipelineSettings(top_n=3, vector_threshold=0.3))
        pipeline.set_progress_callback(on_progress)
        pipeline.run(vulns, software_list)

        assert len(stages_seen) > 0
        assert "Построение векторного индекса" in stages_seen

    def test_empty_inputs(self, software_list):
        pipeline = Pipeline()
        results = pipeline.run([], software_list)
        assert results == []
