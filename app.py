"""Desktop GUI for MQL Builder Agent.

Run agent requests in a background thread and show results.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import threading
from tkinter import filedialog

import customtkinter as ctk

from main import (
    AGENT_DESCRIPTION,
    AGENT_NAME,
    PROVIDER,
    _read_mql_file,
    run_agent,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PAD = {"padx": 12, "pady": 6}
PREVIEW_HEIGHT = 280
OUTPUT_HEIGHT = 320
TOPIC_HEIGHT = 72


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class _LogRedirect(io.StringIO):
    """Redirect stdout to the output textbox for real-time log display."""

    def __init__(self, gui: "MqlBuilderGUI") -> None:
        """Store GUI reference for log appending."""
        super().__init__()
        self._gui = gui

    def write(self, s: str) -> int:
        """Strip ANSI codes and forward text to output box."""
        clean = _ANSI_RE.sub("", s)
        if clean:
            self._gui.root.after(0, self._gui._append_log, clean)
        return super().write(s)

    def flush(self) -> None:
        """No-op flush for stdout compatibility."""


class MqlBuilderGUI:
    """Main application window for the MQL Builder Agent."""

    def __init__(self) -> None:
        """Initialize window, state, and build the UI."""
        self.root = ctk.CTk()
        self.root.title(AGENT_NAME)
        self.root.geometry("960x820")
        self.root.minsize(720, 640)

        self._selected_file: str = ""
        self._output_path: str = ""
        self._running = False

        self._build_ui()

    def _build_ui(self) -> None:
        """Create all UI elements and layout."""
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        main = ctk.CTkScrollableFrame(self.root)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        # Enable independent textbox scrolling
        main.bind_class("CTkTextbox", "<MouseWheel>", lambda e: "break")

        # Header
        ctk.CTkLabel(
            main, text=AGENT_NAME, font=("", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", **PAD)
        ctk.CTkLabel(
            main, text=AGENT_DESCRIPTION + ".", font=("", 11),
            text_color="gray",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        # File selection
        file_frame = ctk.CTkFrame(main)
        file_frame.grid(row=2, column=0, sticky="ew", **PAD)
        file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(file_frame, text="File:", font=("", 12, "bold")).grid(
            row=0, column=0, sticky="w", padx=(8, 4), pady=6,
        )

        self.file_entry = ctk.CTkEntry(
            file_frame, placeholder_text="Select .mq4 or .mq5 file to edit...",
        )
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=6)

        ctk.CTkButton(
            file_frame, text="Browse", command=self._browse_file, width=80,
        ).grid(row=0, column=2, padx=4, pady=6)
        ctk.CTkButton(
            file_frame, text="Clear", command=self._clear_file, width=60,
            fg_color="transparent", border_width=1,
        ).grid(row=0, column=3, padx=(4, 8), pady=6)

        # File preview
        ctk.CTkLabel(main, text="File Preview", font=("", 12, "bold")).grid(
            row=3, column=0, sticky="w", padx=12, pady=(8, 2),
        )
        self.preview_box = ctk.CTkTextbox(main, height=PREVIEW_HEIGHT, wrap="none")
        self.preview_box.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.preview_box.configure(state="disabled")
        self._enable_text_scroll(self.preview_box)

        # Request input
        ctk.CTkLabel(main, text="Request", font=("", 12, "bold")).grid(
            row=5, column=0, sticky="w", padx=12, pady=(8, 2),
        )
        ctk.CTkLabel(
            main, text="Describe what to create or what changes to make to the file.",
            font=("", 10), text_color="gray",
        ).grid(row=5, column=0, sticky="e", padx=12, pady=(8, 2))

        self.topic_box = ctk.CTkTextbox(main, height=TOPIC_HEIGHT, wrap="word")
        self.topic_box.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 8))
        self._enable_text_scroll(self.topic_box)

        # Run row
        run_frame = ctk.CTkFrame(main, fg_color="transparent")
        run_frame.grid(row=7, column=0, sticky="ew", padx=12, pady=4)
        run_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(run_frame, text=f"Provider: {PROVIDER.label}").grid(
            row=0, column=0, sticky="w", padx=(0, 12),
        )

        self.status_label = ctk.CTkLabel(
            run_frame, text="Idle", text_color="gray", font=("", 11),
        )
        self.status_label.grid(row=0, column=1, sticky="w")

        self.run_btn = ctk.CTkButton(
            run_frame, text="Run Agent", command=self._on_run, width=120, height=32,
        )
        self.run_btn.grid(row=0, column=2, sticky="e")

        # Output viewer
        ctk.CTkLabel(main, text="Output", font=("", 12, "bold")).grid(
            row=8, column=0, sticky="w", padx=12, pady=(12, 2),
        )
        self.output_box = ctk.CTkTextbox(main, height=OUTPUT_HEIGHT, wrap="none")
        self.output_box.grid(row=9, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.output_box.configure(state="disabled")
        self._enable_text_scroll(self.output_box)

        # Save button
        save_frame = ctk.CTkFrame(main, fg_color="transparent")
        save_frame.grid(row=10, column=0, sticky="ew", padx=12, pady=(4, 16))

        self.save_btn = ctk.CTkButton(
            save_frame, text="Save Output As...", command=self._save_output,
            width=140, height=28, state="disabled",
        )
        self.save_btn.grid(row=0, column=0, sticky="e")

    # File operations
    def _enable_text_scroll(self, box: ctk.CTkTextbox) -> None:
        """Bind mousewheel to scroll textbox content."""
        def _scroll(event):
            delta = -1 if event.delta > 0 else 1
            box._textbox.yview_scroll(delta, "units")
            return "break"
        box._textbox.bind("<MouseWheel>", _scroll)

    def _browse_file(self) -> None:
        """Open file dialog and load MQL file."""
        path = filedialog.askopenfilename(
            title="Select MQL File",
            filetypes=[
                ("MQL Files", "*.mq4 *.mq5"),
                ("All Files", "*.*"),
            ],
        )
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path: str) -> None:
        """Read and display MQL file in preview."""
        try:
            content, ext = _read_mql_file(path)
        except FileNotFoundError:
            self._set_status("File not found.", "red")
            return

        self._selected_file = path
        self.file_entry.delete(0, "end")
        self.file_entry.insert(0, path)

        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", content)
        self.preview_box.configure(state="disabled")

        mql_ver = "MQL5" if ext == ".mq5" else "MQL4"
        self._set_status(f"Loaded {mql_ver} file ({len(content)} chars).")

    def _clear_file(self) -> None:
        """Clear file selection, preview, and output."""
        self._selected_file = ""
        self._output_path = ""
        self.file_entry.delete(0, "end")
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self._set_status("File cleared.")

    # Agent execution
    def _on_run(self) -> None:
        """Validate input and launch agent in thread."""
        if self._running:
            return

        topic = self.topic_box.get("1.0", "end").strip()
        if not topic:
            self._set_status("Enter a request first.", "red")
            return

        self._running = True
        self.run_btn.configure(state="disabled", text="Running...")
        self._set_status("Agent running...", "#3b82f6")
        self._clear_output()

        thread = threading.Thread(
            target=self._run_agent_thread, args=(topic,), daemon=True,
        )
        thread.start()
        self._poll_thread(thread)

    def _run_agent_thread(self, topic: str) -> None:
        """Run agent in thread, capturing stdout."""
        old_stdout = sys.stdout
        sys.stdout = _LogRedirect(self)
        try:
            self._result = run_agent(topic, file_path=self._selected_file)
        except Exception as exc:
            self._result = json.dumps({"status": "error", "message": str(exc)})
        finally:
            sys.stdout = old_stdout

    def _poll_thread(self, thread: threading.Thread) -> None:
        """Poll thread until done, then display result."""
        if thread.is_alive():
            self.root.after(200, self._poll_thread, thread)
            return

        self._running = False
        self.run_btn.configure(state="normal", text="Run Agent")
        self._handle_result()

    def _handle_result(self) -> None:
        """Parse agent result, show compilation log and source."""
        result = getattr(self, "_result", "")
        if not result:
            self._set_status("No output from agent.", "red")
            return

        try:
            data = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            self._append_log(result)
            self._set_status("Agent finished.")
            return

        status = data.get("status", "")
        if status == "error":
            self._set_status(data.get("message", "Error."), "red")
            self._append_log(result)
            return

        file_path = data.get("file_path", "")
        self._output_path = file_path

        compilation_log = data.get("compilation_log", "")
        errors = data.get("errors", "")
        warnings = data.get("warnings", "")

        output_parts = []
        if file_path:
            output_parts.append(f"File: {file_path}")
        if compilation_log:
            output_parts.append(f"--- Compilation Log ---\n{compilation_log}")
        if errors:
            output_parts.append(f"--- Errors ---\n{errors}")
        if warnings:
            output_parts.append(f"--- Warnings ---\n{warnings}")

        if file_path and os.path.isfile(file_path):
            try:
                source, _ = _read_mql_file(file_path)
                output_parts.append(f"--- Source ---\n{source}")
                self.save_btn.configure(state="normal")
            except FileNotFoundError:
                output_parts.append("(source file not found)")

        self._append_log("\n".join(output_parts))

        if errors:
            self._set_status("Compiled with errors.", "#eab308")
        elif warnings:
            self._set_status("Compiled with warnings.", "#eab308")
        else:
            self._set_status("Agent finished successfully.", "green")

    # Output handling
    def _append_log(self, text: str) -> None:
        """Append text to output box and auto-scroll."""
        self.output_box.configure(state="normal")
        self.output_box.insert("end", text)
        self.output_box.see("end")
        self.output_box.configure(state="disabled")

    def _clear_output(self) -> None:
        """Clear the output viewer text."""
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.configure(state="disabled")

    def _save_output(self) -> None:
        """Prompt save dialog and write output to disk."""
        source = self._output_path
        if not source or not os.path.isfile(source):
            dest = filedialog.asksaveasfilename(
                title="Save Output",
                defaultextension=".mq5",
                filetypes=[
                    ("MQL5 Files", "*.mq5"),
                    ("MQL4 Files", "*.mq4"),
                    ("All Files", "*.*"),
                ],
            )
            if not dest:
                return
            content = self.output_box.get("1.0", "end")
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)
            self._set_status(f"Saved to {dest}.")
            return

        dest = filedialog.asksaveasfilename(
            title="Save Output As",
            initialfile=os.path.basename(source),
            defaultextension=os.path.splitext(source)[1],
            filetypes=[
                ("MQL5 Files", "*.mq5"),
                ("MQL4 Files", "*.mq4"),
                ("All Files", "*.*"),
            ],
        )
        if not dest:
            return
        try:
            content, _ = _read_mql_file(source)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)
            self._set_status(f"Saved to {dest}.")
        except (OSError, FileNotFoundError) as exc:
            self._set_status(f"Save failed: {exc}", "red")

    # Status bar
    def _set_status(self, text: str, color: str = "gray") -> None:
        """Set status label text and color."""
        self.status_label.configure(text=text, text_color=color)

    # Entry point
    def run(self) -> None:
        """Start the GUI main loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = MqlBuilderGUI()
    app.run()
