#!/usr/bin/env python3
"""eng-calc: everyday electrical + mechanical engineering calculators.

Python 3 stdlib only. SI units in and out; component values accept SI
suffixes (k, M, G, m, u/µ, n, p). See SKILL.md for scope notes.
"""

import argparse
import math
import sys

# ---------------------------------------------------------------- helpers

SI_SUFFIXES = {
    "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6,
    "m": 1e-3, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9,
}


def parse_value(text):
    """Parse a number with an optional SI suffix (e.g. 10k, 100n, 4u7 not supported)."""
    s = str(text).strip()
    # strip common unit letters after the suffix (10kohm, 100nF, 15mA)
    for unit in ("ohm", "Ohm", "OHM", "F", "H", "A", "V", "W", "Hz"):
        if s.endswith(unit) and len(s) > len(unit):
            s = s[: -len(unit)]
            break
    if s and s[-1] in SI_SUFFIXES:
        mult = SI_SUFFIXES[s[-1]]
        s = s[:-1]
    else:
        mult = 1.0
    try:
        return float(s) * mult
    except ValueError:
        raise SystemExit(f"error: cannot parse value '{text}' "
                         "(use plain numbers or SI suffixes k/M/G/m/u/n/p)")


def fmt_si(value, unit=""):
    """Format a value with an engineering SI prefix."""
    if value == 0:
        return f"0 {unit}".strip()
    prefixes = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""),
                (1e-3, "m"), (1e-6, "u"), (1e-9, "n"), (1e-12, "p")]
    mag = abs(value)
    for factor, prefix in prefixes:
        if mag >= factor:
            return f"{value / factor:.4g} {prefix}{unit}".strip()
    return f"{value:.4g} {unit}".strip()


def fail(msg):
    raise SystemExit(f"error: {msg}")


# ---------------------------------------------------------------- E-series

E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
E96 = [1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30,
       1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74,
       1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32,
       2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09,
       3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
       4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49,
       5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32,
       7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76]

SERIES = {"E12": E12, "E24": E24, "E96": E96}


def series_values(series_name, decade_min=0, decade_max=8):
    """All series values across decades 10^decade_min .. 10^decade_max."""
    base = SERIES[series_name]
    return [v * 10 ** d for d in range(decade_min, decade_max + 1) for v in base]


def nearest_in_series(value, series_name):
    """Return (below, nearest, above) standard values for `value`."""
    if value <= 0:
        fail("E-series lookup needs a positive value")
    decade = math.floor(math.log10(value))
    candidates = sorted(v * 10 ** d for d in (decade - 1, decade, decade + 1)
                        for v in SERIES[series_name])
    below = max((v for v in candidates if v <= value), default=candidates[0])
    above = min((v for v in candidates if v >= value), default=candidates[-1])
    nearest = below if abs(below - value) <= abs(above - value) else above
    return below, nearest, above


def cmd_eseries(args):
    value = parse_value(args.value)
    below, nearest, above = nearest_in_series(value, args.series)
    print(f"target : {fmt_si(value)}  ({args.series})")
    for label, v in (("below", below), ("nearest", nearest), ("above", above)):
        err = (v - value) / value * 100
        print(f"{label:7s}: {fmt_si(v):>10s}  ({err:+.2f} %)")


# ---------------------------------------------------------------- divider

def _divider_best_pair(vin, vout, rtotal, series_name):
    """Search E-series pairs; return (r1, r2, actual_vout, err_pct)."""
    target_r2 = rtotal * vout / vin
    decade = math.floor(math.log10(target_r2))
    best = None
    for r2 in series_values(series_name, decade - 1, decade + 1):
        if not (0.2 * target_r2 <= r2 <= 5 * target_r2):
            continue
        r1_ideal = r2 * (vin - vout) / vout
        for r1 in set(nearest_in_series(r1_ideal, series_name)):
            if not (0.5 * rtotal <= r1 + r2 <= 2.0 * rtotal):
                continue  # keep divider impedance near the requested Rtotal
            actual = vin * r2 / (r1 + r2)
            err = abs(actual - vout) / vout
            sum_err = abs((r1 + r2) - rtotal) / rtotal
            key = (err, sum_err)
            if best is None or key < best[0]:
                best = (key, r1, r2, actual)
    if best is None:
        fail("no E-series pair found near that Rtotal; try another --rtotal")
    _, r1, r2, actual = best
    return r1, r2, actual, (actual - vout) / vout * 100


