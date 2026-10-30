"""Гіпоциклоїда (варіант 15).

Рівняння (R - радіус нерухомого кола, r - радіус кола, що котиться, k = R/r):
    x(t) = (R - r) cos t + r cos((R - r) / r * t)
    y(t) = (R - r) sin t - r sin((R - r) / r * t)

Для раціонального k = m/n період параметра t: [0, 2*pi*n].
Якщо R/r не раціональне з малим знаменником, береться найближчий дріб m/n
(знаменник не більше 30), щоб крива замикалась точно.
"""
import math
from fractions import Fraction


def simpson(f, a, b, n):
    """Формула Сімпсона (n - кількість відрізків, стає парним)."""
    if n % 2:
        n += 1
    h = (b - a) / n
    s = f(a) + f(b)
    for i in range(1, n):
        s += (4 if i % 2 else 2) * f(a + i * h)
    return s * h / 3.0


class Hypocycloid:
    def __init__(self, R=7.0, r=2.0):
        self.R, self.r = R, r
        fr = Fraction(R / r).limit_denominator(30)
        self.m, self.n = fr.numerator, fr.denominator
        self.k = float(fr)                 # k = m/n, використовується в геометрії
        self.kk = self.k - 1.0             # (R - r)/r
        self.a = r * self.kk               # R_eff - r
        self.R_eff = r * self.k
        self.T = 2 * math.pi * self.n      # період параметра


    def at(self, t):
        a, r, kk = self.a, self.r, self.kk
        c, s = math.cos(t), math.sin(t)
        ck, sk = math.cos(kk * t), math.sin(kk * t)
        x = a * c + r * ck
        y = a * s - r * sk
        x1 = -a * (s + sk)                 # x'(t)
        y1 = a * (c - ck)                  # y'(t)
        x2 = -a * (c + kk * ck)            # x''(t)
        y2 = a * (-s + kk * sk)            # y''(t)
        return x, y, x1, y1, x2, y2

    @staticmethod
    def speed(x1, y1):
        return math.hypot(x1, y1)

    def _num(self, t):
        _, _, x1, y1, x2, y2 = self.at(t)
        return x1 * y2 - y1 * x2           #


    def points(self, per_turn=150):
        """Точки кривої (x, y, t) на [0, T]; результат кешується."""
        if getattr(self, "_pts", None) is None:
            N = min(per_turn * self.n, 2000)
            self._pts = []
            for i in range(N + 1):
                t = self.T * i / N
                x, y, *_ = self.at(t)
                self._pts.append((x, y, t))
        return self._pts

    def length_analytic(self):
        """Точна формула довжини за період: L = 8 (R_eff - r) n = 8 a n."""
        return 8.0 * self.a * self.n

    def length(self, samples_per_turn=600):
        """Довжина дуги чисельно - для перевірки аналітичної формули"""
        return simpson(lambda t: self.speed(*self.at(t)[2:4]), 0.0, self.T,
                       samples_per_turn * self.n)

    def area(self, samples_per_turn=600):
        """Площа, обмежена кривою: S = |1/2 * integral(x y' - y x') dt|."""
        def f(t):
            x, y, x1, y1, _, _ = self.at(t)
            return x * y1 - y * x1
        N = 2000
        h = self.T / N
        return abs(0.5 * h * sum(f(i * h) for i in range(N)))

    def curvature_radius(self, t):
        _, _, x1, y1, _, _ = self.at(t)
        num = abs(self._num(t))
        if num < 1e-12:
            return math.inf
        return self.speed(x1, y1) ** 3 / num

    def is_cusp(self, t):
        _, _, x1, y1, _, _ = self.at(t)
        return self.speed(x1, y1) < 1e-6

    def inflections(self, samples_per_turn=300):
        """Точки перегину: зміна знаку кривини між точками сітки,
        уточнених бісекцією. Точки повороту (cusp) не враховуються."""
        N = samples_per_turn * self.n
        h = self.T / N
        ts = [i * h for i in range(N + 1)]
        vals = [self._num(t) for t in ts]
        res = []
        for i in range(N):
            if vals[i] * vals[i + 1] < 0:
                lo, hi = ts[i], ts[i + 1]
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    if self._num(lo) * self._num(mid) <= 0:
                        hi = mid
                    else:
                        lo = mid
                tt = 0.5 * (lo + hi)
                if not self.is_cusp(tt):
                    res.append(tt)
        return res

    def has_asymptote(self):
        """Гіпоциклоїда обмежена колом радіуса R_eff, тому асимптот немає."""
        return False