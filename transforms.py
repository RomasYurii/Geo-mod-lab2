"""Власна реалізація матриць перетворень 3x3 (рядкова конвенція: P' = P * T)."""
import math


def identity():
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def mul(a, b):
    """Добуток матриць 3x3: a * b (спочатку a, потім b)."""
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def chain(*ms):
    r = identity()
    for m in ms:
        r = mul(r, m)
    return r


# ---------- Евклідові ----------
def translation(dx, dy):
    m = identity()
    m[2][0], m[2][1] = dx, dy
    return m


def rotation(deg):
    """Обертання навколо початку координат (проти годинникової стрілки)."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]]


def about_point(m, px, py):
    """Виконує перетворення m відносно довільної точки p: T(-p) * m * T(p)."""
    return chain(translation(-px, -py), m, translation(px, py))


def rotation_about(deg, px, py):
    return about_point(rotation(deg), px, py)


# ---------- Афінні (окремі випадки) ----------
def scaling(sx, sy):
    return [[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]]


def scaling_about(sx, sy, px, py):
    return about_point(scaling(sx, sy), px, py)


def point_symmetry(px, py):
    """Симетрія відносно точки p"""
    return scaling_about(-1.0, -1.0, px, py)


# ---------- Афінні ----------
def affine(ox, oy, xx, xy, yx, yy):
    """Новий базис: O - початок, X і Y - одиничні точки на осях."""
    return [[xx - ox, xy - oy, 0.0],
            [yx - ox, yy - oy, 0.0],
            [ox, oy, 1.0]]


# ---------- Проективні ----------
def projective(xend, yend, o, wx, wy, w0, n=1.0):
    """Проективне перетворення."""
    return [[(wx * xend[0] - w0 * o[0]) / n, (wx * xend[1] - w0 * o[1]) / n, (wx - w0) / n],
            [(wy * yend[0] - w0 * o[0]) / n, (wy * yend[1] - w0 * o[1]) / n, (wy - w0) / n],
            [w0 * o[0], w0 * o[1], w0]]


def inverse(m):
    """Обернена матриця 3x3 (через алгебраїчні доповнення)."""
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        return None
    return [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
            [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
            [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]


def apply(m, x, y, clip=True):
    """Застосування матриці до точки з діленням на вагу w (формули 6-9).
    Повертає None, якщо точка за межами області видимості (w <= 0)."""
    nx = x * m[0][0] + y * m[1][0] + m[2][0]
    ny = x * m[0][1] + y * m[1][1] + m[2][1]
    w = x * m[0][2] + y * m[1][2] + m[2][2]
    if (clip and w <= 1e-6) or abs(w) < 1e-9:
        return None
    return nx / w, ny / w