def cmd_divider(args):
    vin, vout = parse_value(args.vin), parse_value(args.vout)
    if not 0 < vout < vin:
        fail("need 0 < vout < vin")
    ratio = vout / vin
    print(f"Vin={fmt_si(vin, 'V')}  Vout={fmt_si(vout, 'V')}  ratio R2/(R1+R2)={ratio:.6g}")
    if args.r1 is not None:
        r1 = parse_value(args.r1)
        r2 = r1 * vout / (vin - vout)
        print(f"exact  : R1={fmt_si(r1, 'ohm')}  R2={fmt_si(r2, 'ohm')}")
        _, near, _ = nearest_in_series(r2, args.series)
        actual = vin * near / (r1 + near)
        print(f"{args.series} R2 : {fmt_si(near, 'ohm')} -> Vout={actual:.4g} V "
              f"({(actual - vout) / vout * 100:+.2f} %)")
        return
    if args.r2 is not None:
        r2 = parse_value(args.r2)
        r1 = r2 * (vin - vout) / vout
        print(f"exact  : R1={fmt_si(r1, 'ohm')}  R2={fmt_si(r2, 'ohm')}")
        _, near, _ = nearest_in_series(r1, args.series)
        actual = vin * r2 / (near + r2)
        print(f"{args.series} R1 : {fmt_si(near, 'ohm')} -> Vout={actual:.4g} V "
              f"({(actual - vout) / vout * 100:+.2f} %)")
        return
    rtotal = parse_value(args.rtotal) if args.rtotal else 10e3
    r2_exact = rtotal * ratio
    r1_exact = rtotal - r2_exact
    print(f"exact @ Rtotal={fmt_si(rtotal, 'ohm')}: "
          f"R1={fmt_si(r1_exact, 'ohm')}  R2={fmt_si(r2_exact, 'ohm')}")
    r1, r2, actual, err = _divider_best_pair(vin, vout, rtotal, args.series)
    i_div = vin / (r1 + r2)
    print(f"best {args.series}: R1={fmt_si(r1, 'ohm')}  R2={fmt_si(r2, 'ohm')}  "
          f"(Rtotal={fmt_si(r1 + r2, 'ohm')})")
    print(f"  Vout={actual:.4g} V ({err:+.2f} %)  Idivider={fmt_si(i_div, 'A')}")


# ---------------------------------------------------------------- rc / rl / lc

def cmd_rc(args):
    given = {k: parse_value(v) for k, v in
             (("r", args.r), ("c", args.c), ("f", args.f)) if v is not None}
    if len(given) != 2:
        fail("rc needs exactly two of --r, --c, --f")
    if "f" not in given:
        r, c = given["r"], given["c"]
        f = 1 / (2 * math.pi * r * c)
    elif "r" not in given:
        f, c = given["f"], given["c"]
        r = 1 / (2 * math.pi * f * c)
    else:
        f, r = given["f"], given["r"]
        c = 1 / (2 * math.pi * f * r)
    print(f"R={fmt_si(r, 'ohm')}  C={fmt_si(c, 'F')}")
    print(f"f_c = {fmt_si(f, 'Hz')}   tau = R*C = {fmt_si(r * c, 's')}")


def cmd_rl(args):
    given = {k: parse_value(v) for k, v in
             (("r", args.r), ("l", args.l), ("f", args.f)) if v is not None}
    if len(given) != 2:
        fail("rl needs exactly two of --r, --l, --f")
    if "f" not in given:
        r, ind = given["r"], given["l"]
        f = r / (2 * math.pi * ind)
    elif "r" not in given:
        f, ind = given["f"], given["l"]
        r = 2 * math.pi * f * ind
    else:
        f, r = given["f"], given["r"]
        ind = r / (2 * math.pi * f)
    print(f"R={fmt_si(r, 'ohm')}  L={fmt_si(ind, 'H')}")
    print(f"f_c = R/(2*pi*L) = {fmt_si(f, 'Hz')}   tau = L/R = {fmt_si(ind / r, 's')}")


