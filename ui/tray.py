"""
System tray icon for SSSSSS.

Manages the pystray icon, menu construction, status indicator,
and tooltip. Delegates all actions back to callbacks.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import Callable, Optional

import pystray
from pystray import MenuItem
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


# Subclass pystray.Icon for double-click support on Windows
if sys.platform == "win32":
    class _Win32Icon(pystray.Icon):
        WM_LBUTTONDBLCLK = 0x0203

        def __init__(self, *args, **kwargs):
            self._on_double_click = kwargs.pop("on_double_click", None)
            super().__init__(*args, **kwargs)

        def _on_notify(self, wparam, lparam):
            super()._on_notify(wparam, lparam)
            if lparam == self.WM_LBUTTONDBLCLK and self._on_double_click:
                self._on_double_click(self, None)

    _IconClass = _Win32Icon
else:
    _IconClass = pystray.Icon


class TrayIcon:
    """Manages the system tray icon."""

    def __init__(
        self,
        on_show_status: Callable[[], None],
        on_quit: Callable[[], None],
        get_game_menu_items: Callable[[], list[MenuItem]],
        get_active_count: Callable[[], int],
        searching: bool = False,
    ):
        self._on_show_status = on_show_status
        self._on_quit = on_quit
        self._get_game_menu_items = get_game_menu_items
        self._get_active_count = get_active_count
        self._searching = searching
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Create and start the tray icon in a daemon thread."""
        self._create_icon()
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("Tray icon started")

    def stop(self) -> None:
        """Stop the tray icon."""
        if self._icon:
            self._icon.stop()
            self._icon = None
        logger.info("Tray icon stopped")

    def restart(self) -> None:
        """Recreate the tray icon (needed when menu structure changes)."""
        self.stop()
        self.start()

    def update(self) -> None:
        """Update the icon image and tooltip without restarting."""
        if self._icon:
            self._icon.icon = self._create_image()
            self._icon.title = self._get_tooltip()

    def set_searching(self, searching: bool) -> None:
        self._searching = searching
        self.update()

    def _create_icon(self) -> None:
        image = self._create_image()
        menu = self._build_menu()

        kwargs = {
            "name": "sssss_save_saver",
            "icon": image,
            "title": self._get_tooltip(),
            "menu": menu,
        }

        if sys.platform == "win32":
            kwargs["on_double_click"] = lambda icon, item: self._on_show_status()

        self._icon = _IconClass(**kwargs)

    def _build_menu(self) -> pystray.Menu:
        if self._searching:
            return pystray.Menu(
                MenuItem("Searching...", lambda: None, enabled=False),
            )

        game_items = self._get_game_menu_items()

        items = [
            MenuItem("Open Status Window", lambda: self._on_show_status()),
            pystray.Menu.SEPARATOR,
            *game_items,
            pystray.Menu.SEPARATOR,
            MenuItem("Quit", lambda: self._on_quit()),
        ]
        return pystray.Menu(*items)

    def _create_image(self) -> Image.Image:
        """Create the tray icon: turquoise square with purple S and status dot."""
        width, height = 64, 64
        image = Image.new("RGB", (width, height), (64, 224, 208))
        draw = ImageDraw.Draw(image)

        # Purple "S" shape
        segments = [
            [(49, 15), (19, 15), (19, 25), (49, 25)],
            [(9, 25), (19, 25), (19, 35), (9, 35)],
            [(19, 35), (49, 35), (49, 45), (19, 45)],
            [(49, 45), (39, 45), (39, 55), (49, 55)],
            [(39, 55), (9, 55), (9, 65), (39, 65)],
        ]
        for seg in segments:
            draw.polygon(seg, fill=(128, 0, 128))

        # Status indicator
        if self._searching:
            color = (255, 165, 0)   # Orange while searching
        elif self._get_active_count() > 0:
            color = (0, 255, 0)     # Green when watching
        else:
            color = (255, 0, 0)     # Red when idle
        draw.rectangle([width - 15, 0, width, 15], fill=color)

        return image

    def _get_tooltip(self) -> str:
        base = "SK's Super Slick and\nStealthy Save Saver"
        if self._searching:
            return f"{base}\nSearching for games..."

        count = self._get_active_count()
        if count > 0:
            return f"{base}\nActive watchers: {count}"
        return f"{base}\nNo active watchers"

    def create_image_no_status(self) -> Image.Image:
        """Create icon image without status indicator (for window icons)."""
        width, height = 64, 64
        image = Image.new("RGB", (width, height), (64, 224, 208))
        draw = ImageDraw.Draw(image)

        segments = [
            [(49, 15), (19, 15), (19, 25), (49, 25)],
            [(9, 25), (19, 25), (19, 35), (9, 35)],
            [(19, 35), (49, 35), (49, 45), (19, 45)],
            [(49, 45), (39, 45), (39, 55), (49, 55)],
            [(39, 55), (9, 55), (9, 65), (39, 65)],
        ]
        for seg in segments:
            draw.polygon(seg, fill=(128, 0, 128))

        return image
