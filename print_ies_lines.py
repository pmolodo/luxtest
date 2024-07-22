# Funcs used to help generate custom .ies profiles


def print_angles_values(angles, values, precision=1):
    assert len(angles) == len(values)

    print(f"num: {len(angles)}")

    for i, angle in enumerate(angles):
        print(f"{angle:>6.1f} ", end="")
        if (i + 1) % 10 == 0:
            print()
    if (i + 1) % 10 != 0:
        print()
    print("0.0")  # horizontal angles

    for i, val in enumerate(values):
        print(f"{val:>6.{precision}f} ", end="")
        if (i + 1) % 10 == 0:
            print()


def vertical_bands2():
    color = 1.0

    angles = []
    values = []

    for theta in range(0, 171, 10):
        angles.append(theta)
        if theta == 170:
            angles.append(180)
        else:
            angles.append(theta + 9.9)
        values.append(color)
        values.append(color)
        color = 1 - color
    print_angles_values(angles, values)


def vertical_bands3():
    v_num = 181  # 0-180, inclusive

    angles = []
    values = []
    for v in range(v_num):
        angles.append(v)
        if v < 10:
            value = 0.25
        elif v >= 170:
            value = 0.75
        else:
            value = (v // 10) % 2
        values.append(value)

    print_angles_values(angles, values, precision=2)


def vertical_bands4():
    # in theory, should give identical results to vertical_bands3, but without
    # uniform spacing

    angles = []
    values = []
    for v in range(181):
        # skip the repeating interior elements

        # bands generally start/end at 0's and 9s, modulo 10
        # exception is last row, which goes from 170 to 180 - so we skip the
        # final "9", 179
        if v == 179:
            continue
        if v % 10 not in (0, 9):
            continue

        angles.append(v)
        if v < 10:
            value = 0.25
        elif v >= 170:
            value = 0.75
        else:
            value = (v // 10) % 2
        values.append(value)

    print_angles_values(angles, values, precision=2)