def cmd_lc(args):
    ind, c = parse_value(args.l), parse_value(args.c)
    f0 = 1 / (2 * math.pi * math.sqrt(ind * c))
    z0 = math.sqrt(ind / c)
    print(f"L={fmt_si(ind, 'H')}  C={fmt_si(c, 'F')}")
    print(f"f_0 = {fmt_si(f0, 'Hz')}   Z0 = sqrt(L/C) = {fmt_si(z0, 'ohm')}")


# ---------------------------------------------------------------- led / ohm

def cmd_led(args):
    vs, vf, i = parse_value(args.vsupply), parse_value(args.vf), parse_value(args.i)
    if vf >= vs:
        fail("Vf must be below Vsupply")
    if i <= 0:
        fail("LED current must be positive")
    r_exact = (vs - vf) / i
    _, r_std, _ = nearest_in_series(r_exact, "E24")
    i_actual = (vs - vf) / r_std
    p_r = i_actual ** 2 * r_std
    print(f"exact R = (Vs-Vf)/I = {fmt_si(r_exact, 'ohm')}")
    print(f"E24 pick: {fmt_si(r_std, 'ohm')} -> I={fmt_si(i_actual, 'A')}  "
          f"P_resistor={fmt_si(p_r, 'W')}")
    print("pick a resistor rated >= 2x P_resistor")


OHM_SOLVERS = {
    ("i", "v"): lambda i, v: (v / i, v * i),
    ("r", "v"): lambda r, v: (v / r, v * v / r),
    ("p", "v"): lambda p, v: (p / v, v * v / p),
    ("i", "r"): lambda i, r: (i * r, i * i * r),
    ("i", "p"): lambda i, p: (p / i, p / (i * i)),
    ("p", "r"): lambda p, r: (math.sqrt(p * r), math.sqrt(p / r)),
}


def cmd_ohm(args):
    given = {k: parse_value(v) for k, v in
             (("v", args.v), ("i", args.i), ("r", args.r), ("p", args.p))
             if v is not None}
    if len(given) != 2:
        fail("ohm needs exactly two of --v, --i, --r, --p")
    keys = tuple(sorted(given))
    a, b = given[keys[0]], given[keys[1]]
    out = {}
    if keys == ("i", "v"):
        out["r"], out["p"] = OHM_SOLVERS[keys](a, b)
    elif keys == ("r", "v"):
        out["i"], out["p"] = OHM_SOLVERS[keys](a, b)
    elif keys == ("p", "v"):
        out["i"], out["r"] = OHM_SOLVERS[keys](a, b)
    elif keys == ("i", "r"):
        out["v"], out["p"] = OHM_SOLVERS[keys](a, b)
    elif keys == ("i", "p"):
        out["v"], out["r"] = OHM_SOLVERS[keys](a, b)
    else:  # ("p", "r")
        out["v"], out["i"] = OHM_SOLVERS[keys](a, b)
    full = {**given, **out}
    print(f"V={fmt_si(full['v'], 'V')}  I={fmt_si(full['i'], 'A')}  "
          f"R={fmt_si(full['r'], 'ohm')}  P={fmt_si(full['p'], 'W')}")


# ---------------------------------------------------------------- awg

COPPER_RESISTIVITY = 1.724e-8  # ohm*m at 20 C

# Rough ampacity guidance (A): {gauge: (chassis wiring, bundled/power transmission)}
AWG_AMPACITY = {
    -3: (380, 302), -2: (328, 239), -1: (283, 190), 0: (245, 150),
    2: (181, 94), 4: (135, 60), 6: (101, 37), 8: (73, 24),
    10: (55, 15), 12: (41, 9.3), 14: (32, 5.9), 16: (22, 3.7),
    18: (16, 2.3), 20: (11, 1.5), 22: (7, 0.92), 24: (3.5, 0.577),
    26: (2.2, 0.361), 28: (1.4, 0.226), 30: (0.86, 0.142), 32: (0.53, 0.091),
}


