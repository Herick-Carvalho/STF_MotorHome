#!/bin/bash
# Gera figuras e compila relatório e slides.
# Requer TeX Live com texlive-lang-portuguese, texlive-science e beamertheme-metropolis.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python relatorio/gerar_figuras.py > /dev/null
cd relatorio
latexmk -pdf -interaction=nonstopmode -halt-on-error relatorio.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error slides.tex
ls -la relatorio.pdf slides.pdf
