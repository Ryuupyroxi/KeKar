"""Thin async wrapper over Playwright's CDP connection.

Uses the user's existing browser (no bundled Chromium). Playwright is imported
lazily so the app starts fast and the GUI works even if Playwright is missing.
"""
from __future__ import annotations

import asyncio
from pathlib import Path


class CDPUnavailable(Exception):
    pass


class CDPClient:
    def __init__(self, port: int = 9222):
        self.port = port
        self._pw = None
        self._browser = None
        self._page = None

    def connect(self, timeout: float = 5.0) -> bool:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise CDPUnavailable("Playwright is not installed") from exc
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.connect_over_cdp(
                f"http://127.0.0.1:{self.port}")
            context = self._browser.contexts[0] if self._browser.contexts \
                else self._browser.new_context()
            self._page = context.pages[0] if context.pages else context.new_page()
            return True
        except Exception as exc:
            self.close()
            raise CDPUnavailable(
                f"Could not attach to the browser on port {self.port}. "
                "Make sure Chrome was started by KeKar.") from exc

    async def navigate(self, url: str) -> bool:
        await asyncio.to_thread(self._page.goto, url, wait_until="domcontentloaded")
        return True

    async def fill(self, selector: str, value: str) -> bool:
        el = await asyncio.to_thread(self._page.query_selector, selector)
        if el is None:
            return False
        await asyncio.to_thread(el.fill, value)
        return True

    async def click(self, selector: str) -> bool:
        el = await asyncio.to_thread(self._page.query_selector, selector)
        if el is None:
            return False
        await asyncio.to_thread(el.click)
        return True

    async def upload_files(self, selector: str, files: list[Path]) -> bool:
        el = await asyncio.to_thread(self._page.query_selector, selector)
        if el is None:
            return False
        await asyncio.to_thread(el.set_input_files, [str(f) for f in files])
        return True

    async def page_text(self, selector: str) -> str:
        el = await asyncio.to_thread(self._page.query_selector, selector)
        if el is None:
            return ""
        return await asyncio.to_thread(el.inner_text)

    def close(self) -> None:
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._browser = self._pw = self._page = None
