import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime, timedelta

APP_NAME = "ReadReminderMVP"

# MVP behavior:
DELAY_AFTER_LOGIN_MIN = 20          # popup appears 20 mins after app starts
SNOOZE_AFTER_CLOSE_MIN = 30         # if closed, don't show again for 30 mins

APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
DATA_JSON = APPDATA_DIR / "data.json"
OBSIDIAN_DIR = Path("C:/obsidian")
COMPLETED_MD = OBSIDIAN_DIR / "2026-Reading-List.md"

def open_list_in_obsidian():
    uri = f"obsidian://open?vault={"obsidian"}&file={COMPLETED_MD}"
    os.startfile(uri)

def apply_theme(root: tk.Tk):
    default_font = ("Segoe UI", 11)
    root.option_add("*Font", default_font)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Purple palette
    PURPLE = "#6D28D9"      # violet-700-ish
    PURPLE_DARK = "#5B21B6"
    LAVENDER = "#F5F3FF"    # violet-50-ish
    TEXT = "#111827"

    style.configure("Card.TFrame", background=LAVENDER)
    style.configure("Title.TLabel", background=LAVENDER, foreground=TEXT, font=("Segoe UI", 16, "bold"))
    style.configure("Subtitle.TLabel", background=LAVENDER, foreground=TEXT, font=("Segoe UI", 11, "bold"))
    style.configure("Body.TLabel", background=LAVENDER, foreground=TEXT)

    style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(12, 8))
    style.map("Primary.TButton",
              background=[("active", PURPLE_DARK), ("!active", PURPLE)],
              foreground=[("!disabled", "white")])

    style.configure("Secondary.TButton", padding=(10, 8))


def now_utc_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds") + "Z"


def parse_utc_iso(s: str) -> datetime:
    # expects "...Z"
    if s.endswith("Z"):
        s = s[:-1]
    return datetime.fromisoformat(s)


def ensure_storage():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    if not COMPLETED_MD.exists():
        COMPLETED_MD.write_text(
            "# 2026 Reading List (Completed)\n\n"
            "## Completed Items\n\n"
            "## In Progress\n\n"
            "- [ ] Preacher Man\n\n",
            encoding="utf-8"
        )
    if not DATA_JSON.exists():
        default = {
            "active": [
                {"title": "Preacher Man", "last_page": 0, "kind": "book"},
                {"title": "Farnam Street", "last_page": 0, "kind": "blog"},
                {"title": "Example Article: Notes on Learning", "last_page": 0, "kind": "article"},
            ],
            "next_popup_not_before": None
        }
        DATA_JSON.write_text(json.dumps(default, indent=2), encoding="utf-8")


