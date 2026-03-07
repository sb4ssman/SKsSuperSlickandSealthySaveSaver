"""
ToolTip widget for tkinter.

Ported from the original ToolTips.py by Thomas.
Provides hover tooltips for any tkinter widget.

Usage:
    create_tooltip(widget, "Tooltip text")
"""

import tkinter as tk

DEFAULT_TOOLTIP_DELAY = 500


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str,
                 delay: int = DEFAULT_TOOLTIP_DELAY):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow: tk.Toplevel | None = None
        self.after_id: str | None = None
        self.enabled = True

        self._destroy_bind_id = self.widget.bind(
            "<Destroy>", self._on_destroy, add="+"
        )

    def show(self) -> None:
        self.hide()
        if self.enabled and self.text:
            try:
                self.after_id = self.widget.after(self.delay, self._display)
            except Exception:
                pass

    def _display(self) -> None:
        if not self.enabled or self.tipwindow or not self.widget.winfo_exists():
            return
        try:
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
            self.tipwindow = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                tw, text=self.text, justify=tk.LEFT,
                background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                font=("tahoma", "8", "normal"),
            )
            label.pack(ipadx=1)
            tw.wm_attributes("-topmost", True)
        except Exception:
            pass

    def hide(self) -> None:
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def _on_destroy(self, event) -> None:
        self.hide()
        if self._destroy_bind_id:
            try:
                self.widget.unbind("<Destroy>", self._destroy_bind_id)
            except Exception:
                pass
            self._destroy_bind_id = None

    def update_text(self, new_text: str) -> None:
        self.text = new_text
        if self.tipwindow:
            label = self.tipwindow.winfo_children()[0]
            label.config(text=self.text)

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False
        self.hide()


def create_tooltip(widget: tk.Widget, text: str,
                   delay: int = DEFAULT_TOOLTIP_DELAY) -> ToolTip:
    """Create and bind a tooltip to a widget. Returns the ToolTip instance."""
    tooltip = ToolTip(widget, text, delay)
    widget.bind("<Enter>", lambda e: tooltip.show(), add="+")
    widget.bind("<Leave>", lambda e: tooltip.hide(), add="+")
    return tooltip
