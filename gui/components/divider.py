import customtkinter as ctk


class Divider(ctk.CTkFrame):
    """A thin line separating two sections. Can double as a draggable
    resize handle: when enabled, hovering shows a resize cursor, and
    dragging reports the cumulative pixel offset from where the drag
    began via on_drag — measured from the original press point every
    time, not incrementally, so the caller can always compute a fresh
    target size as (size_at_drag_start + delta) without drift building up.
    on_drag_start fires once when a drag begins (record the current size);
    on_drag_end fires once when it finishes (persist the final size,
    rather than saving on every pixel of movement).
    """

    COLOR = "#000000"
    THICKNESS = 2

    def __init__(self, master, orientation: str = "horizontal", on_drag_start=None, on_drag=None, on_drag_end=None):
        size_kwargs = {"height": self.THICKNESS} if orientation == "horizontal" else {"width": self.THICKNESS}
        super().__init__(master, fg_color=self.COLOR, corner_radius=0, **size_kwargs)
        self.orientation = orientation
        self.on_drag_start = on_drag_start
        self.on_drag = on_drag
        self.on_drag_end = on_drag_end
        self._enabled = False
        self._drag_origin = None  # (root_x, root_y) captured at press time

        self.bind("<Enter>", self._handle_enter)
        self.bind("<Leave>", self._handle_leave)
        self.bind("<ButtonPress-1>", self._handle_press)
        self.bind("<B1-Motion>", self._handle_motion)
        self.bind("<ButtonRelease-1>", self._handle_release)

    def set_resizable(self, enabled: bool) -> None:
        """Turn free-form dragging on or off for this divider."""
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