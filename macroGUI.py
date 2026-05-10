import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tissueScanFunctions
import multipointsFunctions
import continuingFunctions
import os
import shutil
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileTableTissue(ttk.Frame):
    """A frame containing a file table with add/remove and drag-drop reorder."""
    def __init__(self, parent):
        super().__init__(parent)
        self.n_z = tk.StringVar(value='75')
        self.autofocus_channel = tk.StringVar(value='DAPI')
        self.samples_to_image = tk.StringVar()
        self.objective_lens = tk.StringVar(value='40x')
        self.macro_dir = tk.StringVar()
        self.image_dir = tk.StringVar()

        # --- Top buttons ---
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(button_frame, text="Add Files", command=self.add_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected).pack(side="left", padx=5)

        # --- Treeview setup ---
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("path","sample")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("path", text="File Path")
        self.tree.heading("sample", text="Samples to Image")
        self.tree.column("path", anchor="w", width=550)
        self.tree.column("sample", anchor="w", width=200)
        self.tree.pack(side='left', fill='both', expand=True)
        
        self.edit_entry = tk.Entry(self.tree)
        self.editing_item = None
        self.editing_column = None
        self.tree.bind("<Double-1>", self.edit_samples_to_image)

        # --- Scrollbar ---
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscroll=scrollbar.set)

        # --- Bind drag and drop events ---
        self.tree.bind("<ButtonPress-1>", self.on_button_press)
        self.tree.bind("<B1-Motion>", self.on_mouse_drag)
        self.tree.bind("<ButtonRelease-1>", self.on_button_release)

        self.drag_data = {"item": None, "y": 0}


        # --- text input frame ---
        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", pady=5, padx=10)

        label = tk.Label(input_frame, text="Number of Z planes:")
        label.grid(row=0, column=0, sticky="w")
        entry = tk.Entry(input_frame, textvariable=self.n_z, width=10)
        entry.grid(row=0, column=1, sticky="w", padx=5)

        label = tk.Label(input_frame, text="Autofocus channel:")
        label.grid(row=0, column=2, sticky="w", padx=(20,0))
        entry = ttk.Combobox(input_frame, textvariable=self.autofocus_channel, values=['DAPI', 'FITC', 'TRITC', 'Cy5'], width=10, state="readonly")
        entry.grid(row=0, column=3, sticky="w", padx=5)

        label = tk.Label(input_frame, text="Objective lens:")
        label.grid(row=1, column=0, sticky="w")
        entry = ttk.Combobox(input_frame, textvariable=self.objective_lens, values=['10x', '20x', '40x', '60x'], width=10, state="readonly")
        entry.grid(row=1, column=1, sticky="w", padx=5)

        ## select output folder
        label = tk.Label(input_frame, text="Macro directory:")
        label.grid(row=2, column=0, sticky="w", pady=5)
        entry = tk.Entry(input_frame, textvariable=self.macro_dir, width=50)
        entry.grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_directory(self.macro_dir)).grid(row=2, column=4, sticky="w", padx=0)
        # button.pack(side="left", padx=5)

        label = tk.Label(input_frame, text="Image directory:")
        label.grid(row=3, column=0, sticky="w", pady=5)
        entry = tk.Entry(input_frame, textvariable=self.image_dir, width=50)
        entry.grid(row=3, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_directory(self.image_dir)).grid(row=3, column=4, sticky="w", padx=0)
        # button.pack(side="left", padx=5)

        # --- run command buttons ---
        run_frame = ttk.Frame(self)
        run_frame.pack(fill="x", pady=5, padx=10)
        ttk.Button(run_frame, text="Generate Tissue Scan Macro", command=self.generate_macro).pack(side="left", padx=5)

    # -------------------------------
    # Functional methods
    # -------------------------------
    def add_files(self):
        """Select and add multiple files."""
        paths = filedialog.askopenfilenames(title="Select Files")
        for path in paths:
            self.tree.insert("", "end", values=(os.path.normpath(path),))

    def remove_selected(self):
        """Delete selected item."""
        for item in self.tree.selection():
            self.tree.delete(item)

    def edit_samples_to_image(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)

        # Only allow editing the "param" column (#2)
        if col != "#2":
            return

        x, y, width, height = self.tree.bbox(row_id, col)
        value = self.tree.set(row_id, col)

        self.editing_item = row_id
        self.editing_column = col

        self.edit_entry.place(x=x, y=y, width=width, height=height)
        self.edit_entry.delete(0, tk.END)
        self.edit_entry.insert(0, value)
        self.edit_entry.focus()

        self.edit_entry.bind("<Return>", self.save_edit)
        # self.edit_entry.after(1, self.save_edit)
        self.edit_entry.bind("<FocusOut>", self.cancel_edit)
    
    def save_edit(self, event=None):    
        if not self.editing_item:
            return  # already saved / closed

        new_value = self.edit_entry.get()
        self.tree.set(self.editing_item, self.editing_column, new_value)

        self.edit_entry.place_forget()
        self.editing_item = None
        self.editing_column = None


    def cancel_edit(self, event):
        self.edit_entry.place_forget()
        self.editing_item = None

    # -------------------------------
    # Drag-and-drop logic
    # -------------------------------
    def on_button_press(self, event):
        """Record item and y-position when click starts."""
        if self.edit_entry.winfo_ismapped():
            return  # Ignore clicks on the entry widget
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_data["item"] = item
            self.drag_data["y"] = event.y

    def on_mouse_drag(self, event):
        """Handle the dragging motion."""
        if self.edit_entry.winfo_ismapped():
            return  # Ignore drags on the entry widget
        item = self.drag_data["item"]
        if not item:
            return

        # Where is the mouse now?
        y = event.y
        if abs(y - self.drag_data["y"]) < 5:
            return  # ignore small moves

        # Determine target row
        target = self.tree.identify_row(y)
        if target and target != item:
            self.tree.move(item, self.tree.parent(target), self.tree.index(target))
            self.drag_data["y"] = y

    def on_button_release(self, event):
        """Clear drag data when released."""
        self.drag_data = {"item": None, "y": 0}
    
    def browse_directory(self, var):
        """Open a directory selection dialog and set the variable."""
        directory = filedialog.askdirectory()
        if directory:
            var.set(os.path.normpath(directory))
    
    def generate_macro(self):
        """Generate the macro based on current settings."""
        # print("Generating tissue scan macro...")
        # print(f"Number of Z planes: {self.n_z.get()}")
        # print(f"Autofocus channel: {self.autofocus_channel.get()}")
        data = [
            {"path": self.tree.set(i, "path"),
            "sample": self.tree.set(i, "sample")}
            for i in self.tree.get_children()
            ]
        sample_names = []
        for item in data:
            sample_names.extend(tissueScanFunctions.generateScanMacroFromFile(item['path'],
                                                          item['sample'],
                                                          self.objective_lens.get(),
                                                          self.n_z.get(),
                                                          self.image_dir.get(),
                                                          self.macro_dir.get(),
                                                          self.autofocus_channel.get()))
        for i in range(1, len(sample_names)):
            tissueScanFunctions.chainingMacro(sample_names[i-1], sample_names[i], self.macro_dir.get())
        messagebox.showinfo("Macros generated", "Start macro by running {}.mac in NIS-Elements".format(sample_names[0]))

