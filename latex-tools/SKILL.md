---
name: latex-tools
description: Compile, scaffold, and debug LaTeX documents - build PDFs with latexmk/tectonic, diagnose log errors, start from ready-made templates (IEEE paper, technical report, letter, TikZ gallery), manage BibTeX citations, and write math/units with siunitx. Use when the user says "compile this LaTeX", "fix this LaTeX error", "start an IEEE paper", "convert to LaTeX", "manage my .bib/citations", or "make a TikZ diagram".
argument-hint: "[compile|new|fix|bib] [file.tex] [options]"
---

# LaTeX Tools

Templates location:

```bash
TEMPLATES="$HOME/.claude/skills/latex-tools/templates"
```

## Installation

This machine has a full TeX Live (MacTeX) install at `/Library/TeX/texbin`: `latexmk`, `pdflatex`, `xelatex`, `bibtex`, `biber` are all available. Nothing to install.

If working on a machine without LaTeX:

- **Minimal (recommended):** `brew install tectonic` — single binary, downloads packages on demand, no TeX Live needed. Compile with `tectonic file.tex`.
- **Full:** `brew install --cask mactex` (several GB) — gives `latexmk` and every package offline.

Detect what exists before compiling:

```bash
which latexmk tectonic pdflatex
```

## 1. Compile

Preferred loop (latexmk reruns passes and bibtex/biber automatically):

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error file.tex
```

With tectonic instead: `tectonic file.tex`.

Clean auxiliary files: `latexmk -c` (keep PDF) or `latexmk -C` (remove PDF too).

Verify success — never trust the wall of output:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error file.tex; echo "exit=$?"
ls -la file.pdf
```

### Reading the log

Fix the FIRST error only, then recompile — later errors are usually cascades:

```bash
grep -n "^!" file.log | head -5
```

Then read ~10 lines around the first match for the line number (`l.<n>`) and context.

### Common errors → fixes

| Log message | Cause | Fix |
|---|---|---|
| `! Undefined control sequence` | Typo in a command, or missing package | Fix spelling, or `\usepackage{...}` that provides it |
| `! Missing $ inserted` | Math symbol (`_`, `^`, `\alpha`) in text mode | Wrap in `$...$`, or escape (`\_`, `\%`) |
| `! LaTeX Error: File 'x.sty' not found` | Package not installed | TeX Live: `sudo tlmgr install <pkg>`; tectonic fetches automatically |
| `! LaTeX Error: Environment x undefined` | Missing package for that environment | Add the `\usepackage` (e.g. `align` needs `amsmath`) |
| `Overfull \hbox (Npt too wide)` | Line/box wider than margin | **Warning, not error** — PDF still builds; fix only if visually bad |
| `Citation 'x' undefined` / `?? ` in PDF | bib pass not run, or key missing from .bib | latexmk handles reruns; otherwise run `bibtex file` (or `biber file` for biblatex) then compile twice; check the key exists |
| `! LaTeX Error: \begin{x} ended by \end{y}` | Mismatched environments | Match the `\begin`/`\end` pair |
| `Runaway argument?` | Unclosed brace `{` | Find the missing `}` near the reported line |

## 2. New document

Copy a template, then adapt:

```bash
cp "$TEMPLATES/ieee-paper.tex" "$TEMPLATES/refs.bib" .   # IEEE conference paper
cp "$TEMPLATES/report.tex" .                              # technical report
cp "$TEMPLATES/letter.tex" .                              # formal letter
cp "$TEMPLATES/tikz-examples.tex" .                       # TikZ/pgfplots/circuitikz gallery
```

All templates are self-contained, compile with both pdflatex and tectonic, and use only packages that ship with TeX Live:

