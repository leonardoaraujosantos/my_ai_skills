#!/usr/bin/env python3
"""rf-tools: RF/microwave engineering calculators (Python 3 stdlib only)."""

import argparse
import math
import sys

C0 = 299792458.0          # speed of light, m/s
MU0 = 4 * math.pi * 1e-7  # vacuum permeability, H/m
KT_DBM_HZ = 10 * math.log10(1.380649e-23 * 290.0) + 30  # ~ -174 dBm/Hz

E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]

# conductivity in S/m
MATERIALS = {"copper": 5.80e7, "aluminum": 3.77e7, "gold": 4.10e7, "silver": 6.30e7}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------- unit parsing ----------

def parse_freq(text):
    """Frequency with optional k/M/G suffix (and optional 'Hz'): 2.4G, 915M, 32k."""
    s = text.strip()
    if s.lower().endswith("hz"):
        s = s[:-2]
    mult = 1.0
    if s and s[-1].lower() in "kmg":
        mult = {"k": 1e3, "m": 1e6, "g": 1e9}[s[-1].lower()]
        s = s[:-1]
    try:
        f = float(s) * mult
    except ValueError:
        die(f"invalid frequency '{text}' (use e.g. 2.4G, 915M, 433.92MHz, 2400000000)")
    if f <= 0:
        die(f"frequency must be > 0, got '{text}'")
    return f


def _parse_length(text, units, what):
    s = text.strip().lower()
    mult = 1.0
    for suffix, m in units:
        if s.endswith(suffix):
            mult = m
            s = s[: -len(suffix)]
            break
    try:
        value = float(s) * mult
    except ValueError:
        die(f"invalid {what} '{text}'")
    if value <= 0:
        die(f"{what} must be > 0, got '{text}'")
    return value


def parse_dist(text):
    """Distance with optional km/m/cm/mm suffix; bare number = meters."""
    return _parse_length(text, [("km", 1e3), ("cm", 1e-2), ("mm", 1e-3), ("m", 1.0)], "distance")


def parse_len(text):
    """Small length with optional mm/mil/um/cm/m suffix; bare number = meters."""
    units = [("mil", 25.4e-6), ("um", 1e-6), ("µm", 1e-6),
             ("mm", 1e-3), ("cm", 1e-2), ("m", 1.0)]
    return _parse_length(text, units, "length")


# ---------- formatting ----------

