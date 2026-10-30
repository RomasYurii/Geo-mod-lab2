import math
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush, QPixmap
from PySide6.QtWidgets import QWidget

import transforms as T

HANDLE_R = 12          # радіус захоплення точки мишкою, px


class Canvas(QWidget):


    def __init__(self, on_pick, on_pivot):
        super().__init__()
        self.setMinimumSize(760, 640)
        self.p = {}
        self.curve = None
        self.infl = []
        self.on_pick = on_pick          # callback(t)
        self.on_pivot = on_pivot        # callback(x, y) у координатах сцени
        self.screen_pts = []            # (sx, sy, t) для пошуку найближчої точки
        self.P_screen = None
        self.drag = None
        self._grid = None               # кеш сітки та осей
        self._grid_key = None
        self._path = None               # кеш кривої
        self._path_key = None

    def set_state(self, p, curve, infl):
        self.p, self.curve, self.infl = p, curve, infl
        self.update()

    def to_screen(self, x, y):
        s = self.p["ppc"]
        return QPointF(self.width() / 2 + x * s, self.height() / 2 - y * s)

    def from_screen(self, sx, sy):
        s = self.p["ppc"]
        return (sx - self.width() / 2) / s, (self.height() / 2 - sy) / s

    def model(self):
        p = self.p
        return T.chain(T.rotation_about(p["angle"], p["px"], p["py"]),
                       T.translation(p["dx"], p["dy"]))

    def mousePressEvent(self, e):
        if not self.curve:
            return
        mx, my = e.position().x(), e.position().y()
        pv = self.to_screen(self.p["px"], self.p["py"])
        if math.hypot(pv.x() - mx, pv.y() - my) <= HANDLE_R:
            self.drag = "pivot"
            return
        if self.P_screen and math.hypot(self.P_screen.x() - mx, self.P_screen.y() - my) <= HANDLE_R:
            self.drag = "point"
            return
        self.drag = "point"
        self._pick_nearest(mx, my, limit=HANDLE_R * 3)

    def mouseMoveEvent(self, e):
        if not self.drag:
            return
        mx, my = e.position().x(), e.position().y()
        if self.drag == "pivot":
            x, y = self.from_screen(mx, my)
            self.on_pivot(round(x, 2), round(y, 2))
        else:
            self._pick_nearest(mx, my, limit=None)

    def mouseReleaseEvent(self, _):
        self.drag = None

    def _pick_nearest(self, mx, my, limit):
        best, bd = None, 1e18
        for sx, sy, t in self.screen_pts:
            d = (sx - mx) ** 2 + (sy - my) ** 2
            if d < bd:
                best, bd = t, d
        if best is not None and (limit is None or bd <= limit ** 2):
            self.on_pick(best)

    def _grid_pixmap(self):
        key = (self.width(), self.height(), self.p["ppc"])
        if self._grid_key == key:
            return self._grid
        s = self.p["ppc"]
        W, H = self.width(), self.height()
        pm = QPixmap(W, H)
        pm.fill(QColor("#ffffff"))
        qp = QPainter(pm)
        qp.setRenderHint(QPainter.Antialiasing)
        grid = QPainterPath()
        nx, ny = int(W / 2 / s) + 2, int(H / 2 / s) + 2
        for i in range(-nx, nx + 1):
            grid.moveTo(self.to_screen(i, -ny)); grid.lineTo(self.to_screen(i, ny))
        for j in range(-ny, ny + 1):
            grid.moveTo(self.to_screen(-nx, j)); grid.lineTo(self.to_screen(nx, j))
        qp.setPen(QPen(QColor("#d9d9d9"), 1))
        qp.drawPath(grid)
        qp.setPen(QPen(QColor("#e03131"), 2))
        qp.drawLine(self.to_screen(-nx, 0), self.to_screen(nx, 0))
        qp.setPen(QPen(QColor("#2f9e44"), 2))
        qp.drawLine(self.to_screen(0, -ny), self.to_screen(0, ny))
        qp.setPen(QColor("#222222"))
        for i in range(-nx, nx + 1, 5):
            if i:
                qp.drawText(QPointF(self.to_screen(i, 0).x() - 4, self.to_screen(i, 0).y() + 15), str(i))
        for j in range(-ny, ny + 1, 5):
            if j:
                qp.drawText(QPointF(self.to_screen(0, j).x() + 6, self.to_screen(0, j).y() + 4), str(j))
        qp.end()
        self._grid, self._grid_key = pm, key
        return pm


    def _curve_path(self, m):
        key = (id(self.curve), self.width(), self.height(), self.p["ppc"],
               self.p["dx"], self.p["dy"], self.p["px"], self.p["py"], self.p["angle"])
        if self._path_key == key:
            return self._path
        path = QPainterPath()
        pts = []
        first = True
        for x, y, t in self.curve.points():
            q = T.apply(m, x, y, clip=False)
            sp = self.to_screen(*q)
            pts.append((sp.x(), sp.y(), t))
            if first:
                path.moveTo(sp); first = False
            else:
                path.lineTo(sp)
        self.screen_pts = pts
        self._path, self._path_key = path, key
        return path

    def paintEvent(self, _):
        if not self.p or not self.curve:
            return
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.drawPixmap(0, 0, self._grid_pixmap())

        m = self.model()
        c = self.curve
        qp.setPen(QPen(QColor("#111111"), 2.5))
        qp.drawPath(self._curve_path(m))

        # точки перегину
        qp.setPen(QPen(QColor("#c2255c"), 2))
        qp.setBrush(QBrush(QColor("#c2255c")))
        for t in self.infl:
            x, y, *_ = c.at(t)
            qp.drawEllipse(self.to_screen(*T.apply(m, x, y, clip=False)), 4, 4)

        # дотична і нормаль
        t = self.p["t"]
        x, y, x1, y1, _, _ = c.at(t)
        L = self.p["half"]
        sp = math.hypot(x1, y1)
        if sp > 1e-9:
            ux, uy = x1 / sp, y1 / sp
            if self.p["show_tan"]:
                qp.setPen(QPen(QColor("#1c7ed6"), 2))
                a = T.apply(m, x - L * ux, y - L * uy, clip=False)
                b = T.apply(m, x + L * ux, y + L * uy, clip=False)
                qp.drawLine(self.to_screen(*a), self.to_screen(*b))
            if self.p["show_norm"]:
                qp.setPen(QPen(QColor("#f08c00"), 2))
                a = T.apply(m, x + L * uy, y - L * ux, clip=False)
                b = T.apply(m, x - L * uy, y + L * ux, clip=False)
                qp.drawLine(self.to_screen(*a), self.to_screen(*b))

        qp.setPen(QPen(QColor("#ffffff"), 1))
        qp.setBrush(QBrush(QColor("#e8590c")))
        self.P_screen = self.to_screen(*T.apply(m, x, y, clip=False))
        qp.drawEllipse(self.P_screen, 7, 7)

        qp.setBrush(QBrush(QColor("#fcc419")))
        qp.setPen(QPen(QColor("#222222"), 1))
        qp.drawEllipse(self.to_screen(self.p["px"], self.p["py"]), 6, 6)
        qp.end()