def load_data():
    ensure_storage()
    try:
        return json.loads(DATA_JSON.read_text(encoding="utf-8"))
    except Exception:
        # if corrupted, back it up and reset
        backup = APPDATA_DIR / f"data.backup.{int(datetime.datetime.now(datetime.UTC).timestamp())}.json"
        try:
            backup.write_text(DATA_JSON.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
        default = {"active": [], "next_popup_not_before": None}
        DATA_JSON.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default


def save_data(data):
    DATA_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_completed_md(title: str, last_page: int, kind: str):
    line = f"- **{title}** ({kind}) — completed at page **{last_page}** on {datetime.now().strftime('%Y-%m-%d')}\n"
    with COMPLETED_MD.open("a", encoding="utf-8") as f:
        f.write(line)


class ReadingListEditor(tk.Toplevel):
    def __init__(self, parent, data, on_save):
        super().__init__(parent)
        apply_theme(self)
        self.title("Reading List (Active)")
        self.resizable(False, False)
        self.data = data
        self.on_save = on_save
        self.new_item_mode = False

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Active reading list", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w")

        self.listbox = tk.Listbox(frm, width=60, height=10)
        self.listbox.grid(row=1, column=0, columnspan=4, pady=(8, 8), sticky="w")
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        ttk.Label(frm, text="Title:").grid(row=2, column=0, sticky="e")
        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(frm, width=45, textvariable=self.title_var)
        self.title_entry.grid(row=2, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=2)

        ttk.Label(frm, text="Last page:").grid(row=3, column=0, sticky="e")
        self.page_var = tk.StringVar()
        self.page_entry = ttk.Entry(frm, width=10, textvariable=self.page_var)
        self.page_entry.grid(row=3, column=1, sticky="w", padx=(8, 0), pady=2)

        ttk.Label(frm, text="Type:").grid(row=3, column=2, sticky="e")
        self.kind_var = tk.StringVar(value="book")
        self.kind_combo = ttk.Combobox(frm, width=12, textvariable=self.kind_var, values=["book", "blog", "article", "paper"], state="readonly")
        self.kind_combo.grid(row=3, column=3, sticky="w", padx=(8, 0), pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=4, pady=(10, 0), sticky="w")

        ttk.Button(btns, text="Add new", command=self.add_new, style="Primary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Save changes", command=self.save_selected, style="Primary.TButton").grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Remove", command=self.remove_selected, style="Primary.TButton").grid(row=0, column=2, padx=(0, 8))
        ttk.Button(btns, text="Mark completed", command=self.mark_completed, style="Primary.TButton").grid(row=0, column=3, padx=(0, 8))
        ttk.Button(btns, text="See 2026 Reading List", command=self.open_completed, style="Primary.TButton").grid(row=0, column=4)

        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for item in self.data["active"]:
            self.listbox.insert(tk.END, f'{item.get("title","(untitled)")}  —  page {item.get("last_page", 0)}  ({item.get("kind","book")})')
        # clear fields
        self.title_var.set("")
        self.page_var.set("")
        self.kind_var.set("book")

    def current_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def on_select(self, _evt=None):
        idx = self.current_index()
        self.new_item_mode = False
        if idx is None:
            return
        item = self.data["active"][idx]
        self.title_var.set(item.get("title", ""))
        self.page_var.set(str(item.get("last_page", 0)))
        self.kind_var.set(item.get("kind", "book"))

    def add_new(self):
        self.new_item_mode = True
        self.listbox.selection_clear(0, tk.END)
        self.title_var.set("")
        try:
            self.kind_var.set("book")
        except Exception:
            pass
        self.page_var.set("0")
        self.title_entry.focus_set()

    def save_selected(self):
        idx = self.current_index()
        title = self.title_var.get().strip() or "Untitled"
        try:
            page = int(self.page_var.get().strip() or "0")
            if page < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid page", "Last page must be a non-negative integer.")
            return
        kind = self.kind_var.get() or "book"

        if self.new_item_mode or idx is None:
            self.data["active"].append({"title": title, "kind": kind, "last_page": page})
            self.new_item_mode = False
            self.on_save(self.data)
            self.refresh()

            # select the newly added item
            new_idx = len(self.data["active"]) - 1
            if new_idx >= 0:
                self.listbox.selection_set(new_idx)
                self.listbox.see(new_idx)
            return

        self.data["active"][idx] = {"title": title, "kind": kind, "last_page": page}

        self.on_save(self.data)
        self.refresh()
        self.listbox.selection_set(idx)
        self.listbox.see(idx)


    def remove_selected(self):
        idx = self.current_index()
        if idx is None:
            messagebox.showinfo("Remove", "Select an item first.")
            return
        del self.data["active"][idx]
        self.on_save(self.data)
        self.refresh()

    def mark_completed(self):
        idx = self.current_index()
        if idx is None:
            messagebox.showinfo("Completed", "Select an item first.")
            return
        item = self.data["active"][idx]
        append_completed_md(item.get("title", "Untitled"), int(item.get("last_page", 0)), item.get("kind", "book"))
        del self.data["active"][idx]
        self.on_save(self.data)
        self.refresh()
        messagebox.showinfo("Completed", "Marked completed and added to 2026 Reading List markdown.")

    def open_completed(self):
        try:
            open_list_in_obsidian() #os.startfile(str(COMPLETED_MD))
        except Exception as e:
            messagebox.showerror("Open failed", f"Could not open markdown file:\n{e}")


