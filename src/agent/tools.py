"""The agent's tool surface.

Implements the four toolsets from spec §11.3 as native functions exposed to the
model via function calling. The model can only call these — never raw SQL.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..data.models import Applicant, Property
from ..services.listing_compiler import compile_listing


@dataclass
class ToolContext:
    db: Any
    property_repo: Any
    applicant_repo: Any
    memory: Any
    settings: Any
    browser: Any = None
    #: Called after any tool that changes stored data, so the UI can reload.
    #: Emitted from a worker thread; Qt queues it to the GUI thread.
    on_change: Any = None


# Tools that write. A read-only answer must not make the sidebar reload.
MUTATING_TOOLS = frozenset({
    "property_upsert",
    "property_set_status",
    "applicant_upsert",
    "applicant_set_stage",
    "memory_write",
})


TOOL_SCHEMAS: list[dict] = [
    {"type": "function", "function": {
        "name": "property_list",
        "description": "List rental properties, optionally filtered by status.",
        "parameters": {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["Vacant", "Rented"]}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "property_get",
        "description": "Get full details for one property by id.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "property_upsert",
        "description": "Create a property, or update it when 'id' is provided. "
                       "Only include fields that should change.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"},
            "address": {"type": "string"}, "city": {"type": "string"},
            "zip_code": {"type": "string"}, "rent_price": {"type": "number"},
            "deposit_amount": {"type": "number"},
            "available_date": {"type": "string"},
            "bedrooms": {"type": "integer"}, "bathrooms": {"type": "number"},
            "sqft": {"type": "integer"}, "pet_policy": {"type": "string"},
            "status": {"type": "string", "enum": ["Vacant", "Rented"]},
            "amenity_wd": {"type": "boolean"}, "amenity_ac": {"type": "boolean"},
            "amenity_yard": {"type": "boolean"},
            "amenity_dishwasher": {"type": "boolean"},
            "amenity_parking": {"type": "boolean"},
            "notes": {"type": "string"}}, "required": ["address"]}}},
    {"type": "function", "function": {
        "name": "property_set_status",
        "description": "Mark a property Vacant or Rented.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"},
            "status": {"type": "string", "enum": ["Vacant", "Rented"]}},
            "required": ["id", "status"]}}},
    {"type": "function", "function": {
        "name": "applicant_list",
        "description": "List prospective tenants, optionally by property and stage.",
        "parameters": {"type": "object", "properties": {
            "property_id": {"type": "integer"},
            "stage": {"type": "string", "enum": [
                "Inquiry Received", "Questionnaire Sent",
                "Background Check", "Approved", "Rejected"]}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "applicant_upsert",
        "description": "Create or update an applicant record.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"}, "property_id": {"type": "integer"},
            "applicant_name": {"type": "string"},
            "contact_info": {"type": "string"},
            "screening_stage": {"type": "string", "enum": [
                "Inquiry Received", "Questionnaire Sent",
                "Background Check", "Approved", "Rejected"]},
            "notes": {"type": "string"}}, "required": ["applicant_name"]}}},
    {"type": "function", "function": {
        "name": "applicant_set_stage",
        "description": "Move an applicant to a new screening stage.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"}, "stage": {"type": "string", "enum": [
                "Inquiry Received", "Questionnaire Sent",
                "Background Check", "Approved", "Rejected"]}},
            "required": ["id", "stage"]}}},
    {"type": "function", "function": {
        "name": "listing_compile",
        "description": "Generate Facebook Marketplace listing copy for a property.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "clipboard_copy",
        "description": "Copy text to the system clipboard so it can be pasted.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {
        "name": "marketplace_autofill",
        "description": "Open Facebook Marketplace and fill in a listing for a "
                       "property. ALWAYS pauses for the user to review and click "
                       "Publish. Requires the user to enable auto-fill in Settings.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "memory_read",
        "description": "Read the assistant's saved operational notes.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "memory_write",
        "description": "Replace the assistant's saved operational notes.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"}}, "required": ["text"]}}},
]


def _property_dict(p: Property) -> dict:
    return {
        "id": p.id, "address": p.address, "city": p.city, "zip_code": p.zip_code,
        "rent_price": p.rent_price, "deposit_amount": p.deposit_amount,
        "available_date": p.available_date, "bedrooms": p.bedrooms,
        "bathrooms": p.bathrooms, "sqft": p.sqft, "pet_policy": p.pet_policy,
        "status": p.status,
        "amenities": [label for attr, label in [
            ("amenity_wd", "Washer & dryer in unit"),
            ("amenity_ac", "Central AC & heat"),
            ("amenity_yard", "Fenced yard"),
            ("amenity_dishwasher", "Dishwasher"),
            ("amenity_parking", "Parking spot")] if getattr(p, attr)],
        "notes": p.notes,
    }


async def dispatch_tool(name: str, arguments: dict, ctx: ToolContext) -> str:
    registry = build_registry(ctx)
    if name not in registry:
        raise KeyError(f"unknown tool: {name}")
    result = await registry[name](**(arguments or {}))
    if name in MUTATING_TOOLS and ctx.on_change is not None:
        ctx.on_change()
    return result if isinstance(result, str) else json.dumps(result)


def build_registry(ctx: ToolContext) -> dict:
    async def property_list(status: str | None = None) -> dict:
        return {"properties": [_property_dict(p)
                              for p in ctx.property_repo.list(status=status)]}

    async def property_get(id: int) -> dict:
        p = ctx.property_repo.get(id)
        if p is None:
            return {"error": f"no property with id {id}"}
        return _property_dict(p)

    async def property_upsert(**fields) -> dict:
        pid = fields.pop("id", None)
        if pid:
            existing = ctx.property_repo.get(pid)
            if existing is None:
                return {"error": f"no property with id {pid}"}
            for key, value in fields.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            ctx.property_repo.update(existing)
            return {"updated": pid, "property": _property_dict(existing)}
        prop = Property(**fields)
        new_id = ctx.property_repo.create(prop)
        return {"created": new_id,
                "property": _property_dict(ctx.property_repo.get(new_id))}

    async def property_set_status(id: int, status: str) -> dict:
        ctx.property_repo.set_status(id, status)
        return {"id": id, "status": status}

    async def applicant_list(property_id: int | None = None,
                             stage: str | None = None) -> dict:
        if ctx.applicant_repo is None:
            return {"error": "applicant repository unavailable"}
        rows = ctx.applicant_repo.list(property_id=property_id, stage=stage)
        return {"applicants": [
            {"id": a.id, "name": a.applicant_name, "property_id": a.property_id,
             "contact": a.contact_info, "stage": a.screening_stage,
             "notes": a.notes} for a in rows]}

    async def applicant_upsert(**fields) -> dict:
        aid = fields.pop("id", None)
        if aid:
            existing = ctx.applicant_repo.get(aid)
            if existing is None:
                return {"error": f"no applicant with id {aid}"}
            for key, value in fields.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            ctx.applicant_repo.update(existing)
            return {"updated": aid}
        new_id = ctx.applicant_repo.create(Applicant(**fields))
        return {"created": new_id}

    async def applicant_set_stage(id: int, stage: str) -> dict:
        ctx.applicant_repo.set_stage(id, stage)
        return {"id": id, "stage": stage}

    async def listing_compile(id: int) -> dict:
        p = ctx.property_repo.get(id)
        if p is None:
            return {"error": f"no property with id {id}"}
        return {"id": id, "text": compile_listing(p)}

    async def clipboard_copy(text: str) -> dict:
        from ..services.clipboard import copy_text
        copy_text(text)
        return {"copied": True, "length": len(text)}

    async def marketplace_autofill(id: int) -> dict:
        if ctx.settings is not None and not ctx.settings.autofill_enabled:
            return {"error": "Auto-fill is disabled. Ask the user to enable it in "
                              "Settings, or offer to copy the listing text instead."}
        if ctx.browser is None:
            return {"error": "Browser automation is not available."}
        p = ctx.property_repo.get(id)
        if p is None:
            return {"error": f"no property with id {id}"}
        return await ctx.browser.autofill_listing(p)

    async def memory_read() -> dict:
        if ctx.memory is None:
            return {"text": ""}
        return {"text": ctx.memory.read()}

    async def memory_write(text: str) -> dict:
        if ctx.memory is None:
            return {"error": "memory unavailable"}
        ctx.memory.write(text)
        return {"written": True}

    return {
        "property_list": property_list,
        "property_get": property_get,
        "property_upsert": property_upsert,
        "property_set_status": property_set_status,
        "applicant_list": applicant_list,
        "applicant_upsert": applicant_upsert,
        "applicant_set_stage": applicant_set_stage,
        "listing_compile": listing_compile,
        "clipboard_copy": clipboard_copy,
        "marketplace_autofill": marketplace_autofill,
        "memory_read": memory_read,
        "memory_write": memory_write,
    }