class FileTableMultipoint(ttk.Frame):
    """A frame containing a file table with add/remove and drag-drop reorder."""
    def __init__(self, parent):
        super().__init__(parent)
        self.n_z = tk.StringVar(value='75')
        self.autofocus_channel = tk.StringVar(value='DAPI')
        self.samples_to_image = tk.StringVar()
        self.objective_lens = tk.StringVar(value='40x')
        self.macro_dir = tk.StringVar()
        self.image_dir = tk.StringVar()

        # --- Top buttons ---
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(button_frame, text="Add Files", command=self.add_files).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected).pack(side="left", padx=5)

        # --- Treeview setup ---
        columns = ("path",)
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("path", text="File Path")
        self.tree.column("path", anchor="w", width=550)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        

        # --- Scrollbar ---
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscroll=scrollbar.set)

        # --- Bind drag and drop events ---
        self.tree.bind("<ButtonPress-1>", self.on_button_press)
        self.tree.bind("<B1-Motion>", self.on_mouse_drag)
        self.tree.bind("<ButtonRelease-1>", self.on_button_release)

        self.drag_data = {"item": None, "y": 0}

        # --- text input frame ---
        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", pady=5, padx=10)

        label = tk.Label(input_frame, text="Number of Z planes:")
        label.grid(row=0, column=0, sticky="w")
        entry = tk.Entry(input_frame, textvariable=self.n_z, width=10)
        entry.grid(row=0, column=1, sticky="w", padx=5)

        label = tk.Label(input_frame, text="Autofocus channel:")
        label.grid(row=0, column=2, sticky="w", padx=(20,0))
        entry = ttk.Combobox(input_frame, textvariable=self.autofocus_channel, values=['DAPI', 'FITC', 'TRITC', 'Cy5'], width=10, state="readonly")
        entry.grid(row=0, column=3, sticky="w", padx=5)

        label = tk.Label(input_frame, text="Objective lens:")
        label.grid(row=1, column=0, sticky="w")
        entry = ttk.Combobox(input_frame, textvariable=self.objective_lens, values=['10x', '20x', '40x', '60x'], width=10, state="readonly")
        entry.grid(row=1, column=1, sticky="w", padx=5)

        ## select output folder
        label = tk.Label(input_frame, text="Macro directory:")
        label.grid(row=2, column=0, sticky="w", pady=5)
        entry = tk.Entry(input_frame, textvariable=self.macro_dir, width=50)
        entry.grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_directory(self.macro_dir)).grid(row=2, column=4, sticky="w", padx=0)
        # button.pack(side="left", padx=5)

        label = tk.Label(input_frame, text="Image directory:")
        label.grid(row=3, column=0, sticky="w", pady=5)
        entry = tk.Entry(input_frame, textvariable=self.image_dir, width=50)
        entry.grid(row=3, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_directory(self.image_dir)).grid(row=3, column=4, sticky="w", padx=0)
        # button.pack(side="left", padx=5)

        # --- run command buttons ---
        run_frame = ttk.Frame(self)
        run_frame.pack(fill="x", pady=5, padx=10)
        ttk.Button(run_frame, text="Generate Tissue Scan Macro", command=self.generate_macro).pack(side="left", padx=5)


    # -------------------------------
    # Functional methods
    # -------------------------------
    def add_files(self):
        """Select and add multiple files."""
        paths = filedialog.askopenfilenames(title="Select Files")
        for path in paths:
            self.tree.insert("", "end", values=(path,))

    def remove_selected(self):
        """Delete selected item."""
        for item in self.tree.selection():
            self.tree.delete(item)

    # -------------------------------
    # Drag-and-drop logic
    # -------------------------------
    def on_button_press(self, event):
        """Record item and y-position when click starts."""
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_data["item"] = item
            self.drag_data["y"] = event.y

    def on_mouse_drag(self, event):
        """Handle the dragging motion."""
        item = self.drag_data["item"]
        if not item:
            return

        # Where is the mouse now?
        y = event.y
        if abs(y - self.drag_data["y"]) < 5:
            return  # ignore small moves

        # Determine target row
        target = self.tree.identify_row(y)
        if target and target != item:
            self.tree.move(item, self.tree.parent(target), self.tree.index(target))
            self.drag_data["y"] = y

    def on_button_release(self, event):
        """Clear drag data when released."""
        self.drag_data = {"item": None, "y": 0}
    
    def browse_directory(self, var):
        """Open a directory selection dialog and set the variable."""
        directory = filedialog.askdirectory()
        if directory:
            var.set(os.path.normpath(directory))
    
    def generate_macro(self):
        """Generate the macro based on current settings."""
        # print("Generating tissue scan macro...")
        # print(f"Number of Z planes: {self.n_z.get()}")
        # print(f"Autofocus channel: {self.autofocus_channel.get()}")
        data = [
            {"path": self.tree.set(i, "path")}
            for i in self.tree.get_children()
            ]
        sample_names = []
        for item in data:
            sample_names.append(multipointsFunctions.multipointMacroFromFile(item['path'],
                                                          self.objective_lens.get(),
                                                          self.n_z.get(),
                                                          self.image_dir.get(),
                                                          self.macro_dir.get(),
                                                          self.autofocus_channel.get()))
        for i in range(1, len(sample_names)):
            tissueScanFunctions.chainingMacro(sample_names[i-1], sample_names[i], self.macro_dir.get())
        messagebox.showinfo("Macros generated", "Start macro by running {}.mac in NIS-Elements".format(sample_names[0]))

