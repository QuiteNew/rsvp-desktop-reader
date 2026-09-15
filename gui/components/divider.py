import customtkinter as ctk
from gui.theme import WARM_LINE


class Divider(ctk.CTkFrame):
    """A resize handle: a thin visible line sitting inside a much larger
    invisible band that actually receives hover/click/drag events. A
    purely 2px-thick clickable target proved unreliable to grab in
    practice — this keeps the same thin visual line but gives the mouse
    a genuinely generous area to land on, the pattern most real desktop
    apps use for thin draggable dividers.

    When enabled, hovering anywhere in the band shows a resize cursor,
    and dragging reports the cumulative pixel offset from where the drag
    began via on_drag — measured from the original press point every
    time, not incrementally, so the caller can always compute a fresh
    target size as (size_at_drag_start + delta) without drift building up.
    """

    LINE_THICKNESS = 2
    HIT_THICKNESS = 10  # the real clickable size — much larger than the visible line

    def __init__(self, master, orientation: str = "horizontal", on_drag_start=None, on_drag=None, on_drag_end=None):
        size_kwargs = {"height": self.HIT_THICKNESS} if orientation == "horizontal" else {"width": self.HIT_THICKNESS}
        super().__init__(master, fg_color="transparent", corner_radius=0, **size_kwargs)
        self.orientation = orientation
        self.on_drag_start = on_drag_start
        self.on_drag = on_drag
        self.on_drag_end = on_drag_end
        self._enabled = False
        self._drag_origin = None

        if orientation == "horizontal":
            self.line = ctk.CTkFrame(self, fg_color=WARM_LINE, corner_radius=0, height=self.LINE_THICKNESS)
            self.line.place(relx=0, rely=0.5, relwidth=1.0, anchor="w")
        else:
            self.line = ctk.CTkFrame(self, fg_color=WARM_LINE, corner_radius=0, width=self.LINE_THICKNESS)
            self.line.place(relx=0.5, rely=0, relheight=1.0, anchor="n")

        # Bound to self — the full, larger band — not the thin line itself,
        # so the whole band is clickable/hoverable, not just its center.
        self.bind("<Enter>", self._handle_enter)
        self.bind("<Leave>", self._handle_leave)
        self.bind("<ButtonPress-1>", self._handle_press)
        self.bind("<B1-Motion>", self._handle_motion)
        self.bind("<ButtonRelease-1>", self._handle_release)

    def set_resizable(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self.configure(cursor="")

    def _resize_cursor(self) -> str:
        return "sb_h_double_arrow" if self.orientation == "vertical" else "sb_v_double_arrow"

    def _handle_enter(self, event) -> None:
        if self._enabled:
            self.configure(cursor=self._resize_cursor())

    def _handle_leave(self, event) -> None:
        if self._enabled and self._drag_origin is None:
            self.configure(cursor="")

    def _handle_press(self, event) -> None:
        if not self._enabled:
            return
        self._drag_origin = (event.x_root, event.y_root)
        if self.on_drag_start:
            self.on_drag_start()

    def _handle_motion(self, event) -> None:
        if not self._enabled or self._drag_origin is None:
            return
        origin_x, origin_y = self._drag_origin
        delta = (event.x_root - origin_x) if self.orientation == "vertical" else (event.y_root - origin_y)
        if self.on_drag:
            self.on_drag(delta)

    def _handle_release(self, event) -> None:
        if not self._enabled or self._drag_origin is None:
            return
        self._drag_origin = None
        self.configure(cursor=self._resize_cursor())
        if self.on_drag_end:
            self.on_drag_end()