class TimerWindow(tk.Toplevel):
    def __init__(self, parent, minutes, on_done):
        super().__init__(parent)
        self.title("Reading Timer")
        self.resizable(False, False)
        self.on_done = on_done

        self.total_seconds = max(1, int(minutes * 60))
        self.remaining = self.total_seconds
        self.running = True

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Reading timer running", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")

        self.time_label = ttk.Label(frm, text="", font=("Segoe UI", 24, "bold"))
        self.time_label.grid(row=1, column=0, pady=(8, 10))

        ttk.Button(frm, text="Stop", command=self.stop, style="Primary.TButton").grid(row=2, column=0, padx=(0, 8))
        ttk.Button(frm, text="Hide", command=self.hide, style="Primary.TButton").grid(row=2, column=1)

        self.protocol("WM_DELETE_WINDOW", self.hide)  # closing hides it
        self.tick()

    def format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def tick(self):
        if not self.running:
            return
        self.time_label.config(text=self.format_time(self.remaining))
        if self.remaining <= 0:
            self.running = False
            self.destroy()
            self.on_done()
            return
        self.remaining -= 1
        self.after(1000, self.tick)

    def stop(self):
        self.running = False
        self.destroy()

    def hide(self):
        # keep running but hide window
        self.withdraw()

        # Create a tiny "restore" toast-ish window so user can bring it back.
        # Super MVP: a small always-on-top window.
        toast = tk.Toplevel()
        toast.title("Timer")
        toast.attributes("-topmost", True)
        toast.resizable(False, False)
        frm = ttk.Frame(toast, padding=8)
        frm.grid(row=0, column=0)
        ttk.Label(frm, text="Reading timer running…").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(frm, text="Show", command=lambda: (toast.destroy(), self.deiconify())).grid(row=0, column=1)
        toast.protocol("WM_DELETE_WINDOW", lambda: None)


class LogWindow(tk.Toplevel):
    def __init__(self, parent, data, on_submit):
        super().__init__(parent)
        self.title("Log your reading")
        self.resizable(False, False)
        self.data = data
        self.on_submit = on_submit
        self.geometry("520x320")

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Great job, girl! Log what you read:", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(frm, text="What you read:", style="Subtitle.TLabel").grid(row=1, column=0, sticky="e", pady=(10, 4))
        self.choice_var = tk.StringVar()
        titles = [item.get("title", "Untitled") for item in self.data["active"]]
        if titles:
            self.choice_var.set(titles[0])
        self.choice = ttk.Combobox(frm, width=45, textvariable=self.choice_var, values=titles, state="readonly")
        self.choice.grid(row=1, column=1, sticky="w", pady=(10, 4))

        ttk.Label(frm, text="Last page read:", style="Subtitle.TLabel").grid(row=2, column=0, sticky="e", pady=4)
        self.page_var = tk.StringVar()
        self.page_entry = ttk.Entry(frm, width=10, textvariable=self.page_var)
        self.page_entry.grid(row=2, column=1, sticky="w", pady=4)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="w")
        ttk.Button(btns, text="Submit", command=self.submit, style="Primary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Cancel", command=self.destroy).grid(row=0, column=1)

    def submit(self):
        title = self.choice_var.get().strip()
        if not title:
            messagebox.showerror("Missing", "Select a title.")
            return
        try:
            page = int(self.page_var.get().strip())
            if page < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid", "Last page must be a non-negative integer.")
            return

        self.on_submit(title, page)
        self.destroy()


