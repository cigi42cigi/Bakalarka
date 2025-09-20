import os
import sys
import shutil
import random
import time
import errno
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# ====== KONFIGURACE ======
CATEGORIES = {
    "1": "gunshot",
    "2": "noise",
    "3": "other",
}
AUDIO_EXTS = None

SHUFFLE = True
# =========================

try:
    import pygame
except ImportError:
    print("Chybí knihovna 'pygame'. Nainstaluj: pip install pygame")
    sys.exit(1)

# Bezpečný přesun souboru (řeší locky i síťové disky)
def safe_move(src: Path, dest: Path, retries: int = 6, wait: float = 0.25):
    last_err = None
    for _ in range(retries):
        try:
            if not src.exists():
                time.sleep(wait)
                continue
            return shutil.move(str(src), str(dest))
        except PermissionError as e:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            last_err = e
            time.sleep(wait)
        except FileNotFoundError as e:
            last_err = e
            time.sleep(wait)
    # fallback: copy+delete
    try:
        shutil.copy2(str(src), str(dest))
        try:
            os.remove(str(src))
        except FileNotFoundError:
            pass
        return str(dest)
    except Exception as e:
        raise last_err or e


class AudioSorter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Audio Sorter (Tkinter + pygame)")
        self.geometry("720x260")
        self.minsize(600, 220)

        self.source_dir = filedialog.askdirectory(title="Vyber složku se zvuky")
        if not self.source_dir:
            self.destroy()
            return

        self.source_path = Path(self.source_dir)
        for folder in CATEGORIES.values():
            (self.source_path / folder).mkdir(exist_ok=True, parents=True)

        self.files = [p for p in self.source_path.iterdir()
              if p.is_file() and (AUDIO_EXTS is None or p.suffix.lower() in AUDIO_EXTS)]

        if SHUFFLE:
            random.shuffle(self.files)

        self.history = []
        pygame.mixer.init()

        self.current_idx = -1
        self.current_path: Path | None = None
        self.is_paused = False

        self.build_ui()
        self.bind_hotkeys()
        self.next_file()
        self.after(300, self.poll_music)

    def build_ui(self):
        top = tk.Frame(self, padx=12, pady=10)
        top.pack(fill="x")

        self.lbl_folder = tk.Label(top, text=f"Složka: {self.source_dir}", anchor="w")
        self.lbl_folder.pack(fill="x")

        self.lbl_file = tk.Label(self, text="—", font=("Segoe UI", 14, "bold"),
                                 wraplength=680, justify="left")
        self.lbl_file.pack(fill="x", padx=12)

        self.lbl_progress = tk.Label(self, text="0 / 0", anchor="w")
        self.lbl_progress.pack(fill="x", padx=12, pady=(0, 8))

        btns = tk.Frame(self)
        btns.pack(pady=4)
        self.btn_play = tk.Button(btns, text="Play (Space)", width=14,
                                  command=self.toggle_play_pause)
        self.btn_play.grid(row=0, column=0, padx=4, pady=4)
        self.btn_replay = tk.Button(btns, text="Replay (R)", width=14,
                                    command=self.replay)
        self.btn_replay.grid(row=0, column=1, padx=4, pady=4)
        self.btn_skip = tk.Button(btns, text="Skip (N)", width=14,
                                  command=self.next_file)
        self.btn_skip.grid(row=0, column=2, padx=4, pady=4)
        self.btn_undo = tk.Button(btns, text="Undo (Backspace)", width=18,
                                  command=self.undo_move)
        self.btn_undo.grid(row=0, column=3, padx=4, pady=4)

        cats = tk.Frame(self)
        cats.pack(pady=(8, 12))
        tk.Label(cats, text="Zařaď do kategorie:").grid(row=0, column=0, sticky="w", padx=4)
        col = 1
        for key, name in CATEGORIES.items():
            b = tk.Button(cats, text=f"[{key}] {name}", width=16,
                          command=lambda k=key: self.categorize(k))
            b.grid(row=0, column=col, padx=4, pady=4)
            col += 1

        help_text = ("Klávesy: 1/2/3 = přesun do složek | Space = Play/Pause | "
                     "R = Replay | N = Skip | Backspace = Undo")
        self.lbl_help = tk.Label(self, text=help_text, fg="#666")
        self.lbl_help.pack(pady=(6, 4))

    def bind_hotkeys(self):
        self.bind("<space>", lambda e: self.toggle_play_pause())
        self.bind("<Key-r>", lambda e: self.replay())
        self.bind("<Key-R>", lambda e: self.replay())
        self.bind("<Key-n>", lambda e: self.next_file())
        self.bind("<Key-N>", lambda e: self.next_file())
        self.bind("<BackSpace>", lambda e: self.undo_move())
        for key in CATEGORIES.keys():
            self.bind(key, lambda e, kk=key: self.categorize(kk))
            self.bind(f"<KP_{key}>", lambda e, kk=key: self.categorize(kk))

    def load_and_play(self, path: Path):
        self.stop()
        self.is_paused = False
        self.current_path = path
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            self.btn_play.config(text="Pause (Space)")
        except Exception as e:
            messagebox.showerror("Chyba přehrávání", f"{path.name}\n\n{e}")
            self.next_file()

    def toggle_play_pause(self):
        if not self.current_path:
            return
        if pygame.mixer.music.get_busy() and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.btn_play.config(text="Play (Space)")
        else:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.btn_play.config(text="Pause (Space)")

    def replay(self):
        if self.current_path:
            self.load_and_play(self.current_path)

    def stop(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def poll_music(self):
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            self.btn_play.config(text="Play (Space)")
        self.after(300, self.poll_music)

    def next_file(self):
        self.stop()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        if not self.files:
            self.current_path = None
            self.lbl_file.config(text="Hotovo! Žádné další soubory.")
            self.lbl_progress.config(text="✓")
            return
        self.current_idx += 1
        if self.current_idx >= len(self.files):
            self.current_idx = 0
        path = self.files[self.current_idx]
        self.lbl_file.config(text=f"{path.name}")
        self.lbl_progress.config(text=f"{len(self.history)} z {len(self.history) + len(self.files)} zpracováno | {len(self.files)} zbývá")
        self.load_and_play(path)

    def categorize(self, key: str):
        if not self.current_path or key not in CATEGORIES:
            return
        dest_dir = self.source_path / CATEGORIES[key]
        dest_dir.mkdir(exist_ok=True, parents=True)
        src = self.current_path
        dest = dest_dir / src.name
        i = 1
        while dest.exists():
            dest = dest_dir / f"{src.stem}__{i}{src.suffix}"
            i += 1
        self.stop()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        try:
            safe_move(src, dest)
            self.history.append((dest, src))
            self.files.pop(self.current_idx)
            if self.current_idx >= len(self.files):
                self.current_idx = 0
            self.lbl_progress.config(text=f"{len(self.history)} z {len(self.history) + len(self.files)} zpracováno | {len(self.files)} zbývá")
            self.next_file()
        except Exception as e:
            messagebox.showerror("Chyba přesunu", f"{src.name}\n\n{e}")

    def undo_move(self):
        if not self.history:
            return
        try:
            moved_path, original_path = self.history.pop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            if original_path.exists():
                original_path = original_path.with_stem(original_path.stem + "__undo")
            safe_move(moved_path, original_path)
            if original_path.suffix.lower() in AUDIO_EXTS:
                self.files.insert(self.current_idx, original_path)
                self.lbl_progress.config(text=f"{len(self.history)} z {len(self.history) + len(self.files)} zpracováno | {len(self.files)} zbývá")
                self.load_and_play(original_path)
        except Exception as e:
            messagebox.showerror("Chyba Undo", str(e))


if __name__ == "__main__":
    app = AudioSorter()
    if app.winfo_exists():
        app.mainloop()