def awg_to_number(text):
    """'0000'/'4/0' -> -3, '00' -> -1, '24' -> 24."""
    s = str(text).strip().upper().replace("AWG", "").strip()
    if "/" in s:  # e.g. 4/0
        zeros = int(s.split("/")[0])
        return 1 - zeros
    if set(s) == {"0"} and len(s) > 1:
        return 1 - len(s)
    try:
        n = int(s)
    except ValueError:
        fail(f"invalid AWG gauge '{text}'")
    if not -3 <= n <= 40:
        fail("gauge must be between 0000 (4/0) and 40")
    return n


def awg_diameter_mm(n):
    return 0.127 * 92 ** ((36 - n) / 39)


def awg_name(n):
    return "0" * (1 - n) if n <= 0 else str(n)


def print_awg(n):
    d_mm = awg_diameter_mm(n)
    area_mm2 = math.pi / 4 * d_mm ** 2
    kcmil = (d_mm / 0.0254) ** 2 / 1000  # circular mils / 1000
    r_per_m = COPPER_RESISTIVITY / (area_mm2 * 1e-6)
    print(f"AWG {awg_name(n)}: dia={d_mm:.4g} mm  area={area_mm2:.4g} mm2 "
          f"({kcmil:.4g} kcmil)")
    print(f"copper resistance: {fmt_si(r_per_m, 'ohm/m')} "
          f"({fmt_si(r_per_m * 1000, 'ohm/km')})")
    amp = AWG_AMPACITY.get(n)
    if amp:
        print(f"ampacity guidance: ~{amp[0]} A chassis, ~{amp[1]} A bundled "
              "(rough handbook values, not NEC/IPC design data)")
    else:
        print("ampacity guidance: n/a for this gauge (see NEC/IPC tables)")


def cmd_awg(args):
    if args.area:
        s = args.area.strip().lower().replace("mm²", "").replace("mm2", "")
        target = parse_value(s)
        best = min(range(-3, 41),
                   key=lambda n: abs(math.pi / 4 * awg_diameter_mm(n) ** 2 - target))
        print(f"nearest gauge for {target:.4g} mm2:")
        print_awg(best)
        return
    if args.gauge is None:
        fail("awg needs a gauge (e.g. 24, 0000, 4/0) or --area")
    print_awg(awg_to_number(args.gauge))


# ---------------------------------------------------------------- tolerance

def parse_term(text):
    try:
        v, pct = text.split(",")
        return parse_value(v), float(pct.rstrip("%")) / 100
    except (ValueError, SystemExit):
        fail(f"invalid --term '{text}' (expected value,pct e.g. 10k,1)")


def cmd_tolerance(args):
    if not args.term:
        fail("tolerance needs at least one --term value,pct")
    terms = [parse_term(t) for t in args.term]
    if args.mode == "sum":
        nominal = sum(v for v, _ in terms)
        lo = sum(v * (1 - t) for v, t in terms)
        hi = sum(v * (1 + t) for v, t in terms)
        rss = math.sqrt(sum((v * t) ** 2 for v, t in terms))
    else:  # product
        nominal = math.prod(v for v, _ in terms)
        lo = math.prod(v * (1 - t) for v, t in terms)
        hi = math.prod(v * (1 + t) for v, t in terms)
        rss = nominal * math.sqrt(sum(t ** 2 for _, t in terms))
    print(f"mode={args.mode}  terms={len(terms)}")
    print(f"nominal    : {nominal:.6g}")
    print(f"worst-case : {lo:.6g} .. {hi:.6g} "
          f"({(lo - nominal) / nominal * 100:+.3f} % / "
          f"{(hi - nominal) / nominal * 100:+.3f} %)")
    print(f"RSS (1-sigma-ish): +/- {rss:.6g} "
          f"({rss / nominal * 100:.3f} %)")
    print("note: models independent terms in a pure sum or product chain only; "
          "no correlated errors, no ratios/dividers")