class ReminderPopup(tk.Toplevel):
    def __init__(self, parent, data, on_start_reading, on_close_snooze):
        super().__init__(parent)
        self.title("Reminder to read!")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.on_start_reading = on_start_reading
        self.on_close_snooze = on_close_snooze

        frm = ttk.Frame(self, padding=16, style="Card.TFrame")
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Reminder to read!", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        ttk.Label(frm, text="Current reading list:", style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 4))

        text = tk.Text(frm, width=60, height=6, wrap="word")
        text.configure(
            bg="#FFFFFF",
            fg="#111827",
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#7062B4",  # light purple border
            padx=10,
            pady=8,
)

        text.grid(row=2, column=0, sticky="w")
        text.insert("1.0", self.format_list(data))
        text.config(state="disabled")

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, sticky="w", pady=(10, 0))

        ttk.Button(btns, text="Start reading", command=self.start, style="Primary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Close", command=self.close, style="Secondary.TButton").grid(row=0, column=1)

        self.protocol("WM_DELETE_WINDOW", self.close)

        # Center-ish on screen
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 3) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def format_list(self, data):
        active = data.get("active", [])
        if not active:
            return "No active items.\n\n(Use the editor after your next timer to add items.)"
        lines = []
        for i, item in enumerate(active, start=1):
            lines.append(f"{i}. {item.get('title','Untitled')}  —  page {item.get('last_page',0)}  ({item.get('kind','book')})")
        return "\n".join(lines)

    def start(self):
        self.destroy()
        self.on_start_reading()

    def close(self):
        self.destroy()
        self.on_close_snooze()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_theme(self)
        self.withdraw()  # no main window for MVP
        self.data = load_data()

        self.popup_handle = None
        self.scheduled_popup_id = None

        # Decide first popup time
        not_before = self.data.get("next_popup_not_before")
        force_popup_now = ("--popup-now" in sys.argv)

        if not_before and not force_popup_now:
            try:
                dt = parse_utc_iso(not_before)
                # dt is UTC; compare with utcnow
                delay = max(0, int((dt - datetime.datetime.now(datetime.UTC)).total_seconds()))
                self.schedule_popup_in_seconds(delay)
                return
            except Exception:
                pass

        # default: 20 mins after app start
        self.schedule_popup_in_seconds(DELAY_AFTER_LOGIN_MIN * 60)

    def schedule_popup_in_seconds(self, seconds: int):
        if self.scheduled_popup_id is not None:
            try:
                self.after_cancel(self.scheduled_popup_id)
            except Exception:
                pass
        self.scheduled_popup_id = self.after(seconds * 1000, self.show_popup)

    def show_popup(self):
        # Enforce snooze
        not_before = self.data.get("next_popup_not_before")
        if not_before:
            try:
                dt = parse_utc_iso(not_before)
                if datetime.datetime.now(datetime.UTC) < dt:
                    delay = max(0, int((dt - datetime.datetime.now(datetime.UTC)).total_seconds()))
                    self.schedule_popup_in_seconds(delay)
                    return
            except Exception:
                pass

        if self.popup_handle and self.popup_handle.winfo_exists():
            return

        self.data = load_data()  # reload latest
        self.popup_handle = ReminderPopup(
            parent=self,
            data=self.data,
            on_start_reading=self.start_read_flow,
            on_close_snooze=self.snooze_30m
        )

    def snooze_30m(self):
        dt = datetime.datetime.now(datetime.UTC) + timedelta(minutes=SNOOZE_AFTER_CLOSE_MIN)
        self.data["next_popup_not_before"] = dt.isoformat(timespec="seconds") + "Z"
        save_data(self.data)

        # schedule next popup at not-before time (while app is running)
        self.schedule_popup_in_seconds(SNOOZE_AFTER_CLOSE_MIN * 60)

    def start_read_flow(self):
        minutes = self.ask_minutes()
        if minutes is None:
            # If they cancel, snooze a bit so it doesn't instantly reappear
            self.snooze_30m()
            return

        def timer_done():
            self.show_log_form()

        TimerWindow(self, minutes=minutes, on_done=timer_done)

    def ask_minutes(self):
        dialog = tk.Toplevel(self)
        dialog.title("Set timer")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        frm = ttk.Frame(dialog, padding=12)
        frm.grid(row=0, column=0)

        ttk.Label(frm, text="How many minutes do you want to read?", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")

        mins_var = tk.StringVar(value="10")
        ttk.Label(frm, text="Minutes:").grid(row=1, column=0, sticky="e", pady=(10, 0))
        entry = ttk.Entry(frm, width=10, textvariable=mins_var)
        entry.grid(row=1, column=1, sticky="w", pady=(10, 0))
        entry.focus_set()

        result = {"value": None}

        def ok():
            try:
                m = int(mins_var.get().strip())
                if m <= 0 or m > 600:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Invalid", "Enter minutes as an integer between 1 and 600.")
                return
            result["value"] = m
            dialog.destroy()

        def cancel():
            result["value"] = None
            dialog.destroy()

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=2, pady=(12, 0), sticky="w")
        ttk.Button(btns, text="Start", command=ok, style="Primary.TButton").grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Cancel", command=cancel, style="Primary.TButton").grid(row=0, column=1)

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        self.wait_window(dialog)
        return result["value"]

    def show_log_form(self):
        self.data = load_data()

        def on_submit(title, page):
            # Update the chosen item
            updated = False
            for item in self.data.get("active", []):
                if item.get("title") == title:
                    item["last_page"] = page
                    updated = True
                    break
            if not updated:
                # if somehow missing, add it
                self.data.setdefault("active", []).append({"title": title, "last_page": page, "kind": "book"})

            save_data(self.data)

            # Then show editor to adjust / complete / remove
            ReadingListEditor(self, self.data, on_save=lambda d: save_data(d))

            # After a reading session, snooze popup for 30 mins
            self.snooze_30m()

        if not self.data.get("active"):
            # Still allow logging even if empty
            messagebox.showinfo("Reading list empty", "Your reading list is empty. Add items in the editor.")
            ReadingListEditor(self, self.data, on_save=lambda d: save_data(d))
            self.snooze_30m()
            return

        LogWindow(self, self.data, on_submit=on_submit)


def main():
    ensure_storage()
    if "--reset" in sys.argv:
        data = load_data()
        data["next_popup_not_before"] = None
        save_data(data)
        print("Reset: next_popup_not_before cleared")

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
