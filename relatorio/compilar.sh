#!/bin/bash
# Gera figuras e compila relatório e slides.
# Requer TeX Live com texlive-lang-portuguese, texlive-science e beamertheme-metropolis.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python relatorio/gerar_figuras.py > /dev/null
# Renderizações de CAD/CFD: geometria do cache externo; os campos do CFD só se o VTK existir.
CACHE=${CACHE:-/home/mhc/motorhome_referencias_tarefas}
VTK="$CACHE/cfd-familia-gci-20261116/bg_55x20x10/case/VTK/case_344"
if [ -d "$CACHE" ]; then
  .venv/bin/python relatorio/renderizar_cad.py --cache "$CACHE" $( [ -d "$VTK" ] && echo --cfd-vtk "$VTK" ) > /dev/null
fi
cd relatorio
latexmk -pdf -interaction=nonstopmode -halt-on-error relatorio.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error slides.tex
ls -la relatorio.pdf slides.pdf