def si(value, unit):
    """Engineering-notation formatting: 1.658e-9 H -> '1.658 nH'."""
    prefixes = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1.0, ""),
                (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"), (1e-12, "p"), (1e-15, "f")]
    if value == 0:
        return f"0 {unit}"
    for factor, prefix in prefixes:
        if abs(value) >= factor:
            return f"{value / factor:.4g} {prefix}{unit}"
    return f"{value:.4g} {unit}"


def fmt_freq(f):
    return si(f, "Hz")


# ---------- core formulas ----------

def fspl_db(freq, dist):
    return 20 * math.log10(4 * math.pi * dist * freq / C0)


def gamma_to_all(gamma):
    vswr = math.inf if gamma >= 1 else (1 + gamma) / (1 - gamma)
    rl = math.inf if gamma == 0 else -20 * math.log10(gamma)
    mismatch = math.inf if gamma >= 1 else -10 * math.log10(1 - gamma * gamma) + 0.0
    return vswr, rl, mismatch, gamma * gamma * 100


def microstrip_synthesize(z0, er):
    """Hammerstad-Jensen synthesis: W/h for target Z0."""
    a = z0 / 60 * math.sqrt((er + 1) / 2) + (er - 1) / (er + 1) * (0.23 + 0.11 / er)
    wh = 8 * math.exp(a) / (math.exp(2 * a) - 2)
    if wh > 2:
        b = 377 * math.pi / (2 * z0 * math.sqrt(er))
        wh = (2 / math.pi) * (b - 1 - math.log(2 * b - 1)
                              + (er - 1) / (2 * er) * (math.log(b - 1) + 0.39 - 0.61 / er))
    return wh


def microstrip_analyze(wh, er):
    """Hammerstad-Jensen analysis: Z0 and effective er for a given W/h."""
    if wh < 1:
        eeff = (er + 1) / 2 + (er - 1) / 2 * ((1 + 12 / wh) ** -0.5 + 0.04 * (1 - wh) ** 2)
        z0 = 60 / math.sqrt(eeff) * math.log(8 / wh + wh / 4)
    else:
        eeff = (er + 1) / 2 + (er - 1) / 2 / math.sqrt(1 + 12 / wh)
        z0 = 120 * math.pi / (math.sqrt(eeff) * (wh + 1.393 + 0.667 * math.log(wh + 1.444)))
    return z0, eeff


def nearest_e24(r):
    exp = math.floor(math.log10(r))
    candidates = [v * 10 ** e for e in (exp - 1, exp, exp + 1) for v in E24]
    return min(candidates, key=lambda c: abs(c - r))


# ---------- commands ----------

def cmd_fspl(args):
    loss = fspl_db(args.freq, args.dist)
    delay = args.dist / C0
    print(f"Free-space path loss (Friis: FSPL = 20*log10(4*pi*d*f/c))")
    print(f"  f = {fmt_freq(args.freq)},  d = {si(args.dist, 'm')}")
    print(f"  FSPL          = {loss:.2f} dB")
    print(f"  one-way delay = {si(delay, 's')}")


def cmd_linkbudget(args):
    loss = fspl_db(args.freq, args.dist)
    prx = args.ptx + args.gtx + args.grx - loss - args.losses
    print("Link budget (Prx = Ptx + Gtx + Grx - FSPL - losses)")
    print(f"  f = {fmt_freq(args.freq)},  d = {si(args.dist, 'm')}")
    print(f"  Ptx = {args.ptx:.2f} dBm,  Gtx = {args.gtx:.2f} dBi,  Grx = {args.grx:.2f} dBi,"
          f"  extra losses = {args.losses:.2f} dB")
    print(f"  FSPL = {loss:.2f} dB")
    print(f"  Prx  = {prx:.2f} dBm")
    if args.sens is not None:
        margin = prx - args.sens
        verdict = "OK" if margin >= 0 else "LINK FAILS"
        print(f"  sensitivity = {args.sens:.2f} dBm  ->  margin = {margin:.2f} dB  [{verdict}]")


def cmd_vswr(args):
    given = [v is not None for v in (args.vswr, args.rl, args.gamma)]
    if sum(given) != 1:
        die("give exactly one of: VSWR (positional), -rl <dB>, or -g <|gamma|>")
    if args.vswr is not None:
        if args.vswr < 1:
            die(f"VSWR must be >= 1, got {args.vswr}")
        gamma, src = (args.vswr - 1) / (args.vswr + 1), f"VSWR = {args.vswr}"
    elif args.rl is not None:
        if args.rl <= 0:
            die(f"return loss must be > 0 dB, got {args.rl}")
        gamma, src = 10 ** (-args.rl / 20), f"RL = {args.rl} dB"
    else:
        if not 0 <= args.gamma < 1:
            die(f"|gamma| must be in [0, 1), got {args.gamma}")
        gamma, src = args.gamma, f"|gamma| = {args.gamma}"

    vswr, rl, mismatch, refl_pct = gamma_to_all(gamma)
    rl_s = "inf" if math.isinf(rl) else f"{rl:.2f} dB"
    print(f"Reflection conversions (gamma = (VSWR-1)/(VSWR+1), RL = -20*log10|gamma|) from {src}")
    print(f"  VSWR           = {vswr:.3f}")
    print(f"  return loss    = {rl_s}")
    print(f"  |gamma|        = {gamma:.4f}")
    print(f"  mismatch loss  = {mismatch:.3f} dB")
    print(f"  reflected pwr  = {refl_pct:.2f} %")


def cmd_db(args):
    z = args.z
    if z <= 0:
        die(f"impedance must be > 0, got {z}")
    v = args.value
    dbuv_offset = 90 + 10 * math.log10(z)  # dBuV = dBm + 90 + 10*log10(Z)
    conversions = {
        "dbm2w":    lambda: (f"{v} dBm", si(1e-3 * 10 ** (v / 10), "W"), "P = 1mW * 10^(dBm/10)"),
        "w2dbm":    lambda: (si(v, "W"), f"{10 * math.log10(v / 1e-3):.2f} dBm", "dBm = 10*log10(P/1mW)"),
        "dbm2v":    lambda: (f"{v} dBm", si(math.sqrt(1e-3 * 10 ** (v / 10) * z), "V rms"), "V = sqrt(P*Z)"),
        "v2dbm":    lambda: (si(v, "V rms"), f"{10 * math.log10(v * v / z / 1e-3):.2f} dBm", "P = V^2/Z"),
        "dbm2dbuv": lambda: (f"{v} dBm", f"{v + dbuv_offset:.2f} dBuV", "dBuV = dBm + 90 + 10*log10(Z)"),
        "dbuv2dbm": lambda: (f"{v} dBuV", f"{v - dbuv_offset:.2f} dBm", "dBm = dBuV - 90 - 10*log10(Z)"),
    }
    if args.conversion in ("w2dbm", "v2dbm") and v <= 0:
        die(f"power/voltage must be > 0, got {v}")
    src, dst, formula = conversions[args.conversion]()
    print(f"Power/voltage conversion ({formula}, Z = {z:g} ohm)")
    print(f"  {src}  ->  {dst}")


def parse_stage(text):
    parts = text.split(",")
    if len(parts) != 2:
        die(f"invalid stage '{text}' (expected gain_db,nf_db e.g. 15,1)")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        die(f"invalid stage '{text}' (expected gain_db,nf_db e.g. 15,1)")


def cmd_friis(args):
    if not args.stage:
        die("at least one --stage gain_db,nf_db is required")
    stages = [parse_stage(s) for s in args.stage]
    f_total, g_cascade = 0.0, 1.0
    for i, (gain_db, nf_db) in enumerate(stages, 1):
        f_lin = 10 ** (nf_db / 10)
        f_total += (f_lin - 1) / g_cascade if i > 1 else f_lin
        g_cascade *= 10 ** (gain_db / 10)
        print(f"  stage {i}: gain = {gain_db:+.2f} dB, NF = {nf_db:.2f} dB"
              f"  ->  cascade NF so far = {10 * math.log10(f_total):.3f} dB")
    nf_total = 10 * math.log10(f_total)
    gain_total = 10 * math.log10(g_cascade)
    print("Friis cascade (F = F1 + (F2-1)/G1 + (F3-1)/(G1*G2) + ...)")
    print(f"  total gain            = {gain_total:.2f} dB")
    print(f"  total NF              = {nf_total:.3f} dB")
    print(f"  input noise floor     = {KT_DBM_HZ + nf_total:.2f} dBm/Hz  (kT290 + NF)")
    if args.bw is not None:
        floor = KT_DBM_HZ + nf_total + 10 * math.log10(args.bw)
        print(f"  noise floor in {fmt_freq(args.bw)} BW = {floor:.2f} dBm")


def cmd_match(args):
    rs, rl, freq = args.rs, args.rl, args.freq
    if rs <= 0 or rl <= 0:
        die("source and load resistances must be > 0")
    if math.isclose(rs, rl):
        die("Rs == Rl: already matched, no L-network needed")
    r_high, r_low = max(rs, rl), min(rs, rl)
    high_side = "source" if rs > rl else "load"
    low_side = "load" if rs > rl else "source"
    q = math.sqrt(r_high / r_low - 1)
    xs, xp = q * r_low, r_high / q
    w = 2 * math.pi * freq
    print(f"L-network match (Q = sqrt(Rhigh/Rlow - 1)) at f = {fmt_freq(freq)}")
    print(f"  Rs = {rs:g} ohm, Rl = {rl:g} ohm  ->  Q = {q:.3f}")
    print(f"  series arm on the {low_side} ({r_low:g} ohm) side, shunt arm across the "
          f"{high_side} ({r_high:g} ohm) side")
    print(f"  topology 1 (low-pass):  series L = {si(xs / w, 'H')},  shunt C = {si(1 / (w * xp), 'F')}")
    print(f"  topology 2 (high-pass): series C = {si(1 / (w * xs), 'F')},  shunt L = {si(xp / w, 'H')}")


def cmd_wavelength(args):
    if not 0 < args.vf <= 1:
        die(f"velocity factor must be in (0, 1], got {args.vf}")
    lam = C0 * args.vf / args.freq
    print(f"Wavelength (lambda = c*vf/f) at f = {fmt_freq(args.freq)}, vf = {args.vf:g}")
    for name, frac in (("lambda  ", 1), ("lambda/2", 2), ("lambda/4", 4)):
        v = lam / frac
        print(f"  {name} = {v:.6g} m = {v * 100:.4g} cm = {v * 1000:.4g} mm")


def cmd_microstrip(args):
    er, h = args.er, args.height
    if er < 1:
        die(f"relative permittivity must be >= 1, got {er}")
    if args.width is None and args.z is None:
        die("give either -z <target Z0> (synthesize) or --width <w> (analyze)")
    if args.width is not None:
        wh = args.width / h
        mode = f"analysis of W = {si(args.width, 'm')}"
    else:
        wh = microstrip_synthesize(args.z, er)
        mode = f"synthesis for Z0 = {args.z:g} ohm  ->  W = {si(wh * h, 'm')}  (W/h = {wh:.4f})"
    z0, eeff = microstrip_analyze(wh, er)
    print(f"Microstrip (Hammerstad-Jensen), er = {er:g}, h = {si(h, 'm')}")
    print(f"  {mode}")
    print(f"  Z0           = {z0:.2f} ohm")
    print(f"  effective er = {eeff:.4f}")
    if args.freq is not None:
        lam_g = C0 / (args.freq * math.sqrt(eeff))
        print(f"  guided wavelength at {fmt_freq(args.freq)}: "
              f"lambda_g = {si(lam_g, 'm')},  lambda_g/4 = {si(lam_g / 4, 'm')}")


def cmd_attenuator(args):
    a, z = args.atten, args.z
    if a <= 0 or z <= 0:
        die("attenuation (dB) and impedance must be > 0")
    k = 10 ** (a / 20)
    if args.topology == "pi":
        shunt = z * (k + 1) / (k - 1)
        series = z / 2 * (k * k - 1) / k
        legs = [("shunt (x2)", shunt), ("series", series)]
    else:
        series = z * (k - 1) / (k + 1)
        shunt = 2 * z * k / (k * k - 1)
        legs = [("series (x2)", series), ("shunt", shunt)]
    print(f"{args.topology.capitalize()} attenuator: {a:g} dB, Z0 = {z:g} ohm")
    for name, r in legs:
        print(f"  {name:11s} R = {r:.2f} ohm  (nearest E24: {nearest_e24(r):g} ohm)")


def cmd_skin(args):
    sigma = MATERIALS.get(args.material)
    if sigma is None:
        die(f"unknown material '{args.material}' (choose from: {', '.join(MATERIALS)})")
    delta = 1 / math.sqrt(math.pi * args.freq * MU0 * sigma)
    rs = 1 / (sigma * delta)
    print(f"Skin depth (delta = 1/sqrt(pi*f*mu0*sigma)), {args.material}, "
          f"sigma = {sigma:.3g} S/m, f = {fmt_freq(args.freq)}")
    print(f"  skin depth         = {si(delta, 'm')}")
    print(f"  surface resistance = {rs * 1000:.4g} mohm/sq")


# ---------- CLI ----------

def build_parser():
    p = argparse.ArgumentParser(prog="rf_tools.py",
                                description="RF/microwave engineering calculators")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("fspl", help="free-space path loss and one-way delay")
    sp.add_argument("-f", "--freq", type=parse_freq, required=True)
    sp.add_argument("-d", "--dist", type=parse_dist, required=True)
    sp.set_defaults(func=cmd_fspl)

    sp = sub.add_parser("linkbudget", help="received power via FSPL and link margin")
    sp.add_argument("--ptx", type=float, required=True, help="TX power, dBm")
    sp.add_argument("--gtx", type=float, required=True, help="TX antenna gain, dBi")
    sp.add_argument("--grx", type=float, required=True, help="RX antenna gain, dBi")
    sp.add_argument("-f", "--freq", type=parse_freq, required=True)
    sp.add_argument("-d", "--dist", type=parse_dist, required=True)
    sp.add_argument("--losses", type=float, default=0.0, help="extra losses, dB")
    sp.add_argument("--sens", type=float, help="RX sensitivity, dBm")
    sp.set_defaults(func=cmd_linkbudget)

    sp = sub.add_parser("vswr", help="convert between VSWR, return loss, and |gamma|")
    sp.add_argument("vswr", nargs="?", type=float, help="VSWR value (>= 1)")
    sp.add_argument("-rl", "--return-loss", dest="rl", type=float, help="return loss, dB")
    sp.add_argument("-g", "--gamma", type=float, help="|gamma| in [0, 1)")
    sp.set_defaults(func=cmd_vswr)

    sp = sub.add_parser("db", help="dBm/W/V(rms)/dBuV conversions")
    sp.add_argument("conversion",
                    choices=["dbm2w", "w2dbm", "dbm2v", "v2dbm", "dbm2dbuv", "dbuv2dbm"])
    sp.add_argument("value", type=float)
    sp.add_argument("--z", type=float, default=50.0, help="impedance, ohm (default 50)")
    sp.set_defaults(func=cmd_db)

    sp = sub.add_parser("friis", help="cascaded noise figure and gain")
    sp.add_argument("--stage", action="append", metavar="GAIN_DB,NF_DB",
                    help="repeatable, in signal-chain order (e.g. --stage 15,1)")
    sp.add_argument("--bw", type=parse_freq, help="bandwidth for integrated noise floor")
    sp.set_defaults(func=cmd_friis)

    sp = sub.add_parser("match", help="L-network between two resistive impedances")
    sp.add_argument("--rs", type=float, required=True, help="source resistance, ohm")
    sp.add_argument("--rl", type=float, required=True, help="load resistance, ohm")
    sp.add_argument("-f", "--freq", type=parse_freq, required=True)
    sp.set_defaults(func=cmd_match)

    sp = sub.add_parser("wavelength", help="lambda, lambda/2, lambda/4")
    sp.add_argument("-f", "--freq", type=parse_freq, required=True)
    sp.add_argument("--vf", type=float, default=1.0, help="velocity factor (default 1.0)")
    sp.set_defaults(func=cmd_wavelength)

    # add_help=False frees -h for substrate height
    sp = sub.add_parser("microstrip", add_help=False,
                        help="microstrip synthesis/analysis (Hammerstad-Jensen)")
    sp.add_argument("--help", action="help", help="show this help message and exit")
    sp.add_argument("-z", type=float, help="target Z0, ohm (synthesize width)")
    sp.add_argument("--width", type=parse_len, help="trace width (analyze Z0)")
    sp.add_argument("--er", type=float, required=True, help="substrate relative permittivity")
    sp.add_argument("-h", "--height", type=parse_len, required=True,
                    help="substrate height (e.g. 1.6mm, 10mil)")
    sp.add_argument("-f", "--freq", type=parse_freq, help="print guided wavelength")
    sp.set_defaults(func=cmd_microstrip)

    sp = sub.add_parser("attenuator", help="pi/tee attenuator resistor values")
    sp.add_argument("-a", "--atten", type=float, required=True, help="attenuation, dB")
    sp.add_argument("-z", type=float, default=50.0, help="impedance, ohm (default 50)")
    sp.add_argument("--topology", choices=["pi", "tee"], default="pi")
    sp.set_defaults(func=cmd_attenuator)

    sp = sub.add_parser("skin", help="skin depth and surface resistance")
    sp.add_argument("-f", "--freq", type=parse_freq, required=True)
    sp.add_argument("--material", default="copper", help=", ".join(MATERIALS))
    sp.set_defaults(func=cmd_skin)

    return p


def join_stage_values(argv):
    """Rewrite ['--stage', '-7,7'] as ['--stage=-7,7'] so negative gains parse."""
    out = []
    it = iter(argv)
    for arg in it:
        value = next(it, None) if arg == "--stage" else None
        out.append(arg if value is None else f"--stage={value}")
    return out


def main(argv=None):
    argv = join_stage_values(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
