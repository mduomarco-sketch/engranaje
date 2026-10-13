"""Engranaje recto de recambio, modulo 2, 25 dientes, con cubo en un lado.

Medidas tomadas con calibre (fotos en ../../engranaje):
  - diametro exterior 53,92 mm  -> modulo 2, z = 25 (54 teorico)
  - grosor de la rueda 6,90 mm
  - longitud total con cubo 21,21 mm
  - diametro del cubo 16,86 mm
  - agujero central 9,68 mm
Supuestos (estimados en las fotos): angulo de presion 20 grados, 4 agujeros
de 6 mm sobre un circulo de 33 mm con anillos de 10 mm, agujero central
redondo, cubo que sobresale 2 mm por el lado corto, alma del disco rebajada
1,5 mm por cada cara dentro de un diametro de 42 mm.
"""

import math
from pathlib import Path

import build123d as bd

_HERE = Path(__file__).resolve().parent

MODULE = 2.0
TEETH = 25
PRESSURE_ANGLE = 20.0
BACKLASH = 0.15  # holgura total en el circulo primitivo (mm)

GEAR_THICKNESS = 6.90
TOTAL_LENGTH = 21.21
HUB_DIAMETER = 16.86
BORE_DIAMETER = 9.68
BORE_CLEARANCE = 0.2  # holgura de impresion sobre el diametro del eje

HOLE_COUNT = 4
HOLE_DIAMETER = 6.0
HOLE_CIRCLE_DIAMETER = 33.0

SHORT_HUB = 2.0  # lo que sobresale el cubo por el lado corto
RECESS_DEPTH = 1.5  # rebaje del alma en cada cara
RECESS_DIAMETER = 42.0  # diametro interior de la corona dentada
BOSS_DIAMETER = 10.0  # anillos alrededor de los 4 agujeros

HUB_FILLET = 1.0


def _inv(alpha):
    return math.tan(alpha) - alpha


def gear_profile_points(module, teeth, pressure_deg, backlash, flank_steps=12, arc_steps=4):
    """Contorno 2D de un engranaje recto de evolvente, como lista de puntos XY."""
    alpha = math.radians(pressure_deg)
    r_pitch = module * teeth / 2
    r_base = r_pitch * math.cos(alpha)
    r_tip = r_pitch + module
    r_root = r_pitch - 1.25 * module
    pitch_angle = 2 * math.pi / teeth
    # medio angulo del diente en el primitivo, menos la mitad de la holgura
    half_tooth = math.pi / (2 * teeth) - backlash / (2 * r_pitch)

    def flank_angle(r):
        a_r = math.acos(min(1.0, r_base / r))
        return half_tooth + _inv(alpha) - _inv(a_r)

    r_start = max(r_base, r_root)
    radii = [r_start + (r_tip - r_start) * i / flank_steps for i in range(flank_steps + 1)]

    # medio diente (lado +): de la raiz a la punta
    half = []
    if r_root < r_base:
        half.append((r_root, flank_angle(r_base)))
    half += [(r, flank_angle(r)) for r in radii]

    pts = []
    for k in range(teeth):
        c = k * pitch_angle
        # flanco derecho (angulo negativo) de raiz a punta
        for r, a in half:
            pts.append((r, c - a))
        # arco de cabeza
        a_tip = half[-1][1]
        for i in range(1, arc_steps):
            pts.append((r_tip, c - a_tip + 2 * a_tip * i / arc_steps))
        # flanco izquierdo de punta a raiz
        for r, a in reversed(half):
            pts.append((r, c + a))
        # arco de fondo hasta el siguiente diente
        a_root = half[0][1]
        gap_start = c + a_root
        gap_end = c + pitch_angle - a_root
        for i in range(1, arc_steps):
            pts.append((r_root, gap_start + (gap_end - gap_start) * i / arc_steps))
    return [(r * math.cos(a), r * math.sin(a)) for r, a in pts]


def _cyl(radius, height, z0=0.0, x=0.0, y=0.0):
    return bd.Pos(x, y, z0) * bd.Cylinder(
        radius, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


def make_gear():
    """Z=0 en la cara de los dientes del lado corto; el cubo corto queda en Z<0."""
    profile = bd.Polygon(*gear_profile_points(MODULE, TEETH, PRESSURE_ANGLE, BACKLASH), align=None)
    body = bd.extrude(profile, amount=GEAR_THICKNESS)

    # rebaje del alma por las dos caras
    r_recess = RECESS_DIAMETER / 2
    body -= _cyl(r_recess, RECESS_DEPTH, 0.0)
    body -= _cyl(r_recess, RECESS_DEPTH, GEAR_THICKNESS - RECESS_DEPTH)

    # anillos de grosor completo alrededor de los agujeros
    r_bc = HOLE_CIRCLE_DIAMETER / 2
    hole_xy = [
        (r_bc * math.cos(2 * math.pi * i / HOLE_COUNT), r_bc * math.sin(2 * math.pi * i / HOLE_COUNT))
        for i in range(HOLE_COUNT)
    ]
    for x, y in hole_xy:
        body += _cyl(BOSS_DIAMETER / 2, GEAR_THICKNESS, 0.0, x, y)

    # cubo pasante: corto por abajo, largo por arriba
    body += _cyl(HUB_DIAMETER / 2, TOTAL_LENGTH, -SHORT_HUB)

    # redondeo en las uniones cubo-alma para dar resistencia
    web_faces_z = (RECESS_DEPTH, GEAR_THICKNESS - RECESS_DEPTH)
    root_edges = body.edges().filter_by(bd.GeomType.CIRCLE).filter_by(
        lambda e: abs(e.radius - HUB_DIAMETER / 2) < 1e-3
        and any(abs(e.center().Z - z) < 1e-3 for z in web_faces_z)
    )
    body = bd.fillet(root_edges, HUB_FILLET)

    body -= _cyl((BORE_DIAMETER + BORE_CLEARANCE) / 2, TOTAL_LENGTH, -SHORT_HUB)
    for x, y in hole_xy:
        body -= _cyl(HOLE_DIAMETER / 2, GEAR_THICKNESS, 0.0, x, y)
    return body


def main():
    gear = make_gear()
    gear.label = "engranaje_m2_z25"
    (_HERE / "STEP").mkdir(exist_ok=True)
    (_HERE / "STL").mkdir(exist_ok=True)
    bd.export_step(gear, str(_HERE / "STEP" / "engranaje.step"))
    bd.export_stl(gear, str(_HERE / "STL" / "engranaje.stl"), tolerance=1e-3, angular_tolerance=0.1)
    bb = gear.bounding_box()
    print(f"engranaje: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm, V={gear.volume / 1000:.2f} cm3")


if __name__ == "__main__":
    main()
