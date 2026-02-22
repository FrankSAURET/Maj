import tkinter as tk
import time

class AdvancedTooltip:
    """
    Tooltip avancé avec :
    - arrondis
    - ombre portée
    - flèche triangulaire
    - délai d’apparition
    - positionnement intelligent
    - style configurable
    """

    def __init__(
        self,
        widget,
        text,
        delay=400,
        bg="#f8fcf9",
        fg="#145a32",
        border="#b7e1cd",
        font=("Segoe UI", 10),
        padding=8,
        corner_radius=8,
        arrow_size=8,
        max_width=300
    ):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.bg = bg
        self.fg = fg
        self.border = border
        self.font = font
        self.padding = padding
        self.corner_radius = corner_radius
        self.arrow_size = arrow_size
        self.max_width = max_width

        self.tip = None
        self._after_id = None

        widget.bind("<Enter>", self._schedule_show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    # ---------------------------------------------------------
    # Gestion du délai
    # ---------------------------------------------------------
    def _schedule_show(self, event=None):
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel_schedule(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    # ---------------------------------------------------------
    # Affichage de la bulle
    # ---------------------------------------------------------
    def _show(self, event=None):
        if self.tip:
            return

        # Création de la fenêtre
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.attributes("-topmost", True)

        # Positionnement
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tip.geometry(f"+{x}+{y}")

        # Canvas pour arrondis + ombre + flèche
        canvas = tk.Canvas(
            self.tip,
            bg="",
            highlightthickness=0,
            bd=0
        )
        canvas.pack()

        # Taille du texte
        tmp = tk.Label(canvas, text=self.text, font=self.font, wraplength=self.max_width)
        tmp.update_idletasks()
        text_w = tmp.winfo_width()
        text_h = tmp.winfo_height()

        w = text_w + self.padding * 2
        h = text_h + self.padding * 2
        r = self.corner_radius
        a = self.arrow_size

        # Ombre portée
        canvas.create_rectangle(
            5, 5, w + 5, h + a + 5,
            fill="#00000022",
            outline=""
        )

        # Fond arrondi
        self._rounded_rect(canvas, 0, 0, w, h, r, fill=self.bg, outline=self.border)

        # Flèche
        canvas.create_polygon(
            w//2 - a, h,
            w//2 + a, h,
            w//2, h + a,
            fill=self.bg,
            outline=self.border
        )

        # Texte
        canvas.create_text(
            w//2,
            h//2,
            text=self.text,
            fill=self.fg,
            font=self.font,
            width=self.max_width
        )

    # ---------------------------------------------------------
    # Masquage
    # ---------------------------------------------------------
    def _hide(self, event=None):
        self._cancel_schedule()
        if self.tip:
            self.tip.destroy()
            self.tip = None

