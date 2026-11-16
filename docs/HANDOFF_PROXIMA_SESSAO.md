# Handoff — STF MotorHome (16/11/2026, fim da sessão)

## O que é e por quê
Trabalho da disciplina (motorhome elétrico solar "Aurora Solar", Fiat E-Ducato L3H2, 35 itens).
Entrega oficial **02/12/2026 06:00** por e-mail aos dois docentes: PDF < 20 MB, vídeo 8–10 min
< 50 MB com os 7 integrantes, anexo de códigos. Em 16/11 o usuário pediu para terminar tudo
(revogada a regra antiga de "não fazer relatório/slides").

## Estado (commits `22143a6` e `8f4dcd2`, em `main` e `hub/tarefas-motorhome-com-codex`, CI verde)
- `relatorio/relatorio.pdf` (51 p., 5 MB, 29 figuras), `relatorio/slides.pdf` (15 quadros),
  `relatorio/roteiro_video.md` (7 blocos de ~75 s). Fontes `.tex` + `compilar.sh`.
- Lacunas fechadas e números: `docs/FECHAMENTO_35_ITENS.md`. Principais:
  I19 Cd = 0,622 ± 0,006 (malhas 291k/523k/751k: 0,6220/0,6338/0,6215, convergência oscilatória →
  meia amplitude, Stern 2001; GCI/Richardson inválidos); I24 R$ 789 mil (721–882);
  I29 20,7 km/h, partida 17h45, 248,8 d; I30 489 A RMS, 85 °C no 1×120 mm².
- Figuras: `relatorio/gerar_figuras.py` (gráficos) e `relatorio/renderizar_cad.py`
  (10 renderizações CAD/CFD; geometria do cache, Cp/velocidade do VTK da malha fina).

## Aberto (só o grupo/usuário)
1. Nomes dos integrantes na capa (`relatorio.tex`, tabela P1–P7) e recompilar.
2. Conferir se o GitHub `MHC-CodeSmith/STF_MotorHome` está visível aos docentes.
3. Revisão de cada integrante (A01–A16 sem aprovação registrada; B01 interface CC é hipótese).
4. Gravar o vídeo (ffmpeg 720p, ~600 kbit/s → < 50 MB). M6 30/11.

## Onde e como
- Repo no mhc-lenovo: `/home/mhc/motorhome_solar_codex_tarefas` (não mexer em `motorhome_solar_codex`). Commits como `MHC <carvalho.matheush@gmail.com>`, sem trailer.
- Cache externo: `/home/mhc/motorhome_referencias_tarefas/` — exterior `aurora-L3H2-01/`, portáteis `cad-portatil-01/`,
  malhas/campos CFD `cfd-familia-gci-20261116/bg_*/case` (503 MB; VTK em `bg_55x20x10/case/VTK/case_344`).
- PDFs: compilar na torre (TeX Live completo); o lenovo não tem babel-portuguese/siunitx.
- QA (igual ao CI, Python 3.11): `PYTHONPATH=src .venv/bin/python -m pytest -q`; `~/.local/bin/ruff check src scripts tests relatorio`;
  `MOTORHOME_SCENARIO=maxeon1540_independente PYTHONPATH=src .venv/bin/python scripts/verificar_cenario_integrado.py` e
  `scripts/verificar_desenvolvimento.py` (após mudar script/saída rastreados: `--registrar`, depois sem). O verificador
  hasheia tudo em `entregas/aero_equipado1540/`: não deixar arquivos ignorados lá.
- Referencial CAD: `relatorio/montagem_cad.py` monta tudo no referencial do projeto (traseira interna x = −3,35 m, piso z = 0,68 m,
  largura centrada; rotas e teto Maxeon exportados com y a partir da lateral). O deck fica na posição do `pvdeck.stl` do CFD
  (x − 3,482, y − 0,91, z + 0,648 sobre o arquivo do teto). O antigo offset −3,482/0,648 aplicado ao interior o enfiava 13 cm
  nas portas traseiras (corrigido em 16/11). Colisões resolvidas na montagem: banco US5000 sobre a caixa de roda (A) ou
  18,5 cm para o centro (B); cabos 48 V pela frente do inversor; linha da pia sob o piso. Os arquivos de rotas em
  entregas/ não mudaram (rastreados pelo verificador). Figuras: `fatiar()` divide triângulos longos (matplotlib sem z-buffer).

## Cuidados
- mhc-lenovo (15 GB, swap cheio) reiniciou sem shutdown em 16/11 12:31 durante CFD: rodar pesado com
  `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0`.
- Torre roda o FR3 real ao vivo: nada de CFD lá.
- snappyHexMesh: `maxGlobalCells` corta o refinamento em silêncio — procurar "reached limit" no log.

## Em andamento (16/11, fim da tarde) — revisão por integrante
Pedido do usuário: (1) conferir no repositório se está tudo pronto para cada integrante revisar a sua parte;
(2) escrever a mensagem de WhatsApp pedindo a revisão pelo repositório; (3) confirmar se o repositório é público.
Feito até aqui: só leitura. Existem `docs/guia_revisao.md` (checklist de aceitação, 12 linhas),
`docs/APROVACOES_FINAIS_PENDENTES.md` (167 linhas, aprovações A01–A16 sem registro), `docs/marcos_e_revisoes.md`,
`equipe/P1_estrutura_freios` … `equipe/P7_arrefecimento` e `metadata/itens.csv` (dono de cada item).
Próximo passo exato:
1. Ler `metadata/itens.csv`, `docs/APROVACOES_FINAIS_PENDENTES.md` e o conteúdo de `equipe/P*/`; conferir se cada
   item I01–I35 tem dono, seção no relatório (`\itemsec{n}` em relatorio/relatorio.tex), script/saída e um lugar
   para registrar a aprovação (nome, data, commit).
2. Ver visibilidade: `gh repo view MHC-CodeSmith/STF_MotorHome --json visibility` (rodar na torre; o lenovo não tem gh).
3. Corrigir lacunas pequenas (ex.: um arquivo de revisão por integrante com itens, páginas do PDF e checklist),
   commitar como MHC sem trailer, push para main e hub/tarefas-motorhome-com-codex.
4. Entregar ao usuário a mensagem de WhatsApp (pt-BR): link do repo, PDF em relatorio/relatorio.pdf, onde fica a
   parte de cada um (Pn → itens), checklist, como registrar a aprovação, prazo (M6 30/11; entrega 02/12 06:00),
   visualizador 3D https://claude.ai/artifact/SwLMR3bhXRuDWDFQ7g8hCu (privado: só abre se compartilhado).
Estado do CAD: commit f216e92 (colisões resolvidas, figuras corrigidas), CI verde nos dois ramos.