# ---------------------------------------------------------------- thermal

def cmd_thermal(args):
    p = parse_value(args.p) if args.p else None
    ta = parse_value(args.ta)
    rths = [parse_value(x) for x in args.rth.split(",")]
    rth_total = sum(rths)
    chain = " + ".join(f"{r:g}" for r in rths)
    print(f"Rth chain: {chain} = {rth_total:g} K/W   Ta={ta:g} C")
    if p is not None:
        tj = ta + p * rth_total
        print(f"Tj = Ta + P*Rth = {ta:g} + {p:g}*{rth_total:g} = {tj:.4g} C")
    if args.tjmax is not None:
        tjmax = parse_value(args.tjmax)
        if tjmax <= ta:
            fail("tjmax must exceed ta")
        pmax = (tjmax - ta) / rth_total
        print(f"P_max for Tj<={tjmax:g} C: {pmax:.4g} W")
    if p is None and args.tjmax is None:
        fail("thermal needs --p and/or --tjmax")


# ---------------------------------------------------------------- battery

def cmd_battery(args):
    mah = parse_value(args.mah)
    derate = args.derate
    if args.phase:
        phases = [parse_term_phase(t) for t in args.phase]
        total_t = sum(t for _, t in phases)
        avg_i = sum(i * t for i, t in phases) / total_t
        print(f"duty cycle over {total_t:g} s: avg current = {fmt_si(avg_i, 'A')}")
    elif args.i:
        avg_i = parse_value(args.i)
    else:
        fail("battery needs --i or at least one --phase current,seconds")
    if avg_i <= 0:
        fail("current must be positive")
    hours = mah * derate / (avg_i * 1000)  # avg_i in A -> mA
    print(f"capacity {mah:g} mAh x derate {derate:g} / {fmt_si(avg_i, 'A')}")
    print(f"runtime: {hours:.4g} h ({hours / 24:.4g} days)")


def parse_term_phase(text):
    try:
        i, t = text.split(",")
        return parse_value(i), parse_value(t)
    except (ValueError, SystemExit):
        fail(f"invalid --phase '{text}' (expected current,seconds e.g. 15m,30)")


# ---------------------------------------------------------------- beam

# case: (deflection coefficient k in delta = P*L^3/(k*E*I), moment fn)
BEAM_CASES = {
    "cantilever-end": (3.0, lambda p, l: p * l),
    "cantilever-udl": (8.0, lambda p, l: p * l / 2),
    "simply-center": (48.0, lambda p, l: p * l / 4),
    "simply-udl": (384.0 / 5.0, lambda p, l: p * l / 8),
}


def cmd_beam(args):
    p = parse_value(args.p)
    length = parse_value(args.l)
    e = parse_value(args.e)
    if args.rect:
        try:
            w, h = (parse_value(x) for x in args.rect.split(","))
        except ValueError:
            fail("--rect expects w,h in meters (e.g. 0.02,0.005)")
        inertia = w * h ** 3 / 12
        print(f"rect section {w:g} x {h:g} m -> I = w*h^3/12 = {inertia:.6g} m^4")
    elif args.i:
        inertia = parse_value(args.i)
    else:
        fail("beam needs --i or --rect w,h")
    k, moment_fn = BEAM_CASES[args.case]
    delta = p * length ** 3 / (k * e * inertia)
    moment = moment_fn(p, length)
    load_kind = ("total distributed load W" if "udl" in args.case else "point load P")
    print(f"case={args.case}  L={length:g} m  E={e:.4g} Pa  I={inertia:.4g} m^4  "
          f"{load_kind}={p:g} N")
    print(f"max deflection = {fmt_si(delta, 'm')}")
    print(f"max bending moment = {moment:.4g} N*m")


# ---------------------------------------------------------------- bolt