| Template | What it gives you |
|---|---|
| `ieee-paper.tex` | IEEEtran conference paper: abstract, keywords, figure/table/equation examples, bibliography wired to `refs.bib` |
| `refs.bib` | 3 example entries: `@article`, `@inproceedings`, `@misc` (arXiv) |
| `report.tex` | Title page, TOC, chapters, siunitx units, booktabs tables, appendices |
| `letter.tex` | Plain formal letter (letter class) |
| `tikz-examples.tex` | Block diagram (nodes+arrows), pgfplots plot, circuitikz RC circuit |

## 3. Bibliography

**natbib/BibTeX (classic, what IEEEtran uses):** `\bibliographystyle{IEEEtran}` + `\bibliography{refs}`; cite with `\cite{key}`. latexmk runs bibtex automatically.

**biblatex/biber (modern):** `\usepackage[backend=biber,style=ieee]{biblatex}` + `\addbibresource{refs.bib}` + `\printbibliography`; latexmk runs biber automatically.

### Getting BibTeX entries

From a DOI:

```bash
curl -s "https://api.crossref.org/works/10.1109/CVPR.2016.90/transform/application/x-bibtex"
```

From arXiv: use the "Export BibTeX citation" link on the abstract page, or:

```bash
curl -s "https://arxiv.org/bibtex/1706.03762"
```

### Hygiene rules

- Consistent keys: `author2024short` (first author surname + year + first title word), e.g. `he2016resnet`.
- Escape `%` in URLs/abstracts as `\%` — an unescaped `%` silently comments out the rest of the line.
- Protect casing in titles with braces: `title = {Deep Learning on {FPGA}s with {TensorFlow}}` — otherwise most styles lowercase it.
- Prefer DOI over URL when both exist; delete fields you don't want rendered rather than leaving junk.
- One .bib per project; remove duplicate keys (bibtex takes the first silently).

## 4. Math & units

**Units — always siunitx, never hand-rolled:**

```latex
\usepackage{siunitx}
\SI{3.3}{\volt}   \SI{125}{\mega\hertz}   \SI{10}{\giga\bit\per\second}
\SI{-3}{\decibel} \SI{50}{\ohm}           \num{1.5e-9}
\si{\micro\ampere}          % unit alone
\SIrange{2.4}{2.5}{\giga\hertz}
```

**Multi-line math — `align` from amsmath (never `eqnarray`):**

```latex
\begin{align}
  P_\mathrm{dBm} &= 10\log_{10}\!\left(\frac{P}{\SI{1}{\milli\watt}}\right) \\
  V_\mathrm{out} &= V_\mathrm{in}\frac{R_2}{R_1+R_2}
\end{align}
```

Use `\begin{equation}` for single numbered equations, `\[ ... \]` for unnumbered; `\eqref{eq:x}` for references.

**Common EE/RF notation:**

```latex
$Z_0 = \SI{50}{\ohm}$                        % characteristic impedance
$Z = R + jX$                                  % complex impedance (j, not i)
$S_{11}$, $S_{21}$                            % S-parameters
$\Gamma = \frac{Z_L - Z_0}{Z_L + Z_0}$        % reflection coefficient
$\mathrm{NF} = \SI{2.1}{\decibel}$            % noise figure
$f_c = \frac{1}{2\pi RC}$                     % cutoff frequency
\SI{-90}{dBc\per\hertz}                       % phase noise (declare: \DeclareSIUnit\dBc{dBc})
```

Subscripts that are words are upright: `P_\mathrm{out}`, not `P_{out}`.

## Rules

- **Always compile after every edit** and report errors honestly — quote the first `!` line from the log, don't paraphrase it away.
- **Never claim a PDF built** without checking both the exit code (`echo $?` = 0) and that the `.pdf` file exists (`ls -la file.pdf`).
- **When editing a user's existing document, keep their preamble style** — their class, packages, macros, and formatting conventions. Do not "modernize" a working preamble uninvited.
- Fix the first error in the log, recompile, repeat. Do not attempt to fix multiple log errors blind in one pass.
- Overfull hbox is a warning: mention it, but do not block on it.
