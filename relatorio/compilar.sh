#!/bin/bash
# Gera figuras e compila relatório e slides.
# Requer TeX Live com texlive-lang-portuguese, texlive-science e beamertheme-metropolis.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python relatorio/gerar_figuras.py > /dev/null
# Renderizações de CAD (geometria em entregas/) e de CFD (só se o VTK do cache existir).
CACHE=${CACHE:-/home/mhc/motorhome_referencias_tarefas}
VTK="$CACHE/cfd-familia-gci-20261116/bg_55x20x10/case/VTK/case_344"
.venv/bin/python relatorio/renderizar_cad.py $( [ -d "$VTK" ] && echo --cfd-vtk "$VTK" ) > /dev/null
cd relatorio
latexmk -pdf -interaction=nonstopmode -halt-on-error relatorio.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error slides.tex
ls -la relatorio.pdf slides.pdf
