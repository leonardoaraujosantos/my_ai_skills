---
name: spice
description: Run analog circuit simulations with ngspice in batch mode and get readable results - AC/transient/DC sweeps and operating points from netlists or bundled templates (RC filter, divider, RLC, rectifier, MOSFET switch, op-amp), with CSV output and ASCII plots. Use when the user says "simulate this circuit", "spice simulation", "will this filter/bias/divider work", "AC/transient/DC sweep", or "ngspice".
argument-hint: <netlist.cir | template-name> [--analysis ac|tran|dc|op] [options]
---

# SPICE Simulation

Simulate analog circuits with ngspice (batch mode, no GUI) and read the results as tables, CSV, and ASCII plots.

## Requirements

ngspice must be on PATH:

```bash
which ngspice || brew install ngspice      # macOS
# Debian/Ubuntu: sudo apt install ngspice
```

The helper script is Python 3 stdlib only:

```bash
SKILL_DIR="$HOME/.claude/skills/spice"
python3 "$SKILL_DIR/scripts/spice_run.py" <command> ...
```

## Commands

| Command | What it does |
|---|---|
| `run <netlist.cir> [-o out.csv]` | Run `ngspice -b`; convert `wrdata` output to CSV; print points/columns/min/max summary. If the netlist has no `.control` block, one is injected from `--analysis` (`op` \| `ac` \| `tran` \| `'dc V1 0 5 0.1'` \| any full ngspice analysis line) probing `--probe v(out)` nodes (repeatable; for `ac`, `v(x)` becomes `vdb(x)` + `vp(x)`). |
| `op <netlist.cir>` | DC operating point: node voltages and source currents as a table. |
| `plot <out.csv> [--col NAME] [--log-x] [--db NAME]` | 60x20 ASCII plot of a column vs the first column. `--log-x` for frequency sweeps; `--db` plots `20*log10(\|col\|)`. |
| `template list` | Show bundled templates with one-line descriptions. |
| `template <name> [-o dest.cir]` | Copy a template into the working directory for editing. |

## Templates

| Template | Circuit | Expected physics |
|---|---|---|
| `rc_lowpass` | RC low-pass, AC sweep | -3 dB at 1/(2piRC) = 159 Hz, -20 dB/dec |
| `divider` | Resistor divider, op point | Vout = Vin*R2/(R1+R2) = 2.5 V |
| `rlc_resonant` | Series RLC, AC sweep | 0 dB peak at 1/(2pi sqrt(LC)) = 1592 Hz, Q = 10 |
| `diode_rectifier` | Half-wave rectifier + cap, transient | Peak ~ Vamp - 0.7 V, sawtooth ripple ~ I/(f*C) |
| `mosfet_switch` | NMOS low-side switch, transient | Drain = VDD off, near 0 V on |
| `opamp_inverting` | Inverting amp (ideal 1-pole op-amp), AC sweep | 20 dB gain, -3 dB at GBW/(1+RF/RIN) ~ 91 kHz |

## Workflow

1. **Start from a template**: `template list`, then `template rc_lowpass` (or write a netlist directly).
2. **Edit values**: every template puts its knobs in `.param` lines at the top; each line is commented.
3. **Run**: `run rc_lowpass.cir` — read the min/max summary first (sanity check ranges).
4. **Plot**: `plot rc_lowpass.csv --col "vdb(out)" --log-x` to see the rolloff or transient shape.
5. **Interpret**: extract the numbers that answer the question (e.g. find the -3 dB row in the CSV) and compare against the analytic expectation.

## Netlist crash course

1. First line is a title comment; `*` starts a comment line, `;` an end-of-line comment.
2. Node `0` is ground; other nodes are arbitrary names (`in`, `out`, `n1`).
3. `R1 a b 10k` / `C1 a b 100n` / `L1 a b 10m` — resistor/cap/inductor between nodes a,b.
4. `V1 in 0 DC 5 AC 1` — voltage source; `SIN(0 10 50)` and `PULSE(0 5 1m 1u 1u 2m 4m)` for transients. `I` = current source.
5. `.param RVAL=10k` defines a parameter; reference it as `{RVAL}` in element lines.
6. `.model NAME NMOS(level=1 VTO=2 KP=50u)` / `.model D1 D(Is=4n)` — device models for `M`/`D` elements.
7. `.subckt NAME pins ... .ends` defines a block; instantiate with `X1 pins NAME`.
8. `.control ... .endc` holds interactive commands run in batch mode: an analysis (`ac dec 40 1 10Meg`, `tran 100u 100m`, `op`, `dc V1 0 5 0.1`) then `wrdata file vecs` to dump data.
9. In `.control`, use `vdb(out)`/`vm(out)`/`vp(out)` for dB/magnitude/phase of AC results, and `set wr_vecnames` + `set wr_singlescale` so the dump has named columns and one x column.
10. End the file with `.end`.

## Rules

- **Always report the actual simulation output** — the measured -3 dB frequency, the simulated node voltage, the observed ripple — not the textbook value.
- **Never claim expected behavior without running it** when ngspice is available; run the netlist and quote the numbers.
- If ngspice is **not installed**, say so, offer `brew install ngspice`, and **state clearly that any analysis is analytic reasoning, not simulation**.
- Compare simulation against the analytic estimate; flag disagreement instead of hiding it — it usually means a wiring or unit mistake in the netlist.
