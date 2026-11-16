# Relatório final, slides e roteiro do vídeo

Entrega oficial: **02/12/2026 até 06:00**, por e-mail aos dois docentes — PDF < 20 MB,
vídeo de 8–10 min < 50 MB com todos os integrantes, anexo com os códigos.

| Arquivo | Conteúdo |
|---|---|
| `relatorio.tex` | Memorial de cálculo: introdução, revisão bibliográfica, itens 1–35, resumo, limitações, referências e anexo de códigos |
| `slides.tex` | Seminário de 8 min (12 slides, Beamer/metropolis) |
| `roteiro_video.md` | Roteiro do vídeo: 7 blocos de ~75 s, um por integrante, com os slides de apoio |
| `gerar_figuras.py` | Gera `figuras/` a partir de `entregas/` e `equipe/` (nenhum número é digitado à mão) |
| `valores_i19.tex`, `valores_i29.tex` | Macros escritas por `scripts/calcular_gci_aero.py` e `scripts/fechar_i29_velocidade.py --figura` |
| `compilar.sh` | Figuras + PDFs |

## Compilar

```bash
relatorio/compilar.sh        # na raiz do repositório
```

Requer TeX Live com `texlive-lang-portuguese`, `texlive-science` (siunitx v3) e
`texlive-latex-extra` (metropolis). Nesta máquina (mhc-lenovo) faltam babel-portuguese e
siunitx; os PDFs foram compilados na torre (`hipolito-Precision-5860-Tower`) com a mesma
árvore de arquivos.

## Antes de enviar

- Preencher os nomes dos integrantes na capa (`relatorio.tex`, tabela P1–P7).
- Conferir se o repositório GitHub citado no anexo está público para os docentes.
- Os resultados não têm aprovação humana registrada (A01–A16 em
  `docs/APROVACOES_FINAIS_PENDENTES.md`); cada integrante deve revisar a sua seção.