METRIC_COARSE_PITCH = {  # mm
    "M3": 0.5, "M4": 0.7, "M5": 0.8, "M6": 1.0, "M8": 1.25, "M10": 1.5,
    "M12": 1.75, "M14": 2.0, "M16": 2.0, "M18": 2.5, "M20": 2.5,
}

PROOF_STRESS_MPA = {"8.8": (580, 600), "10.9": (830, 830), "12.9": (970, 970)}


def cmd_bolt(args):
    size = args.size.upper()
    if size not in METRIC_COARSE_PITCH:
        fail(f"unknown size '{args.size}' (supported: {', '.join(METRIC_COARSE_PITCH)})")
    if args.grade not in PROOF_STRESS_MPA:
        fail(f"unknown grade '{args.grade}' (supported: 8.8, 10.9, 12.9)")
    d = float(size[1:])
    pitch = METRIC_COARSE_PITCH[size]
    a_s = math.pi / 4 * (d - 0.9382 * pitch) ** 2  # mm^2
    sp_small, sp_large = PROOF_STRESS_MPA[args.grade]
    sp = sp_small if d <= 16 else sp_large
    f_proof = sp * a_s  # N (MPa * mm^2)
    preload = f_proof * args.pct / 100
    torque = args.k * preload * d / 1000  # N*m (d in mm -> m)
    print(f"{size} coarse (pitch {pitch} mm), grade {args.grade}")
    print(f"stress area As = pi/4*(d-0.9382*p)^2 = {a_s:.4g} mm2")
    print(f"proof stress {sp} MPa -> proof load = {fmt_si(f_proof, 'N')}")
    print(f"preload @ {args.pct:g}% proof = {fmt_si(preload, 'N')}")
    print(f"tightening torque T = k*F*d = {args.k:g}*{preload:.4g}*{d / 1000:g} "
          f"= {torque:.4g} N*m")
    print("assumes dry steel k~0.2; lubrication, plating and washers change k. "
          "Verify critical joints against the fastener spec.")


# ---------------------------------------------------------------- gear

def cmd_gear(args):
    teeth = [int(t) for t in args.teeth.split(",")]
    if len(teeth) < 2 or len(teeth) % 2 != 0:
        fail("--teeth needs an even count: driver,driven[,driver,driven...]")
    if any(t <= 0 for t in teeth):
        fail("tooth counts must be positive")
    overall = 1.0
    for stage, (drv, drn) in enumerate(zip(teeth[::2], teeth[1::2]), start=1):
        ratio = drn / drv
        overall *= ratio
        print(f"stage {stage}: {drv} -> {drn} teeth, ratio {ratio:.4g}:1")
    print(f"overall ratio: {overall:.4g}:1 (output slower/stronger)" if overall >= 1
          else f"overall ratio: {overall:.4g}:1 (output faster/weaker)")
    if args.rpm is not None:
        rpm = parse_value(args.rpm)
        print(f"output speed : {rpm / overall:.4g} rpm (input {rpm:g} rpm)")
    if args.torque is not None:
        tq = parse_value(args.torque)
        print(f"output torque: {tq * overall:.4g} N*m ideal, no losses "
              f"(input {tq:g} N*m)")


# ---------------------------------------------------------------- CLI

