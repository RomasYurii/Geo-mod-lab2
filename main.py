import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGroupBox,
                               QFormLayout, QDoubleSpinBox, QCheckBox, QPushButton,
                               QScrollArea, QLabel, QSlider, QComboBox)
from canvas import Canvas
from curve import Hypocycloid

DEFAULTS = dict(R=7.0, r=2.0, tfrac=0.25, half=4.0, ppc=20.0,
                dx=0.0, dy=0.0, px=0.0, py=0.0, angle=0.0)
# діапазони анімації: (мін, макс, крок) для кожного параметра
ANIM = {"r": (0.5, 5.0, 0.05), "R": (6.0, 15.0, 0.05)}


def line_eq(px, py, dx, dy):
    """Загальне рівняння прямої через P з напрямним вектором (dx, dy): A X + B Y + C = 0."""
    A, B = dy, -dx
    C = -(A * px + B * py)
    return f"{A:.4f}·X {B:+.4f}·Y {C:+.4f} = 0"


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР2. Гіпоциклоїда. Варіант 15")
        self.w, self.defaults = {}, {}
        self._busy = False
        self.anim_dir = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        self.canvas = Canvas(self.pick, self.pivot_drag)
        panel = QVBoxLayout()

        panel.addWidget(self.group("Параметри гіпоциклоїди (см)", [
            ("R", "R - радіус нерухомого кола", DEFAULTS["R"], 1.0, 20.0),
            ("r", "r - радіус кола, що котиться", DEFAULTS["r"], 0.3, 19.7)]))
        self.info_k = QLabel()
        self.info_k.setWordWrap(True)
        panel.addWidget(self.info_k)

        # ---- точка на кривій
        box = QGroupBox("Точка на кривій (дотична, нормаль)")
        lay = QVBoxLayout(box)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setValue(int(DEFAULTS["tfrac"] * 1000))
        self.slider.valueChanged.connect(self.slider_moved)
        lay.addWidget(self.slider)
        row = QHBoxLayout()
        bl = QPushButton("<")
        br = QPushButton(">")
        bl.clicked.connect(lambda: self.step_t(-1))
        br.clicked.connect(lambda: self.step_t(1))
        self.t_label = QLabel()
        row.addWidget(bl); row.addWidget(self.t_label); row.addWidget(br)
        lay.addLayout(row)
        self.tan = QCheckBox("Дотична")
        self.norm = QCheckBox("Нормаль")
        self.tan.setChecked(True); self.norm.setChecked(True)
        self.tan.stateChanged.connect(self.changed)
        self.norm.stateChanged.connect(self.changed)
        lay.addWidget(self.tan); lay.addWidget(self.norm)
        self.half = QDoubleSpinBox()
        self.half.setRange(0.5, 30); self.half.setValue(DEFAULTS["half"])
        self.half.setPrefix("півдовжина: "); self.half.setSuffix(" см")
        self.half.valueChanged.connect(self.changed)
        lay.addWidget(self.half)
        panel.addWidget(box)

        # ---- анімація
        box = QGroupBox("Анімація (автоматична зміна параметра)")
        lay = QVBoxLayout(box)
        self.anim_param = QComboBox()
        self.anim_param.addItems(["r", "R"])
        lay.addWidget(self.anim_param)
        self.anim_btn = QPushButton("Старт / Стоп анімації")
        self.anim_btn.clicked.connect(self.toggle_anim)
        lay.addWidget(self.anim_btn)
        panel.addWidget(box)

        # ---- інформація
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        panel.addWidget(self.info)

        # ---- евклідові
        panel.addWidget(self.group("Евклідові перетворення кривої", [
            ("dx", "Зсув dx", DEFAULTS["dx"], -40, 40),
            ("dy", "Зсув dy", DEFAULTS["dy"], -40, 40),
            ("px", "Точка обертання X", DEFAULTS["px"], -40, 40),
            ("py", "Точка обертання Y", DEFAULTS["py"], -40, 40),
            ("angle", "Кут обертання (°)", DEFAULTS["angle"], -360, 360, 1)]))

        panel.addWidget(self.group("Вигляд", [
            ("ppc", "Пікселів на см", DEFAULTS["ppc"], 6, 60, 1)]))

        b = QPushButton("Скинути все (дефолтний набір)")
        b.clicked.connect(self.reset)
        panel.addWidget(b)
        panel.addStretch()

        host = QWidget(); host.setLayout(panel)
        scroll = QScrollArea(); scroll.setWidget(host); scroll.setWidgetResizable(True)
        scroll.setFixedWidth(470)
        lay = QHBoxLayout(self)
        lay.addWidget(scroll)
        lay.addWidget(self.canvas, 1)
        self.changed()

    def group(self, title, rows):
        box = QGroupBox(title)
        form = QFormLayout(box)
        for row in rows:
            key, label, val, lo, hi = row[:5]
            step = row[5] if len(row) > 5 else 0.1
            sp = QDoubleSpinBox()
            sp.setRange(lo, hi); sp.setDecimals(2); sp.setSingleStep(step); sp.setValue(val)
            sp.valueChanged.connect(self.changed)
            form.addRow(label, sp)
            self.w[key] = sp
            self.defaults[key] = val
        return box


    def slider_moved(self, v):
        self.changed()

    def step_t(self, d):
        self.slider.setValue(max(0, min(1000, self.slider.value() + d * 25)))

    def pick(self, t):
        """Перетягування точки на кривій: t -> положення повзунка."""
        T = Hypocycloid(self.w["R"].value(), self.w["r"].value()).T
        self.slider.setValue(max(0, min(1000, int(round(1000 * t / T)))))

    def pivot_drag(self, x, y):
        """Перетягування центру обертання мишкою."""
        for k, v in (("px", x), ("py", y)):
            self.w[k].blockSignals(True)
            self.w[k].setValue(v)
            self.w[k].blockSignals(False)
        self.changed()

    def toggle_anim(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(40)

    def tick(self):
        name = self.anim_param.currentText()
        lo, hi, step = ANIM[name]
        w = self.w[name]
        v = w.value() + self.anim_dir * step
        if v >= hi:
            v, self.anim_dir = hi, -1
        elif v <= lo:
            v, self.anim_dir = lo, 1
        self._busy = True
        w.setValue(v)
        self._busy = False
        self.changed()

    def reset(self):
        self.timer.stop()
        for k, s in self.w.items():
            s.setValue(self.defaults[k])
        self.slider.setValue(int(DEFAULTS["tfrac"] * 1000))
        self.half.setValue(DEFAULTS["half"])
        self.tan.setChecked(True); self.norm.setChecked(True)
        self.changed()

    def changed(self, *_):
        if self._busy:
            return
        self._busy = True
        w = self.w
        # R завжди більше r
        if w["r"].value() >= w["R"].value() - 0.1:
            w["r"].setValue(w["R"].value() - 0.1)
        R, r = w["R"].value(), w["r"].value()

        curve = Hypocycloid(R, r)
        t = self.slider.value() / 1000.0 * curve.T
        self.t_label.setText(f"t = {t:.3f} рад  ({self.slider.value() / 10:.1f}% періоду)")
        p = {k: s.value() for k, s in w.items()}
        p.update(t=t, half=self.half.value(),
                 show_tan=self.tan.isChecked(), show_norm=self.norm.isChecked(),
                 tfrac=self.slider.value() / 1000.0)
        infl = curve.inflections()
        self.canvas.set_state(p, curve, infl)
        self.update_info(curve, t, infl)
        self._busy = False

    def update_info(self, c, t, infl):
        self.info_k.setText(
            f"k = R/r = {c.m}/{c.n} = {c.k:.4f}; кількість кіл (обертів): {c.n}; "
            f"кількість зубців (cusps): {c.m}\n"
            f"Ефективний радіус R_eff = {c.R_eff:.4f} см (для раціонального k)")
        x, y, x1, y1, _, _ = c.at(t)
        L = c.length_analytic()
        S = c.area()
        rho = c.curvature_radius(t)
        rho_s = "∞ (пряма)" if rho == float("inf") else f"{rho:.4f} см"
        if c.is_cusp(t):
            tan_s = norm_s = "не визначені (точка повороту - cusp)"
            rho_s = "не визначений (точка повороту)"
        else:
            tan_s = line_eq(x, y, x1, y1)      # напрямний вектор (x', y')
            norm_s = line_eq(x, y, -y1, x1)    # напрямний вектор нормалі (-y', x')
        infl_s = "немає" if not infl else ", ".join(
            f"t={tt:.3f} ({c.at(tt)[0]:.3f}; {c.at(tt)[1]:.3f})" for tt in infl)
        self.info.setText(
            f"Точка P(t): ({x:.4f}; {y:.4f}) см\n"
            f"Довжина дуги за період: L = {L:.4f} см  (перевірка: 8(R−r)·n = {8*(c.R_eff-c.r)*c.n:.4f})\n"
            f"Площа, обмежена кривою: S = {S:.4f} см²\n"
            f"Асимптоти: немає (крива обмежена колом радіуса {c.R_eff:.3f} см)\n"
            f"Точки перегину: {infl_s}\n"
            f"Радіус кривини в P: ρ = {rho_s}\n"
            f"Дотична: {tan_s}\n"
            f"Нормаль: {norm_s}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Main()
    win.resize(1400, 860)
    win.show()
    sys.exit(app.exec())