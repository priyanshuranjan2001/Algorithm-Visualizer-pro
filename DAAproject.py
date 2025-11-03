"""
Algorithm Visualizer Pro
A self-contained Python/Tkinter application to visualize algorithms (sorting + backtracking subset-sum).
Features:
- Visualize Bubble, Selection, Insertion, Merge, Quick sort with animations
- Visualize Subset Sum backtracking (show included/excluded elements)
- Controls: Start, Pause, Step, Reset, Randomize, Speed slider, Array size
- Pseudocode panel with line highlighting
- Export current frame as PNG

Run: python Algorithm_Visualizer_Pro.py
Requires: Python 3.8+, Tkinter (usually included), Pillow (optional, only for exporting screenshots)

"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import time
import math
import sys

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

def bubble_sort_generator(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            # compare
            yield {"type": "compare", "indices": (j, j+1)}
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
                yield {"type": "swap", "indices": (j, j+1), "array": arr.copy()}
    yield {"type": "done", "array": arr.copy()}


def selection_sort_generator(arr):
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i+1, n):
            yield {"type": "compare", "indices": (min_idx, j)}
            if arr[j] < arr[min_idx]:
                min_idx = j
                yield {"type": "highlight", "indices": (min_idx,)}
        if min_idx != i:
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
            yield {"type": "swap", "indices": (i, min_idx), "array": arr.copy()}
    yield {"type": "done", "array": arr.copy()}


def insertion_sort_generator(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        yield {"type": "highlight", "indices": (i,)}
        while j >= 0 and arr[j] > key:
            yield {"type": "compare", "indices": (j, j+1)}
            arr[j+1] = arr[j]
            j -= 1
            yield {"type": "shift", "indices": (j+1, j+2), "array": arr.copy()}
        arr[j+1] = key
        yield {"type": "insert", "index": j+1, "array": arr.copy()}
    yield {"type": "done", "array": arr.copy()}


def merge_sort_generator(arr):
    # We'll implement merge sort using an explicit stack to yield merge steps
    aux = arr.copy()
    n = len(arr)

    def merge_range(l, m, r):
        i, j, k = l, m, l
        while i < m and j < r:
            yield {"type": "compare", "indices": (i, j)}
            if aux[i] <= aux[j]:
                arr[k] = aux[i]
                i += 1
            else:
                arr[k] = aux[j]
                j += 1
            k += 1
            yield {"type": "mergewrite", "index": k-1, "value": arr[k-1], "array": arr.copy()}
        while i < m:
            arr[k] = aux[i]
            i += 1; k += 1
            yield {"type": "mergewrite", "index": k-1, "value": arr[k-1], "array": arr.copy()}
        while j < r:
            arr[k] = aux[j]
            j += 1; k += 1
            yield {"type": "mergewrite", "index": k-1, "value": arr[k-1], "array": arr.copy()}

    # bottom-up merge sort
    width = 1
    while width < n:
        for i in range(0, n, 2*width):
            l = i
            m = min(i+width, n)
            r = min(i+2*width, n)
            # copy to aux
            for k in range(l, r):
                aux[k] = arr[k]
            for step in merge_range(l, m, r):
                yield step
        width *= 2
    yield {"type": "done", "array": arr.copy()}


def quick_sort_generator(arr):
    # iterative quicksort using stack, with Lomuto partition, yield swaps and compares
    stack = [(0, len(arr)-1)]
    while stack:
        low, high = stack.pop()
        if low < high:
            pivot = arr[high]
            i = low
            for j in range(low, high):
                yield {"type": "compare", "indices": (j, high)}
                if arr[j] < pivot:
                    arr[i], arr[j] = arr[j], arr[i]
                    yield {"type": "swap", "indices": (i, j), "array": arr.copy()}
                    i += 1
            arr[i], arr[high] = arr[high], arr[i]
            yield {"type": "swap", "indices": (i, high), "array": arr.copy()}
            p = i
            stack.append((low, p-1))
            stack.append((p+1, high))
    yield {"type": "done", "array": arr.copy()}

def subset_sum_generator(arr, target):
    n = len(arr)
    chosen = [False]*n

    def backtrack(i, current_sum):
        if i == n:
            # yield a check
            yield {"type": "check", "chosen": chosen.copy(), "sum": current_sum}
            return
        # exclude
        chosen[i] = False
        yield {"type": "decide", "index": i, "choice": False, "chosen": chosen.copy(), "sum": current_sum}
        for step in backtrack(i+1, current_sum):
            yield step
        # include
        chosen[i] = True
        yield {"type": "decide", "index": i, "choice": True, "chosen": chosen.copy(), "sum": current_sum + arr[i]}
        for step in backtrack(i+1, current_sum + arr[i]):
            yield step
        chosen[i] = False

    for step in backtrack(0, 0):
        # if we hit a full assignment that equals target, yield a solution marker
        if step.get("type") == "check" and step.get("sum") == target:
            step["type"] = "solution"
            yield step
        else:
            yield step
    yield {"type": "done"}

# -----------------------------------------------------------------------------------
# Visualizer App

class AlgorithmVisualizerPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Algorithm Visualizer Pro")
        self.geometry("1100x700")
        self.configure(bg="#f4f7fb")

        self._build_ui()
        self.running = False
        self.generator = None
        self.current_operation = None
        self.after_id = None

    def _build_ui(self):
        control_frame = ttk.Frame(self)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=6)

        # Algorithm selection
        ttk.Label(control_frame, text="Algorithm:").pack(side=tk.LEFT)
        self.algo_var = tk.StringVar(value="Bubble Sort")
        algo_menu = ttk.OptionMenu(control_frame, self.algo_var, "Bubble Sort",
                                    "Bubble Sort", "Selection Sort", "Insertion Sort", "Merge Sort", "Quick Sort", "Subset Sum")
        algo_menu.pack(side=tk.LEFT, padx=6)

        # Array size
        ttk.Label(control_frame, text="Array size:").pack(side=tk.LEFT, padx=(12,0))
        self.size_var = tk.IntVar(value=30)
        size_spin = ttk.Spinbox(control_frame, from_=5, to=120, textvariable=self.size_var, width=5)
        size_spin.pack(side=tk.LEFT, padx=4)

        # Speed slider
        ttk.Label(control_frame, text="Speed:").pack(side=tk.LEFT, padx=(12,0))
        self.speed_var = tk.DoubleVar(value=50.0)
        speed_slider = ttk.Scale(control_frame, from_=1, to=200, variable=self.speed_var, orient=tk.HORIZONTAL)
        speed_slider.pack(side=tk.LEFT, padx=4)

        # Target for subset sum
        ttk.Label(control_frame, text="Target (for Subset Sum):").pack(side=tk.LEFT, padx=(12,0))
        self.target_var = tk.IntVar(value=10)
        target_entry = ttk.Entry(control_frame, textvariable=self.target_var, width=6)
        target_entry.pack(side=tk.LEFT, padx=4)

        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.RIGHT)
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.pause_btn = ttk.Button(btn_frame, text="Pause", command=self.pause)
        self.pause_btn.pack(side=tk.LEFT, padx=4)
        self.step_btn = ttk.Button(btn_frame, text="Step", command=self.step)
        self.step_btn.pack(side=tk.LEFT, padx=4)
        self.reset_btn = ttk.Button(btn_frame, text="Reset", command=self.reset)
        self.reset_btn.pack(side=tk.LEFT, padx=4)

        random_btn = ttk.Button(control_frame, text="Randomize", command=self.randomize)
        random_btn.pack(side=tk.LEFT, padx=6)

        export_btn = ttk.Button(control_frame, text="Export PNG", command=self.export_png)
        export_btn.pack(side=tk.LEFT, padx=6)

        # Main canvas and side panels
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        # Canvas
        self.canvas = tk.Canvas(main_frame, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right panel
        right_panel = ttk.Frame(main_frame, width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)

        # Pseudocode box
        ttk.Label(right_panel, text="Pseudocode / Info:").pack(anchor=tk.NW, pady=(4,0))
        self.code_text = tk.Text(right_panel, width=40, height=25, wrap=tk.NONE)
        self.code_text.pack(fill=tk.Y, padx=4, pady=4)
        self.code_text.configure(state=tk.DISABLED)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(right_panel, textvariable=self.status_var).pack(anchor=tk.SW, pady=(10,0))

        # Initialize array and draw
        self.array = [random.randint(5, 400) for _ in range(self.size_var.get())]
        self.rects = []
        self.draw_array()

        # Bind resizing
        self.bind('<Configure>', self._on_resize)

    def _on_resize(self, event):
        # redraw on resize
        if event.widget == self:
            self.draw_array()

    def draw_array(self, highlight_indices=(), colors=None):
        self.canvas.delete('all')
        w = max(200, self.canvas.winfo_width())
        h = max(200, self.canvas.winfo_height())
        n = len(self.array)
        if n == 0:
            return
        bar_width = w / n
        max_val = max(self.array)
        self.rects = []
        for i, val in enumerate(self.array):
            x0 = i*bar_width
            x1 = (i+1)*bar_width - 1
            bar_h = (val / max_val) * (h - 20)
            y0 = h - bar_h
            y1 = h
            color = 'steelblue'
            if colors and i < len(colors) and colors[i]:
                color = colors[i]
            elif i in highlight_indices:
                color = 'orange'
            rect = self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline='')
            # small label for large arrays would clutter; we only add for small arrays
            if n <= 30:
                self.canvas.create_text((x0+x1)/2, y0-8, text=str(val), anchor=tk.S)
            self.rects.append(rect)

    def randomize(self):
        size = max(2, min(200, self.size_var.get()))
        self.array = [random.randint(5, 400) for _ in range(size)]
        self.draw_array()
        self.status_var.set('Randomized array of size {}'.format(size))

    def start(self):
        if self.running:
            return
        alg = self.algo_var.get()
        self.running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.pause_btn.configure(state=tk.NORMAL)
        self.step_btn.configure(state=tk.NORMAL)
        self.status_var.set(f'Running {alg}...')

        # prepare generator
        arr_copy = self.array.copy()
        if alg == 'Bubble Sort':
            self.generator = bubble_sort_generator(arr_copy)
            self._set_pseudocode('bubble')
        elif alg == 'Selection Sort':
            self.generator = selection_sort_generator(arr_copy)
            self._set_pseudocode('selection')
        elif alg == 'Insertion Sort':
            self.generator = insertion_sort_generator(arr_copy)
            self._set_pseudocode('insertion')
        elif alg == 'Merge Sort':
            self.generator = merge_sort_generator(arr_copy)
            self._set_pseudocode('merge')
        elif alg == 'Quick Sort':
            self.generator = quick_sort_generator(arr_copy)
            self._set_pseudocode('quick')
        elif alg == 'Subset Sum':
            target = self.target_var.get()
            self.generator = subset_sum_generator(arr_copy, target)
            self._set_pseudocode('subset')
        else:
            messagebox.showerror('Algorithm Visualizer', 'Unknown algorithm: ' + alg)
            self.running = False
            return

        # kick off the animation loop
        self._run_step()

    def _run_step(self):
        if not self.running or self.generator is None:
            return
        try:
            op = next(self.generator)
            self.current_operation = op
            self._apply_operation(op)
            delay = int(max(1, 300 - self.speed_var.get()))
            self.after_id = self.after(delay, self._run_step)
        except StopIteration:
            self.running = False
            self.start_btn.configure(state=tk.NORMAL)
            self.status_var.set('Finished')
            self.generator = None
            self.current_operation = None

    def pause(self):
        if not self.running:
            return
        self.running = False
        if self.after_id:
            try:
                self.after_cancel(self.after_id)
            except Exception:
                pass
        self.start_btn.configure(state=tk.NORMAL)
        self.status_var.set('Paused')

    def step(self):
        if self.running:
            # if running, pause first
            self.pause()
        if self.generator is None:
            # if no generator, prepare one
            alg = self.algo_var.get()
            arr_copy = self.array.copy()
            if alg == 'Bubble Sort':
                self.generator = bubble_sort_generator(arr_copy)
                self._set_pseudocode('bubble')
            elif alg == 'Selection Sort':
                self.generator = selection_sort_generator(arr_copy)
                self._set_pseudocode('selection')
            elif alg == 'Insertion Sort':
                self.generator = insertion_sort_generator(arr_copy)
                self._set_pseudocode('insertion')
            elif alg == 'Merge Sort':
                self.generator = merge_sort_generator(arr_copy)
                self._set_pseudocode('merge')
            elif alg == 'Quick Sort':
                self.generator = quick_sort_generator(arr_copy)
                self._set_pseudocode('quick')
            elif alg == 'Subset Sum':
                target = self.target_var.get()
                self.generator = subset_sum_generator(arr_copy, target)
                self._set_pseudocode('subset')
            else:
                messagebox.showerror('Algorithm Visualizer', 'Unknown algorithm: ' + alg)
                return
        try:
            op = next(self.generator)
            self.current_operation = op
            self._apply_operation(op)
        except StopIteration:
            self.generator = None
            self.status_var.set('Finished')

    def reset(self):
        if self.running:
            self.pause()
        self.generator = None
        self.current_operation = None
        self.array = [random.randint(5, 400) for _ in range(max(5, min(200, self.size_var.get())))]
        self.draw_array()
        self.status_var.set('Reset')

    def _apply_operation(self, op):
        t = op.get('type')
        if t == 'compare':
            i,j = op['indices']
            colors = [None]*len(self.array)
            if i < len(colors): colors[i] = 'orange'
            if j < len(colors): colors[j] = 'orange'
            self.draw_array(highlight_indices=(), colors=colors)
            self._highlight_code_line(1)
            self.status_var.set(f'Comparing indices {i} and {j}')
        elif t == 'swap':
            self.array = op.get('array', self.array)
            i,j = op['indices']
            colors = ['lightgreen']*len(self.array)
            if i < len(colors): colors[i] = 'red'
            if j < len(colors): colors[j] = 'red'
            self.draw_array(colors=colors)
            self._highlight_code_line(2)
            self.status_var.set(f'Swapped indices {i} and {j}')
        elif t == 'shift':
            self.array = op.get('array', self.array)
            self.draw_array()
            self._highlight_code_line(3)
            self.status_var.set('Shifting elements')
        elif t == 'insert':
            self.array = op.get('array', self.array)
            self.draw_array()
            self._highlight_code_line(4)
            self.status_var.set(f'Inserted at index {op.get("index")}')
        elif t == 'mergewrite':
            self.array = op.get('array', self.array)
            self.draw_array()
            self._highlight_code_line(5)
            self.status_var.set(f'Writing merged value at index {op.get("index")}')
        elif t == 'highlight':
            indices = op.get('indices', ())
            self.draw_array(highlight_indices=indices)
            self.status_var.set(f'Highlight index {indices}')
        elif t == 'decide':
            chosen = op.get('chosen', [])
            colors = []
            for c in chosen:
                colors.append('lightgreen' if c else None)
            self.draw_array(colors=colors)
            idx = op.get('index')
            choice = op.get('choice')
            self.status_var.set(f'Index {idx} -> {"Include" if choice else "Exclude"}')
            self._highlight_code_line(6)
        elif t == 'check':
            chosen = op.get('chosen', [])
            s = op.get('sum', 0)
            colors = ['lightgreen' if c else None for c in chosen]
            self.draw_array(colors=colors)
            self.status_var.set(f'Checked sum = {s}')
        elif t == 'solution':
            chosen = op.get('chosen', [])
            s = op.get('sum', 0)
            colors = ['gold' if c else None for c in chosen]
            self.draw_array(colors=colors)
            self.status_var.set(f'Solution! sum={s}')
            self._highlight_code_line(7)
        elif t == 'done':
            self.array = op.get('array', self.array)
            self.draw_array()
            self.status_var.set('Done')
            self._highlight_code_line(0)
        else:
            self.status_var.set(str(op))

    # Pseudocode handling
    PSEUDOCODES = {
        'bubble': [
            'for i from 0 to n-1:',
            '  for j from 0 to n-i-2:',
            '    if A[j] > A[j+1]:',
            '      swap(A[j], A[j+1])'
        ],
        'selection': [
            'for i from 0 to n-1:',
            '  min_idx = i',
            '  for j from i+1 to n-1:',
            '    if A[j] < A[min_idx]:',
            '      min_idx = j',
            '  swap(A[i], A[min_idx])'
        ],
        'insertion': [
            'for i from 1 to n-1:',
            '  key = A[i]',
            '  j = i-1',
            '  while j>=0 and A[j] > key:',
            '    A[j+1] = A[j]',
            '    j = j-1',
            '  A[j+1] = key'
        ],
        'merge': [
            'width = 1',
            'while width < n:',
            '  for i in range(0, n, 2*width):',
            '    merge subarrays A[i:i+width] and A[i+width:i+2*width]',
            '  width *= 2'
        ],
        'quick': [
            'use a stack of ranges',
            'pop range (low, high)',
            'partition with pivot = A[high]',
            'push subranges (low, p-1) and (p+1, high)'
        ],
        'subset': [
            'def backtrack(i, sum):',
            '  if i==n: check sum',
            '  choose exclude i, backtrack(i+1, sum)',
            '  choose include i, backtrack(i+1, sum+arr[i])'
        ]
    }

    def _set_pseudocode(self, key):
        code = self.PSEUDOCODES.get(key, [])
        self.code_text.configure(state=tk.NORMAL)
        self.code_text.delete('1.0', tk.END)
        for line in code:
            self.code_text.insert(tk.END, line + "\n")
        self.code_text.configure(state=tk.DISABLED)

    def _highlight_code_line(self, lineno):
        # lineno: 0 means clear, else highlight 1-indexed line
        self.code_text.configure(state=tk.NORMAL)
        self.code_text.tag_remove('hl', '1.0', tk.END)
        if lineno > 0:
            start = f"{lineno}.0"
            end = f"{lineno}.end"
            self.code_text.tag_add('hl', start, end)
            self.code_text.tag_config('hl', background='yellow')
        self.code_text.configure(state=tk.DISABLED)

    def export_png(self):
        if not PIL_AVAILABLE:
            messagebox.showwarning('Export PNG', 'Pillow not available. Install pillow to enable export (pip install pillow)')
            return
        # get file
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG Image','*.png')])
        if not path:
            return
        # use ImageGrab to capture window area
        x = self.winfo_rootx()
        y = self.winfo_rooty()
        w = x + self.winfo_width()
        h = y + self.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, w, h))
        img.save(path)
        messagebox.showinfo('Export PNG', f'Exported screenshot to {path}')


if __name__ == '__main__':
    app = AlgorithmVisualizerPro()
    app.mainloop()