def build_parser():
    p = argparse.ArgumentParser(prog="eng_calc",
                                description="Everyday EE + ME calculators (SI units)")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("divider", help="resistor divider solve/synthesize")
    d.add_argument("--vin", required=True)
    d.add_argument("--vout", required=True)
    d.add_argument("--rtotal", help="target R1+R2 for synthesis (default 10k)")
    d.add_argument("--r1", help="fixed R1, solve R2")
    d.add_argument("--r2", help="fixed R2, solve R1")
    d.add_argument("--series", choices=["E12", "E24", "E96"], default="E24")
    d.set_defaults(func=cmd_divider)

    e = sub.add_parser("eseries", help="nearest standard E-series values")
    e.add_argument("value")
    e.add_argument("--series", choices=["E12", "E24", "E96"], default="E24")
    e.set_defaults(func=cmd_eseries)

    rc = sub.add_parser("rc", help="RC cutoff (give any two of r/c/f)")
    rc.add_argument("--r")
    rc.add_argument("--c")
    rc.add_argument("--f")
    rc.set_defaults(func=cmd_rc)

    rl = sub.add_parser("rl", help="RL cutoff (give any two of r/l/f)")
    rl.add_argument("--r")
    rl.add_argument("--l")
    rl.add_argument("--f")
    rl.set_defaults(func=cmd_rl)

    lc = sub.add_parser("lc", help="LC resonance + characteristic impedance")
    lc.add_argument("--l", required=True)
    lc.add_argument("--c", required=True)
    lc.set_defaults(func=cmd_lc)

    led = sub.add_parser("led", help="LED series resistor")
    led.add_argument("--vsupply", required=True)
    led.add_argument("--vf", required=True)
    led.add_argument("--i", required=True)
    led.set_defaults(func=cmd_led)

    ohm = sub.add_parser("ohm", help="Ohm's law: any two of V/I/R/P")
    ohm.add_argument("--v")
    ohm.add_argument("--i")
    ohm.add_argument("--r")
    ohm.add_argument("--p")
    ohm.set_defaults(func=cmd_ohm)

    awg = sub.add_parser("awg", help="AWG wire data (0000..40)")
    awg.add_argument("gauge", nargs="?")
    awg.add_argument("--area", help="find nearest gauge for area, e.g. 1.5mm2")
    awg.set_defaults(func=cmd_awg)

    tol = sub.add_parser("tolerance", help="worst-case + RSS for sum/product chains")
    tol.add_argument("--term", action="append",
                     help="value,pct — repeatable, e.g. --term 10k,1")
    tol.add_argument("--mode", choices=["sum", "product"], default="sum")
    tol.set_defaults(func=cmd_tolerance)

    th = sub.add_parser("thermal", help="junction temp through Rth chain")
    th.add_argument("--p", help="dissipated power in W")
    th.add_argument("--ta", required=True, help="ambient temp in C")
    th.add_argument("--rth", required=True, help="comma list, e.g. 3.1,0.5,4.2 K/W")
    th.add_argument("--tjmax", help="solve max power for this Tj limit")
    th.set_defaults(func=cmd_thermal)

    bat = sub.add_parser("battery", help="battery runtime")
    bat.add_argument("--mah", required=True)
    bat.add_argument("--i", help="constant load current")
    bat.add_argument("--phase", action="append",
                     help="current,seconds — repeatable for duty cycles")
    bat.add_argument("--derate", type=float, default=1.0)
    bat.set_defaults(func=cmd_battery)

    beam = sub.add_parser("beam", help="beam deflection + bending moment (SI)")
    beam.add_argument("--case", required=True, choices=sorted(BEAM_CASES))
    beam.add_argument("--l", required=True, help="length in m")
    beam.add_argument("--e", required=True, help="Young's modulus in Pa")
    beam.add_argument("--i", help="second moment of area in m^4")
    beam.add_argument("--rect", help="w,h in m — compute I for rectangle")
    beam.add_argument("--p", required=True,
                      help="point load or total UDL load in N")
    beam.set_defaults(func=cmd_beam)

    bolt = sub.add_parser("bolt", help="metric bolt tightening torque")
    bolt.add_argument("--size", required=True, help="M3..M20 (coarse)")
    bolt.add_argument("--grade", default="8.8", help="8.8 | 10.9 | 12.9")
    bolt.add_argument("--k", type=float, default=0.2, help="nut factor (dry steel ~0.2)")
    bolt.add_argument("--pct", type=float, default=75.0,
                      help="preload as %% of proof load")
    bolt.set_defaults(func=cmd_bolt)

    gear = sub.add_parser("gear", help="gear train ratio, speed, torque")
    gear.add_argument("--teeth", required=True,
                      help="driver,driven[,driver,driven...] e.g. 20,60")
    gear.add_argument("--rpm", help="input speed")
    gear.add_argument("--torque", help="input torque in N*m")
    gear.set_defaults(func=cmd_gear)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
