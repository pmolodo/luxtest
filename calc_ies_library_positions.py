import math

import sympy

from sympy import symbols


def deg(x):
    return x * 180 / math.pi


Cz = symbols("Cz")
Cy = symbols("Cy")
Ly = symbols("Ly")
Lz = symbols("Lz")
Dy = Cy - Ly
Dz = Cz - Lz

theta = symbols("theta")
Pl, Pf = symbols("Pl Pf")
Ha, Fl = symbols("Ha Fl")
T = Ha / (2 * Fl)
Pfc = Pf - 512
Plc = 512 - Pl
Pfr = Pfc / 512
Plr = Plc / 512
Q = T * Pfr
P = T * Plr

known_values = {Ly: 1, Lz: 0.05, Pl: 100, Pf: 602, Ha: 20.955, Fl: 50}


tan_theta_floor = (Cy - Cz * Q) / (Cz + Cy * Q)
tan_theta_light = (Dy + Dz * P) / (Dz - Dy * P)

theta_floor = sympy.atan(tan_theta_floor)
theta_light = sympy.atan(tan_theta_light)
theta_floor_known = theta_floor.subs(known_values)
theta_light_known = theta_light.subs(known_values)


theta_floor_deg = deg(theta_floor)
theta_light_deg = deg(theta_light)
theta_floor_deg_known = theta_floor_deg.subs(known_values)
theta_light_deg_known = theta_light_deg.subs(known_values)

theta_eq = sympy.Eq(tan_theta_floor, tan_theta_light)


theta_eq_known = theta_eq.subs(known_values)

Cy_solves = sympy.solve(theta_eq_known, Cy)

print(Cy_solves[1])
# 2.21064742520582*sqrt(-0.204626103519477*Cz**2 + Cz + 0.029404479511661) + 0.379075949035772
# As houdini expression:
# 2.21064742520582*sqrt(-0.204626103519477*ch("tz")*ch("tz") + ch("tz") + 0.029404479511661) + 0.379075949035772

theta_light_known_solve1 = theta_light_known.subs({Cy: Cy_solves[1]})

print(theta_light_known_solve1)
# atan((0.168622265625*Cz + 2.21064742520582*sqrt(-0.204626103519477*Cz**2 + Cz + 0.029404479511661) - 0.629355164245478)/(Cz - 0.372764377336279*sqrt(-0.204626103519477*Cz**2 + Cz + 0.029404479511661) + 0.0547016202546411))
# As houdini expression:
# -(atan((0.168622265625*ch("tz") + 2.21064742520582*sqrt(-0.204626103519477*ch("tz")*ch("tz") + ch("tz") + 0.029404479511661) - 0.629355164245478)/(ch("tz") - 0.372764377336279*sqrt(-0.204626103519477*ch("tz")*ch("tz") + ch("tz") + 0.029404479511661) + 0.0547016202546411)))

# Cz3 = {Cz: 3}
# Cys_solves_Cz3 = [s.subs(Cz3) for s in Cy_solves]
# print(Cys_solves_Cz3)
# # [-2.03019462332524, 2.78834652139679]

# known_Cz3 = known_values | Cz3

# theta_floor_deg_Cz3 = [float(theta_floor_deg.subs(known_Cz3 | {Cy: x})) for x in Cy_solves]
# theta_light_deg_Cz3 = [float(theta_light_deg.subs(known_Cz3 | {Cy: x})) for x in Cy_solves]

# assert all(math.isclose(s[0], s[1]) for s in zip(theta_floor_deg_Cz3, theta_light_deg_Cz3))
# # True

# print(theta_light_deg_Cz3)
# # [-36.19698562751027, 40.79635310724496]
