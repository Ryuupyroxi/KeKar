import json

import pytest

from src.agent.tools import TOOL_SCHEMAS, ToolContext, dispatch_tool
from src.data.models import Property
from src.data.property_repo import PropertyRepo


def _ctx(db):
    return ToolContext(db=db, property_repo=PropertyRepo(db.conn),
                       applicant_repo=None, memory=None, settings=None)


def test_tool_schemas_cover_spec_tools():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert {"property_list", "property_get", "property_upsert",
            "property_set_status", "applicant_list", "applicant_upsert",
            "applicant_set_stage", "listing_compile", "clipboard_copy",
            "marketplace_autofill", "memory_read", "memory_write"} <= names


async def test_property_upsert_and_list(db):
    ctx = _ctx(db)
    out = json.loads(await dispatch_tool(
        "property_upsert",
        {"address": "5 Agent Ave", "city": "Pawhuska", "rent_price": 700}, ctx))
    assert out["created"] > 0
    listed = json.loads(await dispatch_tool("property_list", {}, ctx))
    assert listed["properties"][0]["address"] == "5 Agent Ave"


async def test_property_set_status(db):
    ctx = _ctx(db)
    pid = ctx.property_repo.create(Property(address="6 Status St"))
    out = json.loads(await dispatch_tool(
        "property_set_status", {"id": pid, "status": "Rented"}, ctx))
    assert out["status"] == "Rented"


async def test_listing_compile(db):
    ctx = _ctx(db)
    pid = ctx.property_repo.create(Property(
        address="7 Copy Ct", city="Pawhuska", zip_code="74056",
        rent_price=850.0, bedrooms=3, bathrooms=2.0, sqft=1200,
        amenity_ac=True))
    out = json.loads(await dispatch_tool("listing_compile", {"id": pid}, ctx))
    assert "$850" in out["text"]


async def test_unknown_tool_raises(db):
    with pytest.raises(KeyError):
        await dispatch_tool("drop_table", {}, _ctx(db))


async def test_writes_notify_and_reads_do_not(db):
    """The sidebar must reload after a write, and must not after a read."""
    seen: list[str] = []
    ctx = ToolContext(db=db, property_repo=PropertyRepo(db.conn),
                      applicant_repo=None, memory=None, settings=None,
                      on_change=lambda: seen.append("change"))

    await dispatch_tool("property_list", {}, ctx)
    assert seen == [], "a read must not trigger a reload"

    await dispatch_tool("property_upsert",
                        {"address": "7 Notify St", "rent_price": 500}, ctx)
    assert seen == ["change"], "a write must trigger exactly one reload"

    await dispatch_tool("property_get", {"id": 1}, ctx)
    assert seen == ["change"], "reads after a write must not add notifications"
