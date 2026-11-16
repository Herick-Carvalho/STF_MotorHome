# Handoff — STF MotorHome (16/11/2026)

## Estado
- Pedido do usuário em 16/11: terminar os 35 itens e o trabalho todo (relatório, slides, vídeo). A regra antiga de não preparar relatório/slides está revogada.
- Os 35 itens têm resposta numérica no memorial `relatorio/relatorio.tex` (PDF ~43 p., ~2 MB); slides em `relatorio/slides.tex`; roteiro do vídeo em `relatorio/roteiro_video.md`.
- Lacunas fechadas em 16/11 (I19, I24, I29, I30) e o que mudou: `docs/FECHAMENTO_35_ITENS.md`.
- Cenário canônico continua `maxeon1540_independente`; DEC-001–061 preservadas; YAML global não alterado (novo `config/custos_brl_i24.yaml` é só do I24).

## Pendências
1. I19 concluído: Cd = 0,622 ± 0,006 (família de 3 malhas, convergência oscilatória); ver docs/FECHAMENTO_35_ITENS.md.
2. Preencher nomes dos integrantes na capa do relatório; conferir se o GitHub está público.
3. Revisão por integrante (A01–A16 continuam sem aprovação registrada).
4. Gravar o vídeo (roteiro pronto; ffmpeg 720p ~600 kbit/s para ficar < 50 MB).
5. M5 27/11 revisão cruzada; M6 30/11 PDF+slides+vídeo; entrega 02/12 06:00.

## Compilação
`relatorio/compilar.sh`. O mhc-lenovo não tem babel-portuguese/siunitx; compilar na torre (`hipolito-Precision-5860-Tower`), que tem TeX Live completo.

## Verificações
```sh
PYTHONPATH=src .venv/bin/python -m pytest -q
ruff check src scripts tests
MOTORHOME_SCENARIO=maxeon1540_independente PYTHONPATH=src .venv/bin/python scripts/verificar_cenario_integrado.py
PYTHONPATH=src .venv/bin/python scripts/verificar_desenvolvimento.py
```

## Cuidados de máquina
- mhc-lenovo tem 15 GB e costuma estar com swap cheio (navegadores); reiniciou de forma não limpa em 16/11 12:31 durante as malhas. Rodar trabalhos pesados com `systemd-run --user -p MemoryMax=6G -p MemorySwapMax=0`.
- A torre roda o stack do robô FR3 ao vivo; não usar para CFD.
