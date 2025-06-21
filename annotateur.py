
import tkinter as tk
from tkinter import filedialog, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont

class ImageAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Annotateur d'image")

        self.image = None
        self.draw = None
        self.photo = None
        self.canvas_image = None
        self.rect_start = None
        self.arrow_start = None
        self.mode = "rectangle"
        self.color = "#FF0000"
        self.stroke_width = 3

        self.zoom_factor = 1.0
        self.min_zoom = 0.2
        self.max_zoom = 5.0
        self.offset_x = 0
        self.offset_y = 0
        self.pan_start = None

        self.history = []
        self.redo_stack = []

        self.create_widgets()

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="gray")
        self.canvas.pack(fill="both", expand=True)

        frame = tk.Frame(self.root)
        frame.pack()

        tk.Button(frame, text="Charger image", command=self.load_image).pack(side="left")
        tk.Button(frame, text="Rectangle", command=lambda: self.set_mode("rectangle")).pack(side="left")
        tk.Button(frame, text="Flèche", command=lambda: self.set_mode("arrow")).pack(side="left")
        tk.Button(frame, text="Texte", command=lambda: self.set_mode("text")).pack(side="left")

        self.color_button = tk.Button(frame, command=self.choose_color)
        self.update_color_button()
        self.color_button.pack(side="left")

        tk.Label(frame, text="Taille :").pack(side="left", padx=(10, 0))
        self.thickness_spin = tk.Spinbox(frame, from_=1, to=50, width=3, command=self.update_thickness)
        self.thickness_spin.pack(side="left")
        self.thickness_spin.delete(0, "end")
        self.thickness_spin.insert(0, str(self.stroke_width))

        tk.Button(frame, text="Sauvegarder", command=self.save_image).pack(side="left")

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom_linux)
        self.canvas.bind("<Button-5>", self.on_zoom_linux)
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)

        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-y>", self.redo)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            self.image = Image.open(file_path).convert("RGB")
            self.draw = ImageDraw.Draw(self.image)
            self.zoom_factor = 1.0
            self.offset_x = 0
            self.offset_y = 0
            self.history.clear()
            self.redo_stack.clear()
            self.display_image()

    def display_image(self):
        if not self.image:
            return
        w, h = self.image.size
        zoomed = self.image.resize((int(w * self.zoom_factor), int(h * self.zoom_factor)), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(zoomed)
        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.photo)

    def set_mode(self, mode):
        self.mode = mode

    def choose_color(self):
        color = colorchooser.askcolor(title="Choisir une couleur")
        if color[1]:
            self.color = color[1]
            self.update_color_button()

    def update_color_button(self):
        for widget in self.color_button.winfo_children():
            widget.destroy()
        tk.Label(self.color_button, text="Choisir couleur").pack(side="left")
        color_preview = tk.Canvas(self.color_button, width=20, height=20, bg=self.color, highlightthickness=1, highlightbackground="black")
        color_preview.pack(side="right", padx=5)

    def update_thickness(self):
        try:
            self.stroke_width = int(self.thickness_spin.get())
        except ValueError:
            self.stroke_width = 3

    def to_image_coords(self, x, y):
        ix = (x - self.offset_x) / self.zoom_factor
        iy = (y - self.offset_y) / self.zoom_factor
        return int(ix), int(iy)

    def on_mouse_down(self, event):
        if self.image:
            self.update_thickness()
            coords = self.to_image_coords(event.x, event.y)
            if self.mode == "rectangle":
                self.rect_start = coords
            elif self.mode == "arrow":
                self.arrow_start = coords
            elif self.mode == "text":
                self.save_state()
                self.add_text(coords)

    def on_mouse_up(self, event):
        if self.image and self.mode != "text":
            end = self.to_image_coords(event.x, event.y)
            self.save_state()
            if self.mode == "rectangle" and self.rect_start:
                x0, y0 = self.rect_start
                x1, y1 = end
                x_min, y_min = min(x0, x1), min(y0, y1)
                x_max, y_max = max(x0, x1), max(y0, y1)
                self.draw.rectangle([(x_min, y_min), (x_max, y_max)], outline=self.color, width=self.stroke_width)
            elif self.mode == "arrow" and self.arrow_start:
                self.draw_arrow_head(self.arrow_start, end)
            self.display_image()

    def add_text(self, coords):
        text = simpledialog.askstring("Ajouter texte", "Entrer le texte :")
        if text:
            try:
                font = ImageFont.truetype("arial.ttf", self.stroke_width * 4)
            except:
                font = ImageFont.load_default()
            self.draw.text(coords, text, fill=self.color, font=font)
            self.display_image()

    def draw_arrow_head(self, start, end):
        from math import atan2, sin, cos, radians

        size = max(10, min(30, self.stroke_width * 3))
        angle_deg = 30

        angle = atan2(end[1] - start[1], end[0] - start[0])
        offset_x = size * cos(angle)
        offset_y = size * sin(angle)
        base_x = end[0] - offset_x
        base_y = end[1] - offset_y

        self.draw.line([start, (base_x, base_y)], fill=self.color, width=self.stroke_width)

        angle1 = angle + radians(angle_deg)
        angle2 = angle - radians(angle_deg)

        x1 = end[0] - size * cos(angle1)
        y1 = end[1] - size * sin(angle1)
        x2 = end[0] - size * cos(angle2)
        y2 = end[1] - size * sin(angle2)

        self.draw.polygon([end, (x1, y1), (x2, y2)], fill=self.color)

    def save_image(self):
        if self.image:
            file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if file_path:
                self.image.save(file_path)

    def save_state(self):
        if self.image:
            self.history.append(self.image.copy())
            self.redo_stack.clear()
            if len(self.history) > 20:
                self.history.pop(0)

    def undo(self, event=None):
        if self.history:
            self.redo_stack.append(self.image.copy())
            self.image = self.history.pop()
            self.draw = ImageDraw.Draw(self.image)
            self.display_image()

    def redo(self, event=None):
        if self.redo_stack:
            self.history.append(self.image.copy())
            self.image = self.redo_stack.pop()
            self.draw = ImageDraw.Draw(self.image)
            self.display_image()

    def on_zoom(self, event):
        scale = 1.1 if event.delta > 0 else 0.9
        self.apply_zoom(scale, event.x, event.y)

    def on_zoom_linux(self, event):
        scale = 1.1 if event.num == 4 else 0.9
        self.apply_zoom(scale, event.x, event.y)

    def apply_zoom(self, scale, center_x, center_y):
        new_zoom = self.zoom_factor * scale
        if self.min_zoom <= new_zoom <= self.max_zoom:
            dx = center_x - self.offset_x
            dy = center_y - self.offset_y
            self.offset_x = center_x - dx * scale
            self.offset_y = center_y - dy * scale
            self.zoom_factor = new_zoom
            self.display_image()

    def start_pan(self, event):
        self.pan_start = (event.x, event.y)

    def do_pan(self, event):
        if self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.offset_x += dx
            self.offset_y += dy
            self.pan_start = (event.x, event.y)
            self.display_image()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageAnnotator(root)
    root.mainloop()
