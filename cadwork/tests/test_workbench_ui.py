"""Workbench behaviour in a real browser, driven through Playwright.

The viewport is the only place where document state, the WASM kernel and the three.js
scene meet; a component test over HTTP cannot see whether the camera moved, whether a
click resolved to a real B-Rep face, or whether the canvas stayed blank. These cases
launch headless Chromium against a service started in-process on a temporary store.

Playwright and a Chromium binary are optional tooling: without them the module reports
skipped cases instead of failing the suite. Install with `pip install -r
requirements-ui.txt`; the browser is either the Playwright bundle (`playwright install
chromium`) or a system binary named by `BREPX_CHROMIUM`.
"""

from __future__ import annotations

import io
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any

import uvicorn
from PIL import Image, ImageChops, ImageStat

from cadwork.service import create_app

PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "plugins" / "cadview"
WORKBENCH_BUNDLE = PLUGIN_ROOT / "lib" / "workbench.mjs"
PACKAGE_ROOT = PLUGIN_ROOT / "node_modules"

VIEWPORT = {"width": 1400, "height": 900}
STARTUP_TIMEOUT = 45.0

# Headless Chromium on a machine without a GPU falls back to a broken GL path and the
# canvas stays black; ANGLE's SwiftShader backend is slow but produces the same pixels
# a desktop driver would. The flags are only added when there is no DRI device, so a
# developer with a real GPU keeps hardware rendering.
SOFTWARE_GL_ARGS = [
    "--enable-unsafe-swiftshader",
    "--use-gl=angle",
    "--use-angle=swiftshader",
]
BASE_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]