class ImageTransferHandler(FileSystemEventHandler):
    def __init__(self, src_dir, dst_dir, delay=2.0):
        self.src_dir = src_dir
        self.dst_dir = dst_dir
        self.delay = delay
        self.pending = {}
        self.lock = threading.Lock()

    def on_created(self, event):
        if event.is_directory:
            return
        self._flush_pending()
        with self.lock:
            self.pending[event.src_path] = time.time()

    def _flush_pending(self):
        with self.lock:
            to_transfer = {f: t for f, t in self.pending.items()
                           if time.time() - t >= self.delay}
            for filepath in to_transfer:
                self._transfer(filepath)
                del self.pending[filepath]

    def _transfer(self, src_path):
        rel_path = os.path.relpath(src_path, self.src_dir)
        dst_path = os.path.join(self.dst_dir, rel_path)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)
        print(f"Transferred: {rel_path}")

    def flush_all(self):
        with self.lock:
            for filepath in list(self.pending.keys()):
                self._transfer(filepath)
            self.pending.clear()
            
def start_transfer(src_dir, dst_dir):
    for folder in os.listdir(src_dir):
        src_folder = os.path.join(src_dir, folder)
        dst_folder = os.path.join(dst_dir, folder)
        if os.path.isdir(src_folder):
            os.makedirs(dst_folder, exist_ok=True)

    handler = ImageTransferHandler(src_dir, dst_dir, delay=2.0)
    observer = Observer()
    observer.schedule(handler, src_dir, recursive=True)
    observer.start()
    return observer, handler


