#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""physics.py — the three-body equations, and the steppers that turn them into paths.

Everything on the site that moves comes out of these two functions. The site's pictures
are drawn from them (tools/draw.py), the published initial conditions are checked against
them (tests/check_data.py), and the browser runs the same leapfrog in JavaScript.

    r̈ᵢ = Σ_{j≠i} G mⱼ (rⱼ − rᵢ) / |rⱼ − rᵢ|³
"""
from __future__ import annotations

import numpy as np

G = 1.0


def accel(pos: np.ndarray, mass: np.ndarray, g: float = G, soft: float = 0.0) -> np.ndarray:
    """pos (n,2) → acceleration (n,2). soft > 0 rounds off the bottom of the well."""
    d = pos[None, :, :] - pos[:, None, :]                 # d[i,j] = rj - ri
    r2 = (d ** 2).sum(-1) + soft ** 2
    np.fill_diagonal(r2, np.inf)
    inv = r2 ** -1.5
    return g * (d * (inv * mass[None, :])[..., None]).sum(1)


def energy(pos, vel, mass, g: float = G) -> float:
    ke = 0.5 * (mass * (vel ** 2).sum(-1)).sum()
    d = np.linalg.norm(pos[None, :, :] - pos[:, None, :], axis=-1)
    iu = np.triu_indices(len(mass), 1)
    pe = -g * (mass[iu[0]] * mass[iu[1]] / d[iu]).sum()
    return float(ke + pe)


def angular_momentum(pos, vel, mass) -> float:
    return float((mass * (pos[:, 0] * vel[:, 1] - pos[:, 1] * vel[:, 0])).sum())


def leapfrog(pos, vel, mass, dt, steps, g: float = G, soft: float = 0.0, every: int = 1):
    """Kick-drift-kick. Returns the track (steps//every+1, n, 2) and the final state.
    Symplectic: the energy wobbles with the orbit and does not walk away from it."""
    pos = pos.astype(float).copy()
    vel = vel.astype(float).copy()
    a = accel(pos, mass, g, soft)
    track = [pos.copy()]
    for s in range(steps):
        vel += 0.5 * dt * a
        pos += dt * vel
        a = accel(pos, mass, g, soft)
        vel += 0.5 * dt * a
        if (s + 1) % every == 0:
            track.append(pos.copy())
    return np.array(track), pos, vel


# Yoshida's fourth-order composition of the leapfrog — used where the answer has to be
# good enough to compare against a published number, not just to look right.
_W1 = 1.0 / (2.0 - 2.0 ** (1.0 / 3.0))
_W0 = -(2.0 ** (1.0 / 3.0)) * _W1
YOSHIDA = (_W1, _W0, _W1)


def yoshida(pos, vel, mass, dt, steps, g: float = G, every: int = 0):
    pos = pos.astype(float).copy()
    vel = vel.astype(float).copy()
    track = [pos.copy()] if every else []
    for s in range(steps):
        for w in YOSHIDA:
            h = w * dt
            vel += 0.5 * h * accel(pos, mass, g)
            pos += h * vel
            vel += 0.5 * h * accel(pos, mass, g)
        if every and (s + 1) % every == 0:
            track.append(pos.copy())
    return (np.array(track) if every else None), pos, vel


def state(pos, vel):
    return np.concatenate([np.asarray(pos).ravel(), np.asarray(vel).ravel()])


def close_after(pos, vel, mass, period, dt=2e-4, g: float = G) -> float:
    """How far the state is from where it started after one claimed period.
    A periodic orbit brings it back; the number is the distance in the 12 numbers."""
    n = max(int(round(period / dt)), 1)
    _, p1, v1 = yoshida(pos, vel, mass, period / n, n, g)
    return float(np.linalg.norm(state(p1, v1) - state(pos, vel)))


# ---------------------------------------------------------------- many at once
def accel_batch(pos: np.ndarray, mass: np.ndarray, g: float = G) -> np.ndarray:
    """pos (k,n,2) → (k,n,2). One call moves every trajectory in the batch, which is how
    the search over starting speeds and the divergence fan are affordable."""
    d = pos[:, None, :, :] - pos[:, :, None, :]
    r2 = (d ** 2).sum(-1)
    k, n, _ = pos.shape
    idx = np.arange(n)
    r2[:, idx, idx] = np.inf
    inv = r2 ** -1.5
    return g * (d * (inv * mass[None, None, :])[..., None]).sum(2)


def accel_batch_soft(pos: np.ndarray, mass: np.ndarray, soft: float, g: float = G) -> np.ndarray:
    """Batch acceleration with the bottom of the well rounded off. A deliberate change to
    the physics, made where the close passes are not what is being measured."""
    d = pos[:, None, :, :] - pos[:, :, None, :]
    r2 = (d ** 2).sum(-1) + soft ** 2
    idx = np.arange(pos.shape[1])
    r2[:, idx, idx] = np.inf
    return g * (d * ((r2 ** -1.5) * mass[None, None, :])[..., None]).sum(2)


def leapfrog_batch(pos, vel, mass, dt, steps, g: float = G, every: int = 0):
    pos = pos.astype(float).copy()
    vel = vel.astype(float).copy()
    a = accel_batch(pos, mass, g)
    track = [pos.copy()] if every else []
    for s in range(steps):
        vel += 0.5 * dt * a
        pos += dt * vel
        a = accel_batch(pos, mass, g)
        vel += 0.5 * dt * a
        if every and (s + 1) % every == 0:
            track.append(pos.copy())
    return (np.array(track) if every else None), pos, vel


# ---------------------------------------------------------------- three bodies, scalars
def yoshida3(s, dt, steps, g: float = G, m=(1.0, 1.0, 1.0), keep: int = 0):
    """The same fourth-order stepper written out for three bodies in plain floats.
    s = [x1,y1,x2,y2,x3,y3, vx1,vy1,vx2,vy2,vx3,vy3]. Twenty times faster than the array
    version at n=3, which is what makes the orbit search finish."""
    x1, y1, x2, y2, x3, y3, u1, v1, u2, v2, u3, v3 = (float(q) for q in s)
    m1, m2, m3 = m
    track = []
    for step in range(steps):
        for w in YOSHIDA:
            h = w * dt
            for half in (0, 1):
                dx = x2 - x1; dy = y2 - y1; r = (dx * dx + dy * dy) ** -1.5
                a1x = g * m2 * dx * r; a1y = g * m2 * dy * r
                a2x = -g * m1 * dx * r; a2y = -g * m1 * dy * r
                dx = x3 - x1; dy = y3 - y1; r = (dx * dx + dy * dy) ** -1.5
                a1x += g * m3 * dx * r; a1y += g * m3 * dy * r
                a3x = -g * m1 * dx * r; a3y = -g * m1 * dy * r
                dx = x3 - x2; dy = y3 - y2; r = (dx * dx + dy * dy) ** -1.5
                a2x += g * m3 * dx * r; a2y += g * m3 * dy * r
                a3x += -g * m2 * dx * r; a3y += -g * m2 * dy * r
                u1 += 0.5 * h * a1x; v1 += 0.5 * h * a1y
                u2 += 0.5 * h * a2x; v2 += 0.5 * h * a2y
                u3 += 0.5 * h * a3x; v3 += 0.5 * h * a3y
                if half == 0:
                    x1 += h * u1; y1 += h * v1
                    x2 += h * u2; y2 += h * v2
                    x3 += h * u3; y3 += h * v3
        if keep and (step + 1) % keep == 0:
            track.append((x1, y1, x2, y2, x3, y3))
    return np.array([x1, y1, x2, y2, x3, y3, u1, v1, u2, v2, u3, v3]), track


def sd_state(vx, vy):
    """The starting line Šuvakov and Dmitrašinović scan: two bodies at ±1 on the x axis
    with the same velocity, the third at the origin carrying twice it the other way.
    Zero total momentum, zero angular momentum, the shape a straight line."""
    return np.array([-1.0, 0.0, 1.0, 0.0, 0.0, 0.0, vx, vy, vx, vy, -2 * vx, -2 * vy])


def returns(s0, period, dt=2e-4, g: float = G, m=(1.0, 1.0, 1.0)) -> float:
    n = max(int(round(period / dt)), 1)
    s1, _ = yoshida3(s0, period / n, n, g, m)
    return float(np.linalg.norm(s1 - s0))
