#!/usr/bin/env python3
"""The whole three-body problem, in thirty lines, with no libraries.

Run it:      python3 three_body.py
It prints the figure-eight orbit as characters, and the energy, which should not move.

The physics is the line every page on this site is about: each body is pulled toward
each other body, by their weights divided by the square of the distance. The stepping
is leapfrog — half a kick, a full drift, half a kick — which is what keeps the energy
from walking away.  https://nanobotco.github.io/three-body/
"""

G = 1.0
M = [1.0, 1.0, 1.0]                                    # three equal weights
R = [[0.97000436, -0.24308753],                        # the starting places
     [-0.97000436, 0.24308753], [0.0, 0.0]]
P = [[0.466203685, 0.43236573]] * 2 + [[-0.93240737, -0.86473146]]    # the starting speeds
T, H = 6.32591398, 0.0002                              # one full period, and the step


def pull(r):
    """The acceleration of each body: the line the whole problem is written in."""
    a = [[0.0, 0.0] for _ in r]
    for i in range(len(r)):
        for j in range(len(r)):
            if i != j:
                dx, dy = r[j][0] - r[i][0], r[j][1] - r[i][1]
                d3 = (dx * dx + dy * dy) ** 1.5
                a[i][0] += G * M[j] * dx / d3
                a[i][1] += G * M[j] * dy / d3
    return a


def energy(r, p):
    e = sum(0.5 * M[i] * (p[i][0] ** 2 + p[i][1] ** 2) for i in range(3))
    for i in range(3):
        for j in range(i + 1, 3):
            dx, dy = r[j][0] - r[i][0], r[j][1] - r[i][1]
            e -= G * M[i] * M[j] / (dx * dx + dy * dy) ** 0.5
    return e


def step(r, p, h):
    """Half a kick, a whole drift, half a kick."""
    a = pull(r)
    for i in range(3):
        for k in (0, 1):
            p[i][k] += 0.5 * h * a[i][k]
            r[i][k] += h * p[i][k]
    a = pull(r)
    for i in range(3):
        for k in (0, 1):
            p[i][k] += 0.5 * h * a[i][k]


if __name__ == "__main__":
    r = [q[:] for q in R]
    p = [q[:] for q in P]
    e0 = energy(r, p)
    grid = [[" "] * 78 for _ in range(15)]
    marks = ".oO"
    for n in range(int(T / H)):
        step(r, p, H)
        for i, (x, y) in enumerate(r):
            col, rowi = int(38 + x * 36), int(7 - y * 19)
            if 0 <= col < 78 and 0 <= rowi < 15:
                grid[rowi][col] = marks[i]
    print("\n".join("".join(row) for row in grid))
    print(f"one period of the figure eight, {int(T / H):,} steps of {H}")
    print(f"energy at the start {e0:.9f}   at the end {energy(r, p):.9f}")
    print(f"the three bodies are back within "
          f"{max(abs(r[i][k] - R[i][k]) for i in range(3) for k in (0, 1)):.2e} of where they set off")
