---
name: rf-tools
description: RF/microwave engineering calculators - link budgets, path loss, VSWR, unit conversions, noise cascades, matching networks, microstrip, attenuators, skin depth. Use when working on link budget, path loss, VSWR/return loss, dBm to volts/watts, noise figure cascade, impedance matching, microstrip impedance, or attenuator design.
argument-hint: <command> [values...]
---

# RF Tools

## Script Location

```bash
SKILL_DIR="$HOME/.claude/skills/rf-tools"
```

## Commands

```bash
python3 "$SKILL_DIR/rf_tools.py" <command> [options]
```

| Command | Description |
|---------|-------------|
| `fspl` | Free-space path loss (dB) and one-way delay |
| `linkbudget` | Received power via FSPL, margin vs sensitivity |
| `vswr` | Convert between VSWR, return loss, and \|Γ\|; mismatch loss, reflected % |
| `db` | dBm ↔ W, dBm ↔ V rms, dBm ↔ dBµV (any impedance) |
| `friis` | Cascaded noise figure and gain, noise floor |
| `match` | L-network between two resistive impedances (both topologies) |
| `wavelength` | λ, λ/2, λ/4 with optional velocity factor |
| `microstrip` | Synthesize width for target Z0 or analyze a given width (Hammerstad-Jensen) |
| `attenuator` | Pi/tee attenuator resistors, exact + nearest E24 |
| `skin` | Skin depth and surface resistance (copper, aluminum, gold, silver) |

Frequencies accept SI suffixes: `2.4G`, `915M`, `433.92MHz`, `32k`. Distances accept `km/m/cm/mm`; small lengths accept `mm/mil/um`. Bad input prints an error and exits non-zero.

## Options

| Command | Options |
|---------|---------|
| `fspl` | `-f <freq> -d <dist>` |
| `linkbudget` | `--ptx dBm --gtx dBi --grx dBi -f freq -d dist [--losses dB] [--sens dBm]` |
| `vswr` | `<vswr>` OR `-rl <dB>` OR `-g <\|gamma\|>` (exactly one) |
| `db` | `{dbm2w,w2dbm,dbm2v,v2dbm,dbm2dbuv,dbuv2dbm} <value> [--z 50]` |
| `friis` | `--stage gain_db,nf_db` (repeatable, chain order) `[--bw <bw>]` |
| `match` | `--rs <ohm> --rl <ohm> -f <freq>` |
| `wavelength` | `-f <freq> [--vf 0.66]` |
| `microstrip` | `--er <er> -h <height>` plus `-z <target Z0>` or `--width <w>`; `[-f freq]` for guided λ |
| `attenuator` | `-a <dB> [-z 50] [--topology pi\|tee]` |
| `skin` | `-f <freq> [--material copper]` |

## Examples

```bash
# Quick lookups
python3 "$SKILL_DIR/rf_tools.py" fspl -f 2.4G -d 100m        # 80.05 dB, 333.6 ns
python3 "$SKILL_DIR/rf_tools.py" vswr 2.0                    # RL 9.54 dB, |Γ| 0.333
python3 "$SKILL_DIR/rf_tools.py" db dbm2v 0                  # 223.6 mV rms into 50 Ω
python3 "$SKILL_DIR/rf_tools.py" wavelength -f 2.4G          # λ = 12.49 cm
python3 "$SKILL_DIR/rf_tools.py" attenuator -a 3 --topology pi   # 292.4 Ω / 17.61 Ω
python3 "$SKILL_DIR/rf_tools.py" skin -f 1G                  # 2.09 µm in copper

# Board design
python3 "$SKILL_DIR/rf_tools.py" microstrip -z 50 --er 4.4 -h 1.6mm -f 2.4G
python3 "$SKILL_DIR/rf_tools.py" match --rs 25 --rl 50 -f 2.4G
```

### End-to-end 2.4 GHz link budget

Node with a 20 dBm radio and 2 dBi antennas, 100 m outdoors, 2 dB of cable/connector losses, receiver sensitivity -90 dBm:

```bash
# 1. Path loss at range
python3 "$SKILL_DIR/rf_tools.py" fspl -f 2.4G -d 100m
#    FSPL = 80.05 dB

# 2. Received power and margin
python3 "$SKILL_DIR/rf_tools.py" linkbudget --ptx 20 --gtx 2 --grx 2 \
    -f 2.4G -d 100m --losses 2 --sens -90
#    Prx = -58.05 dBm, margin = 31.95 dB [OK]

# 3. Receiver front-end noise: LNA (G=15 dB, NF=1 dB) into mixer (G=-7 dB, NF=7 dB)
python3 "$SKILL_DIR/rf_tools.py" friis --stage 15,1 --stage -7,7 --bw 1M
#    total NF = 1.417 dB, floor in 1 MHz = -112.56 dBm
#    -> SNR at sensitivity: -90 - (-112.56) = 22.6 dB

# 4. Is the antenna match eating margin? Datasheet says VSWR 2:1 worst case
python3 "$SKILL_DIR/rf_tools.py" vswr 2.0
#    mismatch loss only 0.51 dB - fine
```

Gain/NF/sensitivity numbers extracted from datasheets (see the `datasheet` skill) plug straight into `friis --stage` and `linkbudget --sens`.