def stop_transfer(observer, handler):
    time.sleep(2)
    handler.flush_all()
    observer.stop()
    observer.join()

class FileTransfer(ttk.Frame):
    """A frame for file transfer."""
    def __init__(self, parent):
        super().__init__(parent)
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.observer = None
        self.handler = None
        self.thread = None
        self.transfer_active = False

        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", pady=5, padx=10)

        label = tk.Label(input_frame, text="Source directory:")
        label.grid(row=0, column=0, sticky="w")
        entry = tk.Entry(input_frame, textvariable=self.src_dir, width=50)
        entry.grid(row=0, column=1, sticky="w", padx=5)

        label = tk.Label(input_frame, text="Destination directory:")
        label.grid(row=1, column=0, sticky="w")
        entry = tk.Entry(input_frame, textvariable=self.dst_dir, width=50)
        entry.grid(row=1, column=1, sticky="w", padx=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_directory(self.src_dir)).grid(row=0, column=2, sticky="w", padx=0)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_directory(self.dst_dir)).grid(row=1, column=2, sticky="w", padx=0)

        run_frame = ttk.Frame(self)
        run_frame.pack(fill="x", pady=5, padx=10)
        ttk.Button(run_frame, text="Start Transfer", command=self.start_transfer).pack(side="left", padx=5)
        ttk.Button(run_frame, text="Stop Transfer", command=self.stop_transfer).pack(side="left", padx=5)

        self.status_label = tk.Label(run_frame, text='Status: Idle', fg='gray')
        self.status_label.pack(side="left", padx=20)

    def browse_directory(self, var):
        """Open a directory selection dialog and set the variable."""
        directory = filedialog.askdirectory()
        if directory:
            var.set(os.path.normpath(directory))

    def start_transfer(self):
        src = self.src_dir.get()
        dst = self.dst_dir.get()

        if not src or not dst:
            messagebox.showwarning("Missing Input", "Please select both source and destination directories.")
            return
        if self.transfer_active:
            messagebox.showinfo("Already Running", "Transfer is already running.")
            return

        self.transfer_active = True
        self.status_label.config(text="Status: Running", fg="green")

        def run():
            self.observer, self.handler = start_transfer(src, dst)
            self.observer.join()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop_transfer(self):
        if not self.transfer_active:
            messagebox.showinfo("Not Running", "No transfer is currently running.")
            return

        def run_stop():
            stop_transfer(self.observer, self.handler)
            self.transfer_active = False
            self.after(0, lambda: self.status_label.config(text="Status: Idle", fg="gray"))  # ADDED: update GUI safely from thread

        threading.Thread(target=run_stop, daemon=True).start()



