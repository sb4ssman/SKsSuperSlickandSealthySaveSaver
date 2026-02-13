"""
Status window for SSSSSS.

The main UI window showing game status, settings, backup lists,
and restore controls. Accessible from the system tray.
"""

from __future__ import annotations

import datetime
import logging
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from typing import TYPE_CHECKING

from PIL import ImageTk

from core import backup, restore
from core.registry import GameDefinition

VERSION = "2.0.0"

if TYPE_CHECKING:
    from SuperSaveSaver import SuperSaveSaver

logger = logging.getLogger(__name__)


class StatusWindow:
    """Main status and settings window."""

    def __init__(self, app: SuperSaveSaver):
        self.app = app
        self.window: tk.Toplevel | None = None
        self._game_frames: dict[str, dict] = {}
        self._log_text: tk.Text | None = None

    def show(self) -> None:
        """Show the status window, creating it if needed."""
        if self.window is None or not self.window.winfo_exists():
            self._create()
        self.window.deiconify()
        self.window.lift()

    def hide(self) -> None:
        if self.window:
            self.window.withdraw()

    def log(self, message: str) -> None:
        """Append a message to the log pane."""
        if self._log_text and self._log_text.winfo_exists():
            self._log_text.insert(tk.END, message + "\n")
            self._log_text.see(tk.END)

    def refresh_game(self, game_id: str) -> None:
        """Refresh the display for a specific game."""
        if game_id in self._game_frames:
            frame_info = self._game_frames[game_id]
            self._update_game_status(game_id, frame_info)

    def _create(self) -> None:
        self.window = tk.Toplevel(self.app.root)
        self.window.title("SK's Super Slick and Stealthy Save Saver")
        self.window.geometry("900x650")
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        # Window icon
        if sys.platform == "win32":
            ico_path = self.app.app_dir / "app_icon.ico"
            if ico_path.exists():
                self.window.iconbitmap(str(ico_path))

        # Menu bar
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Minimize to Tray", command=self.hide)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.app.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

        # Main layout
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)

        # Row 0: Header with about + global settings
        header_frame = ttk.Frame(self.window)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))
        self._create_header(header_frame)

        # Row 1: Paned window with games list + log
        paned = ttk.PanedWindow(self.window, orient=tk.VERTICAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=5, pady=2)

        # Games notebook (tabs per game)
        self._notebook = ttk.Notebook(paned)
        paned.add(self._notebook, weight=3)

        # Log pane
        log_frame = ttk.LabelFrame(paned, text="Log")
        paned.add(log_frame, weight=1)
        self._create_log(log_frame)

        # Populate game tabs
        self._populate_game_tabs()

    def _create_header(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        # About section
        about_frame = ttk.LabelFrame(parent, text="About")
        about_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ttk.Label(about_frame, text=f"SSSSSS v{VERSION}").pack(anchor="w", padx=5)
        ttk.Label(
            about_frame,
            text="SK's Super Slick and Stealthy Save Saver",
        ).pack(anchor="w", padx=5)

        # Global settings
        settings_frame = ttk.LabelFrame(parent, text="Settings")
        settings_frame.grid(row=0, column=1, sticky="nsew")
        settings_frame.columnconfigure(1, weight=1)

        settings = self.app.settings_mgr.settings

        # Backup root
        ttk.Label(settings_frame, text="Backup Location:").grid(
            row=0, column=0, sticky="w", padx=5,
        )
        self._backup_root_var = tk.StringVar(
            value=str(self.app.settings_mgr.backup_root)
        )
        entry = ttk.Entry(settings_frame, textvariable=self._backup_root_var)
        entry.grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(
            settings_frame, text="Browse", width=7,
            command=self._browse_backup_root,
        ).grid(row=0, column=2, padx=2)

        # Max backups
        ttk.Label(settings_frame, text="Max Backups:").grid(
            row=1, column=0, sticky="w", padx=5,
        )
        self._max_backups_var = tk.IntVar(value=settings.default_max_backups)
        ttk.Spinbox(
            settings_frame, from_=5, to=500,
            textvariable=self._max_backups_var, width=6,
        ).grid(row=1, column=1, sticky="w", padx=2)

        # Compress
        self._compress_var = tk.BooleanVar(value=settings.compress_backups)
        ttk.Checkbutton(
            settings_frame, text="Compress backups (ZIP)",
            variable=self._compress_var,
        ).grid(row=1, column=2, sticky="w", padx=2)

        # Save settings button
        ttk.Button(
            settings_frame, text="Save Settings",
            command=self._save_global_settings,
        ).grid(row=2, column=2, sticky="e", padx=5, pady=2)

        # Backup size label
        self._size_label = ttk.Label(settings_frame, text="")
        self._size_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=5)
        self._update_total_size()

    def _create_log(self, parent: ttk.LabelFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self._log_text = tk.Text(parent, wrap="word", height=8)
        self._log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            parent, orient="vertical", command=self._log_text.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._log_text.config(yscrollcommand=scrollbar.set)

        # Load existing log file
        log_file = self.app.app_dir / "sssss.log"
        if log_file.exists():
            try:
                content = log_file.read_text(errors="replace")
                # Show last 100 lines
                lines = content.splitlines()[-100:]
                self._log_text.insert(tk.END, "\n".join(lines) + "\n")
            except Exception:
                pass
        self._log_text.see(tk.END)

    def _populate_game_tabs(self) -> None:
        """Create a tab for each configured game."""
        for game_id, game_config in self.app.settings_mgr.settings.games.items():
            game_def = self.app.registry.get(game_id)
            if game_def:
                self._add_game_tab(game_id, game_def)

    def _add_game_tab(self, game_id: str, game_def: GameDefinition) -> None:
        tab = ttk.Frame(self._notebook)
        self._notebook.add(tab, text=game_def.name)
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        game_config = self.app.settings_mgr.settings.get_game_config(game_id)

        # Row 0: Path settings
        path_frame = ttk.LabelFrame(tab, text="Paths")
        path_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        path_frame.columnconfigure(1, weight=1)

        save_var = tk.StringVar(value=game_config.save_path or "")
        ttk.Label(path_frame, text="Save Folder:").grid(row=0, column=0, sticky="w")
        save_entry = ttk.Entry(path_frame, textvariable=save_var)
        save_entry.grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(
            path_frame, text="Browse", width=7,
            command=lambda: self._browse_path(save_var),
        ).grid(row=0, column=2)
        ttk.Button(
            path_frame, text="Open", width=5,
            command=lambda: self._open_folder(save_var.get()),
        ).grid(row=0, column=3)

        backup_var = tk.StringVar(
            value=game_config.backup_dir or str(
                game_config.effective_backup_dir(self.app.settings_mgr.backup_root)
            )
        )
        ttk.Label(path_frame, text="Backup Folder:").grid(row=1, column=0, sticky="w")
        backup_entry = ttk.Entry(path_frame, textvariable=backup_var)
        backup_entry.grid(row=1, column=1, sticky="ew", padx=2)
        ttk.Button(
            path_frame, text="Browse", width=7,
            command=lambda: self._browse_path(backup_var),
        ).grid(row=1, column=2)
        ttk.Button(
            path_frame, text="Open", width=5,
            command=lambda: self._open_folder(backup_var.get()),
        ).grid(row=1, column=3)

        # Row 1: Controls
        ctrl_frame = ttk.Frame(tab)
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)

        is_watching = self.app.watcher.is_watching(game_id)
        status_label = ttk.Label(
            ctrl_frame,
            text=f"Watcher: {'Active' if is_watching else 'Inactive'}",
        )
        status_label.pack(side=tk.LEFT)

        ttk.Button(
            ctrl_frame, text="Save Settings",
            command=lambda gid=game_id, sv=save_var, bv=backup_var: (
                self._save_game_settings(gid, sv.get(), bv.get())
            ),
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            ctrl_frame, text="Save Now",
            command=lambda gid=game_id: self.app.save_now(gid),
        ).pack(side=tk.RIGHT, padx=5)

        # Row 2: Backup list (treeview)
        tree_frame = ttk.Frame(tab)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=2)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        columns = ("file", "date", "size")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        tree.heading("file", text="Backup", anchor="center")
        tree.heading("date", text="Date", anchor="center")
        tree.heading("size", text="Size", anchor="center")
        tree.column("file", width=250, anchor="w")
        tree.column("date", width=180, anchor="center")
        tree.column("size", width=100, anchor="e")
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        # Restore buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=3, column=0, sticky="w", padx=5, pady=2)
        ttk.Button(
            btn_frame, text="Restore Selected",
            command=lambda gid=game_id, t=tree: self._restore_selected(gid, t),
        ).pack(side=tk.LEFT, padx=(0, 5))

        # Store references
        self._game_frames[game_id] = {
            "tab": tab,
            "tree": tree,
            "status_label": status_label,
            "save_var": save_var,
            "backup_var": backup_var,
        }

        # Populate the treeview
        self._populate_backup_tree(game_id, tree)

    def _populate_backup_tree(self, game_id: str, tree: ttk.Treeview) -> None:
        tree.delete(*tree.get_children())

        game_config = self.app.settings_mgr.settings.get_game_config(game_id)
        backup_dir = game_config.effective_backup_dir(self.app.settings_mgr.backup_root)

        snapshots = restore.list_snapshots(backup_dir)
        # Show newest first
        for snap in reversed(snapshots):
            date_str = datetime.datetime.fromtimestamp(
                snap["time"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            size_str = backup.format_size(snap["size"])
            tree.insert("", "end", values=(snap["name"], date_str, size_str))

    def _update_game_status(self, game_id: str, frame_info: dict) -> None:
        is_watching = self.app.watcher.is_watching(game_id)
        frame_info["status_label"].config(
            text=f"Watcher: {'Active' if is_watching else 'Inactive'}"
        )
        self._populate_backup_tree(game_id, frame_info["tree"])

    def _update_total_size(self) -> None:
        total = 0
        backup_root = self.app.settings_mgr.backup_root
        if backup_root.exists():
            total = backup.get_backup_size(backup_root)
        self._size_label.config(text=f"Total backup size: {backup.format_size(total)}")

    def _browse_backup_root(self) -> None:
        folder = filedialog.askdirectory(initialdir=self._backup_root_var.get())
        if folder:
            self._backup_root_var.set(folder)

    def _browse_path(self, var: tk.StringVar) -> None:
        current = var.get()
        initial = current if current and Path(current).exists() else str(Path.home())
        folder = filedialog.askdirectory(initialdir=initial)
        if folder:
            var.set(folder)

    def _open_folder(self, path: str) -> None:
        if path and Path(path).exists():
            os.startfile(path)

    def _save_global_settings(self) -> None:
        settings = self.app.settings_mgr.settings
        settings.backup_root = self._backup_root_var.get()
        settings.default_max_backups = self._max_backups_var.get()
        settings.compress_backups = self._compress_var.get()
        self.app.settings_mgr.save()
        self._update_total_size()
        messagebox.showinfo("Settings", "Global settings saved.")

    def _save_game_settings(self, game_id: str, save_path: str,
                            backup_dir: str) -> None:
        config = self.app.settings_mgr.settings.get_game_config(game_id)
        config.save_path = save_path if save_path else None
        config.backup_dir = backup_dir if backup_dir else None
        self.app.settings_mgr.settings.set_game_config(config)
        self.app.settings_mgr.save()

        # Restart watcher if needed
        self.app.watcher.stop_watching(game_id)
        if config.enabled and config.save_path and Path(config.save_path).exists():
            bdir = config.effective_backup_dir(self.app.settings_mgr.backup_root)
            self.app.watcher.start_watching(game_id, Path(config.save_path), bdir)

        self.refresh_game(game_id)
        self.app.tray.update()
        messagebox.showinfo("Settings", f"{game_id} settings saved.")

    def _restore_selected(self, game_id: str, tree: ttk.Treeview) -> None:
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Select a backup to restore.")
            return

        snap_name = tree.item(selection[0], "values")[0]
        game_config = self.app.settings_mgr.settings.get_game_config(game_id)
        backup_dir = game_config.effective_backup_dir(
            self.app.settings_mgr.backup_root
        )
        snapshot_path = backup_dir / snap_name

        if not snapshot_path.exists():
            messagebox.showerror("Error", f"Backup not found: {snap_name}")
            return

        if not game_config.save_path:
            messagebox.showerror("Error", "No save path configured for this game.")
            return

        if messagebox.askyesno(
            "Confirm Restore",
            f"Restore {snap_name}?\n\nA safety backup of your current save "
            f"will be created first.",
        ):
            save_dir = Path(game_config.save_path)
            safety_dir = backup_dir / "_safety_backups"

            success = restore.restore_snapshot(snapshot_path, save_dir, safety_dir)
            if success:
                messagebox.showinfo("Restored", f"Successfully restored {snap_name}")
                self.log(f"Restored {snap_name} for {game_id}")
            else:
                messagebox.showerror("Error", f"Failed to restore {snap_name}")

    def _show_about(self) -> None:
        active = self.app.watcher.active_count()
        games = len(self.app.settings_mgr.settings.games)
        messagebox.showinfo("About", (
            f"SK's Super Slick and Stealthy Save Saver\n"
            f"Version {VERSION}\n\n"
            f"Real-time game save backup protection.\n\n"
            f"Configured games: {games}\n"
            f"Active watchers: {active}\n"
        ))