def _chromium_executable() -> str | None:
    override = os.environ.get("BREPX_CHROMIUM")
    if override:
        return override if Path(override).exists() else None
    for candidate in (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def _missing_prerequisites() -> str | None:
    if not WORKBENCH_BUNDLE.is_file() or not PACKAGE_ROOT.is_dir():
        return "viewport bundle is not built (npm install && npm run build in plugins/cadview)"
    try:
        import playwright  # noqa: F401
    except ImportError:
        return "playwright is not installed (pip install -r requirements-ui.txt)"
    if _chromium_executable() is None:
        return "no chromium binary (playwright install chromium, or set BREPX_CHROMIUM)"
    return None


SKIP_REASON = _missing_prerequisites()


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class _Service:
    """A live HTTP service on an ephemeral port backed by a throwaway store."""

    def __init__(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        config = uvicorn.Config(
            create_app(self.folder.name),
            host="127.0.0.1",
            port=self.port,
            log_level="error",
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> None:
        self.thread.start()
        deadline = time.monotonic() + STARTUP_TIMEOUT
        while not self.server.started:
            if time.monotonic() > deadline or not self.thread.is_alive():
                raise RuntimeError("cadwork service did not start")
            time.sleep(0.05)

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)
        self.folder.cleanup()


def _brightness_spread(png: bytes) -> float:
    image = Image.open(io.BytesIO(png)).convert("RGB")
    return sum(ImageStat.Stat(image).stddev) / 3.0


def _mean_difference(left: bytes, right: bytes) -> float:
    first = Image.open(io.BytesIO(left)).convert("RGB")
    second = Image.open(io.BytesIO(right)).convert("RGB")
    if first.size != second.size:
        second = second.resize(first.size)
    diff = ImageChops.difference(first, second)
    return ImageStat.Stat(diff).mean[0]


def _skip(cls: type) -> type:
    return unittest.skipUnless(SKIP_REASON is None, SKIP_REASON or "")(cls)


@_skip
class WorkbenchBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from playwright.sync_api import sync_playwright

        cls.service = _Service()
        cls.service.start()
        cls.addClassCleanup(cls.service.stop)

        args = list(BASE_ARGS)
        if not Path("/dev/dri").exists():
            args += SOFTWARE_GL_ARGS
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(
            executable_path=_chromium_executable(), headless=True, args=args
        )
        cls.addClassCleanup(cls.browser.close)
        cls.context = cls.browser.new_context(viewport=VIEWPORT, accept_downloads=True)
        cls.addClassCleanup(cls.context.close)

    def setUp(self) -> None:
        self.created: list[str] = []
        self.addCleanup(self._delete_documents)

    def _delete_documents(self) -> None:
        for document_id in self.created:
            self.context.request.delete(f"{self.service.base}/api/docs/{document_id}")

    def _document(self, name: str, sample: str | None = None) -> str:
        response = self.context.request.post(
            f"{self.service.base}/api/docs", data={"name": name}
        )
        self.assertEqual(response.status, 200, response.text())
        document_id = response.json()["id"]
        self.created.append(document_id)
        if sample:
            loaded = self.context.request.post(
                f"{self.service.base}/api/docs/{document_id}/sample/{sample}", data={}
            )
            self.assertEqual(loaded.status, 200, loaded.text())
        return document_id

    def _open(self, document_id: str):
        page = self.context.new_page()
        self.addCleanup(page.close)
        page.goto(f"{self.service.base}/workbench?document={document_id}")
        page.locator(".bxw-shell").wait_for(state="visible")
        page.wait_for_function(
            "() => { const b = document.querySelector('.bxw-badge');"
            " return b && /\\d+\\/\\d+/.test(b.textContent); }",
            timeout=STARTUP_TIMEOUT * 1000,
        )
        page.frame_locator("iframe[src*='kernel-view']").locator("canvas").wait_for(
            state="visible"
        )
        return page

    def _canvas(self, page):
        return page.frame_locator("iframe[src*='kernel-view']").locator("canvas")

    def _canvas_png(self, page, previous: bytes | None = None) -> bytes:
        """Screenshot the viewport once it shows a drawn frame.

        The scene is drawn from an animation frame and SwiftShader is slow, so a fixed
        delay is not enough under load. With ``previous`` the frame must have changed;
        without it the frame must not be a uniform background.
        """
        deadline = time.monotonic() + STARTUP_TIMEOUT
        png = self._canvas(page).screenshot()
        while time.monotonic() < deadline:
            if previous is None:
                if _brightness_spread(png) > 4.0:
                    return png
            elif _mean_difference(previous, png) > 1.0:
                return png
            page.wait_for_timeout(250)
            png = self._canvas(page).screenshot()
        return png

    def test_viewport_draws_kernel_geometry(self) -> None:
        document_id = self._document("impeller", "impeller")
        page = self._open(document_id)

        canvas = self._canvas(page)
        box = canvas.bounding_box()
        self.assertIsNotNone(box)
        self.assertGreater(box["width"], 400)
        self.assertGreater(box["height"], 300)

        version = canvas.evaluate(
            "e => { const g = e.getContext('webgl2') || e.getContext('webgl');"
            " return g ? g.getParameter(g.VERSION) : null; }"
        )
        self.assertIsNotNone(version, "viewport canvas exposes no WebGL context")

        png = self._canvas_png(page)
        # A failed scene is a uniform background; geometry spreads colour over the frame.
        self.assertGreater(_brightness_spread(png), 4.0, "viewport is blank")
        self.assertIn("检查 55/55", page.locator(".bxw-badge").first.inner_text())

    def test_view_switch_moves_the_camera(self) -> None:
        document_id = self._document("impeller", "impeller")
        page = self._open(document_id)

        isometric = self._canvas_png(page)
        page.get_by_role("button", name="顶视图").click()
        plan = self._canvas_png(page, previous=isometric)
        self.assertGreater(
            _mean_difference(isometric, plan),
            3.0,
            "switching to the plan view did not redraw the viewport",
        )

    def test_clicking_a_face_reports_its_area(self) -> None:
        document_id = self._document("flange", "flange")
        page = self._open(document_id)

        # The flange plate dominates the centre of the isometric frame. Hit testing is
        # a round trip to the kernel, so the row reports a pending state first.
        canvas = self._canvas(page)
        box = canvas.bounding_box()
        self.assertIsNotNone(box)
        canvas.click(position={"x": box["width"] * 0.5, "y": box["height"] * 0.45})
        page.wait_for_function(
            "() => { const i = document.querySelector('.bxw-inspector');"
            " return i && /mm²/.test(i.innerText) && !/正在解析/.test(i.innerText); }",
            timeout=STARTUP_TIMEOUT * 1000,
        )
        text = page.locator(".bxw-inspector").inner_text()
        self.assertIn("选中", text)
        self.assertRegex(text, r"面 \d+")

    def test_checks_command_lists_passing_checks(self) -> None:
        document_id = self._document("impeller", "impeller")
        page = self._open(document_id)

        command = page.get_by_label("命令或设计意图")
        command.fill("/checks")
        command.press("Enter")
        page.get_by_text("55/55 通过").wait_for(timeout=STARTUP_TIMEOUT * 1000)
        inspector = page.locator(".bxw-inspector").inner_text()
        self.assertIn("hub · watertight", inspector)
        self.assertIn("closed mesh, no free edges", inspector)

    def test_theme_toggle_swaps_tokens(self) -> None:
        document_id = self._document("flange", "flange")
        page = self._open(document_id)

        shell = page.locator(".bxw-shell")
        header = page.locator(".bxw-header")
        self.assertEqual(shell.get_attribute("data-theme"), "dark")
        dark = header.evaluate(
            "e => [getComputedStyle(e).backgroundColor, getComputedStyle(e).color]"
        )
        page.get_by_role("button", name="切换到亮色").click()
        page.wait_for_function(
            "() => document.querySelector('.bxw-shell').dataset.theme === 'light'"
        )
        light = header.evaluate(
            "e => [getComputedStyle(e).backgroundColor, getComputedStyle(e).color]"
        )
        self.assertNotEqual(dark[0], light[0])
        self.assertNotEqual(dark[1], light[1])

    def test_new_document_button_creates_an_empty_model(self) -> None:
        before = {row["id"] for row in self._documents()}
        page = self.context.new_page()
        self.addCleanup(page.close)
        page.goto(f"{self.service.base}/documents")
        page.get_by_role("button", name="新建文档").click()

        document_id = None
        deadline = time.monotonic() + STARTUP_TIMEOUT
        while document_id is None and time.monotonic() < deadline:
            created = {row["id"] for row in self._documents()} - before
            document_id = created.pop() if created else None
            if document_id is None:
                page.wait_for_timeout(200)
        self.assertIsNotNone(document_id)
        self.created.append(document_id)  # type: ignore[arg-type]

        page.goto(f"{self.service.base}/workbench?document={document_id}")
        page.locator(".bxw-shell").wait_for(state="visible")
        empty = page.locator(".bxw-empty")
        empty.wait_for(timeout=STARTUP_TIMEOUT * 1000)
        self.assertIn("在下方描述要创建的零件", empty.inner_text())

    def test_step_export_downloads_a_part21_file(self) -> None:
        document_id = self._document("impeller", "impeller")
        page = self.context.new_page()
        self.addCleanup(page.close)
        page.goto(f"{self.service.base}/documents")
        row = page.locator("tr", has_text=document_id)

        with page.expect_download(timeout=120000) as download:
            row.get_by_role("link", name="STEP").click()
        target = Path(self.service.folder.name) / "export.step"
        download.value.save_as(str(target))
        self.assertGreater(target.stat().st_size, 10_000)
        self.assertIn("ISO-10303-21", target.read_text(errors="replace")[:200])

    def test_header_is_one_band_with_one_tab_stop(self) -> None:
        document_id = self._document("flange", "flange")
        page = self._open(document_id)

        bands = page.evaluate(
            "() => [...document.querySelector('.bxw-header').children]"
            ".filter(e => e.offsetParent)"
            ".map(e => Math.round(e.getBoundingClientRect().height))"
        )
        # Brand, context and toolbar must sit on one row; a wrapped or mismatched
        # header is what made the old bar read as four unrelated widgets.
        self.assertEqual(len(bands), 3, bands)
        self.assertLessEqual(max(bands) - min(bands), 8, bands)

        toolbar = page.locator(".bxw-toolbar")
        self.assertEqual(toolbar.get_attribute("role"), "toolbar")
        self.assertTrue(toolbar.get_attribute("aria-label"))
        self.assertEqual(
            toolbar.locator('[role="separator"]').first.get_attribute("aria-orientation"),
            "vertical",
        )

        # One tab stop for the whole toolbar: tabbing from the document picker lands on
        # the first control and leaves the bar again in one press.
        page.locator(".bxw-context select").focus()
        page.keyboard.press("Tab")
        first = page.evaluate("() => document.activeElement.getAttribute('aria-label')")
        self.assertEqual(first, self._toolbar_items(page)[0])
        page.keyboard.press("Tab")
        inside = page.evaluate(
            "() => document.activeElement.closest('.bxw-toolbar') !== null"
        )
        self.assertFalse(inside, "toolbar still exposes more than one tab stop")

    def _toolbar_items(self, page) -> list[str]:
        return page.evaluate(
            "() => [...document.querySelectorAll('.bxw-toolbar button')]"
            ".filter(e => e.offsetParent).map(e => e.getAttribute('aria-label') || e.innerText.trim())"
        )

    def test_narrow_width_keeps_inspector_stats_and_dock(self) -> None:
        document_id = self._document("flange", "flange")
        page = self.context.new_page()
        self.addCleanup(page.close)
        page.set_viewport_size({"width": 900, "height": 900})
        page.goto(f"{self.service.base}/workbench?document={document_id}")
        page.locator(".bxw-shell").wait_for(state="visible")
        page.get_by_role("button", name="打开或收起检查器").click()
        page.locator(".bxw-inspector .bxw-stat").first.wait_for(state="visible")

        # The volume badge and the inspector cards used to share a class, so hiding the
        # badge at this width hid every card too.
        visible = page.evaluate(
            "() => [...document.querySelectorAll('.bxw-inspector .bxw-stat')]"
            ".filter(e => e.offsetParent !== null).length"
        )
        self.assertGreaterEqual(visible, 4)

        page.set_viewport_size({"width": 320, "height": 800})
        page.wait_for_timeout(600)
        dock = page.evaluate(
            "() => { const d = document.querySelector('.bxw-dock');"
            " return { scroll: d.scrollWidth, client: d.clientWidth }; }"
        )
        self.assertLessEqual(dock["scroll"], dock["client"] + 1, dock)
        small = page.evaluate(
            "() => [...document.querySelectorAll('.bxw-header button')]"
            ".filter(e => e.offsetParent)"
            ".map(e => { const r = e.getBoundingClientRect();"
            " return [Math.round(r.width), Math.round(r.height)]; })"
            ".filter(([w, h]) => w < 24 || h < 24)"
        )
        self.assertEqual(small, [], f"controls below the 24px minimum: {small}")

    def test_command_menu_lists_the_slash_commands(self) -> None:
        document_id = self._document("flange", "flange")
        page = self._open(document_id)

        menu = page.locator(".bxw-command-menu")
        self.assertTrue(menu.is_hidden())
        page.get_by_role("button", name="命令列表").click()
        menu.wait_for(state="visible")
        names = menu.locator("code").all_inner_texts()
        self.assertIn("/fit", names)
        self.assertIn("/checks", names)
        self.assertGreaterEqual(len(names), 10)

        menu.locator("button").first.click()
        command = page.get_by_label("命令或设计意图")
        self.assertEqual(command.input_value(), "/fit")
        self.assertTrue(menu.is_hidden())

    def test_dock_does_not_cover_the_model(self) -> None:
        document_id = self._document("flange", "flange")
        page = self._open(document_id)
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="适配视图").click()
        page.wait_for_timeout(1500)

        frame = page.locator(".bxw-frame").bounding_box()
        dock = page.locator(".bxw-dock").bounding_box()
        self.assertIsNotNone(frame)
        self.assertIsNotNone(dock)
        dock_top = dock["y"] - frame["y"]

        # An element screenshot paints whatever overlaps it, so the dock is hidden for
        # the measurement; otherwise its own border is counted as model geometry.
        page.evaluate("() => { document.querySelector('.bxw-dock').style.visibility = 'hidden' }")
        png = self._canvas(page).screenshot()

        # The viewport draws its own status strip along the bottom edge, so the model
        # band is measured above it.
        image = Image.open(io.BytesIO(png)).convert("RGB")
        width, height = image.size
        crop = image.crop((0, 0, width, height - 70))
        pixels = crop.load()
        background = pixels[5, 5]
        rows = [
            y
            for y in range(crop.height)
            if any(
                sum(abs(a - b) for a, b in zip(pixels[x, y], background)) > 40
                for x in range(0, width, 3)
            )
        ]
        self.assertTrue(rows, "viewport is blank")
        self.assertLess(rows[-1], dock_top, "the model extends behind the command dock")

    def test_undo_returns_to_the_parent_milestone(self) -> None:
        document_id = self._document("flange", "flange")
        page = self._open(document_id)
        page.get_by_role("button", name="打开或收起检查器").click()
        undo = page.get_by_role("button", name="撤销上一步")
        undo.wait_for(state="visible", timeout=STARTUP_TIMEOUT * 1000)
        before = page.locator(".bxw-badge-metric").inner_text().strip()

        undo.click()
        page.locator(".bxw-confirm").wait_for(state="visible")
        self.assertIn("撤销上一步", page.locator(".bxw-confirm").inner_text())
        page.locator(".bxw-confirm button[value=confirm]").click()

        # Revert is a new commit, so the version moves forward; what must change back is
        # the content, here to the blank milestone the flange was built from.
        empty = page.locator(".bxw-empty")
        empty.wait_for(state="visible", timeout=STARTUP_TIMEOUT * 1000)
        self.assertIn("空白模型", empty.inner_text())
        self.assertNotEqual(
            page.locator(".bxw-badge-metric").inner_text().strip(), before
        )

    def test_new_assembly_opens_as_an_assembly_document(self) -> None:
        before = {row["id"] for row in self._documents()}
        page = self.context.new_page()
        self.addCleanup(page.close)
        page.goto(f"{self.service.base}/workbench")
        page.locator(".bxw-shell").wait_for(state="visible")
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="打开或收起检查器").click()
        page.get_by_role("button", name="新建装配").first.click()

        page.get_by_role("button", name="查看装配 BOM").wait_for(
            state="visible", timeout=STARTUP_TIMEOUT * 1000
        )
        created = {row["id"] for row in self._documents()} - before
        self.assertEqual(len(created), 1, created)
        assembly_id = created.pop()
        self.created.append(assembly_id)
        self.assertTrue(assembly_id.startswith("a_"), assembly_id)
        self.assertEqual(
            page.evaluate("() => document.querySelector('.bxw-context select').value"),
            assembly_id,
        )
        self.assertIn("空装配", page.locator(".bxw-empty").inner_text())

    def test_external_edit_refreshes_the_open_document(self) -> None:
        document_id = self._document("flange", "flange")
        page = self._open(document_id)
        before = page.locator(".bxw-badge-metric").inner_text()

        # An agent edit is an ordinary HTTP write from outside this tab.
        changed = self.context.request.post(
            f"{self.service.base}/api/docs/{document_id}/tweak",
            data={
                "base_version": 1,
                "changes": [{"feature_id": "plate", "params": {"radius": 70.0}}],
                "title": "external edit",
            },
        )
        self.assertEqual(changed.status, 200, changed.text())

        page.wait_for_function(
            "previous => { const el = document.querySelector('.bxw-badge-metric');"
            " return el && el.textContent.trim() !== previous; }",
            arg=before.strip(),
            timeout=STARTUP_TIMEOUT * 1000,
        )
        self.assertEqual(page.locator(".bxw-version").inner_text().strip(), "v2")

    def _documents(self) -> list[dict[str, Any]]:
        return self.context.request.get(f"{self.service.base}/api/docs").json()


if __name__ == "__main__":
    unittest.main()