class PauseContinue(ttk.Frame):
    """A frame for pause and continue functionality."""
    def __init__(self, parent):
        super().__init__(parent)
        self.alignment_fov = tk.StringVar()
        self.last_fov = tk.StringVar()
        self.macro_dir = tk.StringVar()

        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", pady=5, padx=10)

        label = tk.Label(input_frame, text="FOV to align to:")
        label.grid(row=0, column=0, sticky="w")
        entry = tk.Entry(input_frame, textvariable=self.alignment_fov, width=10)
        entry.grid(row=0, column=1, sticky="w", padx=5)

        label = tk.Label(input_frame, text="Last imaged FOV:")
        label.grid(row=1, column=0, sticky="w")
        entry = tk.Entry(input_frame, textvariable=self.last_fov, width=10)
        entry.grid(row=1, column=1, sticky="w", padx=5)

        label = tk.Label(input_frame, text="Macro directory:")
        label.grid(row=2, column=0, sticky="w", pady=5)
        entry = tk.Entry(input_frame, textvariable=self.macro_dir, width=50)
        entry.grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_file(self.macro_dir)).grid(row=2, column=4, sticky="w", padx=0)

        run_frame = ttk.Frame(self)
        run_frame.pack(fill="x", pady=5, padx=10)
        ttk.Button(run_frame, text="Generate Continuous Scan Macro", command=self.generate_macro).pack(side="left", padx=5)
    
    def browse_file(self, var):
        """Open a file selection dialog and set the variable."""
        file = filedialog.askopenfilename()
        if file:
            var.set(os.path.normpath(file))

    def generate_macro(self):
        continuingFunctions.moveToAlign(self.macro_dir.get(), self.alignment_fov.get().zfill(3))
        continuingFunctions.continueMacro(self.macro_dir.get(), self.alignment_fov.get().zfill(3), self.last_fov.get().zfill(3))
        current_macro_name = os.path.basename(self.macro_dir.get()).split('.')[0]
        messagebox.showinfo("Macros generated", "Run {}_move_to_align.mac in NIS-Elements, and move microscope stage to align to FOV {}.\ Then continue imaging by running {}.mac".format(current_macro_name, self.alignment_fov.get().zfill(3), current_macro_name))

# ===========================================================
# Main App
# ==========================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nikon Ti2 Imaging Macro")
        # self.geometry("650x40")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # --- Tab 1: Tissue ---
        tissue = FileTableTissue(notebook)
        notebook.add(tissue, text="Tissue Scan")

        # --- Tab 2: Multipoint ---
        # multipoint = ttk.Frame(notebook)
        multipoint = FileTableMultipoint(notebook)
        notebook.add(multipoint, text="Multipoint Scan")

        # --- Tab 3: File transfer ---
        transfer = FileTransfer(notebook)
        notebook.add(transfer, text="File Transfer")

        # --- Tab 4: Pause and continue ---
        pause_continue = PauseContinue(notebook)
        notebook.add(pause_continue, text="Pause and Continue")

if __name__ == "__main__":
    app = App()
    app.mainloop()
