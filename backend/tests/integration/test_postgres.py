"""Optional: needs a migrated PostgreSQL. Run with:  TEST_DATABASE_URL=... pytest -m integration"""
import os

import pytest

from tests.conftest import run_and_get, submit

pytestmark = pytest.mark.integration
URL = os.environ.get("TEST_DATABASE_URL")


@pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")
def test_full_flow_on_postgres(make_client, settings):
    settings.database_url = URL
    c = make_client()
    aid, res = run_and_get(c, submit(c))
    assert res.json()["analysis"]["status"] == "completed"
    assert c.delete(f"/api/v1/analyses/{aid}").status_code == 204
