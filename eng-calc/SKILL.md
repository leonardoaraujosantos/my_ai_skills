---
name: eng-calc
description: Everyday electrical + mechanical engineering calculators - resistor dividers with E-series synthesis, RC/RL/LC filters, LED resistors, Ohm's law, AWG wire data, worst-case tolerance stacks, junction temperature, battery runtime, beam deflection, bolt torque, gear trains. Use when the user asks about a resistor divider, which E96 value, RC filter cutoff, LED resistor, wire gauge/AWG, worst-case tolerance, thermal resistance junction temp, beam deflection, bolt torque, or battery life.
argument-hint: <command> [values...]
---

# Engineering Calculators

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/eng-calc"
```

## Commands

```bash
python3 "$SKILL_DIR/eng_calc.py" <command> [options]
```

### Electrical

| Command | Description |
|---------|-------------|
| `divider` | Resistor divider: solve R1/R2 or synthesize best E12/E24/E96 pair |
| `eseries` | Nearest standard values (below/nearest/above) with % error |
| `rc` | RC cutoff + tau; give any two of `--r --c --f` |
| `rl` | RL cutoff + tau; give any two of `--r --l --f` |
| `lc` | LC resonance + characteristic impedance sqrt(L/C) |
| `led` | LED series resistor, E24 pick, resistor power |
| `ohm` | Ohm's law: any two of `--v --i --r --p` -> the other two |
| `awg` | AWG 0000..40: diameter, area, mΩ/m, rough ampacity; `--area 1.5mm2` -> nearest gauge |
| `tolerance` | Worst-case min/max + RSS for sum or product chains of `--term value,pct` |
| `thermal` | Tj through an Rth chain; `--tjmax` solves max power |
| `battery` | Runtime from mAh; constant `--i` or duty cycle via `--phase current,seconds` |

### Mechanical

| Command | Description |
|---------|-------------|
| `beam` | Max deflection + bending moment: `cantilever-end`, `cantilever-udl`, `simply-center`, `simply-udl`; `--rect w,h` computes I |
| `bolt` | Metric coarse M3-M20 tightening torque T = k*F*d (grades 8.8/10.9/12.9) |
| `gear` | Gear train: ratio per stage + overall, output speed/torque |

## Units

SI in, SI out. Component values accept SI suffixes: `k M G m u/µ n p` (e.g. `10k`, `100n`, `15m`, `4.7u`). Beam inputs are meters, pascals, newtons, m^4; thermal is W, °C, K/W; gear torque is N·m.

## Examples

```bash
# Divider: 12 V -> 3.3 V, pick best E24 pair near 10k total
python3 "$SKILL_DIR/eng_calc.py" divider --vin 12 --vout 3.3 --rtotal 10k
python3 "$SKILL_DIR/eng_calc.py" divider --vin 12 --vout 3.3 --r1 10k --series E96

# Nearest E96 value for 3456 ohm
python3 "$SKILL_DIR/eng_calc.py" eseries 3456 --series E96

# RC cutoff (10k, 100n -> 159.2 Hz); or solve R for 1 kHz
python3 "$SKILL_DIR/eng_calc.py" rc --r 10k --c 100n
python3 "$SKILL_DIR/eng_calc.py" rc --f 1k --c 100n

# LED resistor: 5 V supply, 2 V Vf, 10 mA -> 300 ohm E24
python3 "$SKILL_DIR/eng_calc.py" led --vsupply 5 --vf 2 --i 10m

# Ohm's law
python3 "$SKILL_DIR/eng_calc.py" ohm --v 12 --r 1k

# Wire: AWG 24 data; nearest gauge for 1.5 mm2
python3 "$SKILL_DIR/eng_calc.py" awg 24
python3 "$SKILL_DIR/eng_calc.py" awg --area 1.5mm2

# Tolerance stack: 100 +/-1% plus 200 +/-2% (sum), or product chain
python3 "$SKILL_DIR/eng_calc.py" tolerance --term 100,1 --term 200,2 --mode sum
python3 "$SKILL_DIR/eng_calc.py" tolerance --term 3.3,1 --term 2,0.5 --mode product

# Thermal: 2.5 W into RthJC+RthCS+RthSA at 40 C ambient; max P for Tj 125 C
python3 "$SKILL_DIR/eng_calc.py" thermal --p 2.5 --ta 40 --rth 3.1,0.5,4.2 --tjmax 125

# Battery: 2000 mAh at 15 mA with 80% derating; or duty-cycled load
python3 "$SKILL_DIR/eng_calc.py" battery --mah 2000 --i 15m --derate 0.8
python3 "$SKILL_DIR/eng_calc.py" battery --mah 2000 --phase 100m,1 --phase 1m,99

# Beam: 100 N end load on 0.5 m steel cantilever
python3 "$SKILL_DIR/eng_calc.py" beam --case cantilever-end --l 0.5 --e 200e9 --i 8.3e-9 --p 100
python3 "$SKILL_DIR/eng_calc.py" beam --case simply-center --l 1 --e 200e9 --rect 0.02,0.005 --p 500

# Bolt: M6 grade 8.8 dry -> ~10.5 N*m
python3 "$SKILL_DIR/eng_calc.py" bolt --size M6 --grade 8.8

# Gear train: 20->60 then 15->45 teeth
python3 "$SKILL_DIR/eng_calc.py" gear --teeth 20,60,15,45 --rpm 1000 --torque 2
```

## Notes on `divider`

With `--rtotal` (default 10k) it searches E-series pairs whose sum stays within 2x of the target, minimizing Vout error (ties broken by sum closeness). With `--r1` or `--r2` fixed it solves the other resistor exactly and shows the nearest standard value with the resulting Vout error.

## Notes on `tolerance`

Models independent terms combined in a pure sum or a pure product: worst-case takes every term at its extreme; RSS root-sum-squares the individual contributions. It does not model correlated errors, ratios/dividers, or mixed expressions.

## Scope and honesty notes

- Ampacity figures are rough handbook guidance for chassis vs bundled wiring - not NEC/IPC design data. Do real derating for anything that matters.
- Bolt torque assumes dry steel nut factor k~=0.2 and preload at 75% of proof load by default. Lubrication, plating, and washers change k substantially - verify critical joints against the fastener/OEM spec.
- Wire resistance uses copper at 20 C (rho = 1.724e-8 ohm*m).
- Beam formulas are classic Euler-Bernoulli small-deflection cases; for UDL cases `--p` is the TOTAL distributed load W = w*L in newtons.
- Gear output torque is ideal (no efficiency losses).
- No generic unit conversion command - that is out of scope for this skill.
