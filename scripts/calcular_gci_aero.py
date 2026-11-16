"""I19: discretization uncertainty of the drag coefficient.

Reads the three members of the background-mesh family run by
executar_aero_malha_adicional.py (same snappy levels, no cell cap, only the
background divisions change). Representative size h = (V/N)^(1/3).

Monotone convergence (0 < R < 1, R = e21/e32 with e = f_coarser - f_finer):
Celik et al. (2008) GCI with apparent order p by fixed-point iteration and
Richardson extrapolation. Oscillatory convergence (R < 0): Richardson
extrapolation does not apply, and the uncertainty is bounded by half the
oscillation range, U = (max - min)/2 (Stern et al., 2001). The Celik numbers
are still written to the summary as a diagnostic. Writes the summary, a
figure and the LaTeX macros used by the report.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FAMILIA = ROOT / "entregas/aero_equipado1540/familia_gci"
MEMBROS = ["bg_55x20x10", "bg_44x16x8", "bg_33x12x6"]   # fina, média, grossa
VOLUME_M3 = 55.0 * 20.0 * 10.0
A_REF = 4.827840375264284
CD_ENERGIA_NOMINAL = 0.62487678   # config/parametros_globais.yaml: cd_range[1]


def ordem_aparente(e21: float, e32: float, r21: float, r32: float) -> float:
    s = math.copysign(1.0, e32 / e21)
    p = 1.0
    for _ in range(500):
        q = math.log((r21**p - s) / (r32**p - s))
        novo = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(novo - p) < 1e-12:
            return novo
        p = novo
    raise RuntimeError("apparent order did not converge")


def main() -> None:
    casos = []
    for nome in MEMBROS:
        r = json.loads((FAMILIA / nome / "resumo.json").read_text())
        if not (r.get("mesh_ok") and r.get("solver_exit") == 0 and r.get("last_cd_diagnostic")):
            raise SystemExit(f"{nome}: run incomplete or failed")
        log = (FAMILIA / nome / "case/log.snappyHexMesh").read_text(errors="replace")
        if "reached limit" in log:
            raise SystemExit(f"{nome}: snappy hit the cell cap; not a valid family member")
        n = int(r["cell_count"])
        casos.append({"caso": nome, "celulas": n, "h_m": (VOLUME_M3 / n) ** (1 / 3), "cd": float(r["last_cd_diagnostic"]),
                      "convergiu": bool(r.get("solver_converged")), "cd_span_50it": r.get("last50_cd_relative_span"),
                      "yplus": r.get("yplus_summary")})
    (h1, h2, h3), (f1, f2, f3) = [c["h_m"] for c in casos], [c["cd"] for c in casos]
    r21, r32 = h2 / h1, h3 / h2
    e21, e32 = f2 - f1, f3 - f2
    razao_convergencia = e21 / e32
    oscilatoria = razao_convergencia < 0
    p = ordem_aparente(e21, e32, r21, r32)
    f_ext = (r21**p * f1 - f2) / (r21**p - 1)
    ea21 = abs((f1 - f2) / f1)
    gci21 = 1.25 * ea21 / (r21**p - 1)
    ea32 = abs((f2 - f3) / f2)
    gci32 = 1.25 * ea32 / (r32**p - 1)
    if oscilatoria:
        metodo = "oscilatoria: U = (max - min)/2 (Stern et al., 2001); Richardson não aplicável"
        incerteza = (max(f1, f2, f3) - min(f1, f2, f3)) / 2
    else:
        metodo = "monotônica: GCI de Celik et al. (2008)"
        incerteza = gci21 * f1
    resumo = {
        "script": "scripts/calcular_gci_aero.py", "method": metodo,
        "casos": casos, "r21": r21, "r32": r32, "razao_convergencia_R": razao_convergencia,
        "oscilatoria": oscilatoria, "cd_fina": f1, "incerteza_absoluta_cd": incerteza,
        "incerteza_relativa_cd": incerteza / f1, "cda_m2": f1 * A_REF,
        "cd_modelos_energia": CD_ENERGIA_NOMINAL,
        "diferenca_relativa_modelos_energia": (CD_ENERGIA_NOMINAL - f1) / f1,
        "diagnostico_celik": {"ordem_aparente_p": p, "cd_extrapolado": f_ext, "gci_fina_21": gci21,
                              "gci_media_32": gci32, "valido": not oscilatoria,
                              "nota": "r21 < 1,3 e convergência oscilatória: valores apenas diagnósticos"},
        "physical_validation": False,
    }
    (FAMILIA / "resumo_gci.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    hs = [c["h_m"] for c in casos]
    fs = [c["cd"] for c in casos]
    ax.axhspan(f1 - incerteza, f1 + incerteza, color="#1f5fbf", alpha=0.12, label=f"$C_d$ = {f1:.3f} ± {incerteza:.3f}")
    ax.plot(hs, fs, "o-", color="#1f5fbf", lw=1)
    ax.axhline(CD_ENERGIA_NOMINAL, color="#e8590c", ls="--", lw=1, label=f"$C_d$ dos modelos de energia ({CD_ENERGIA_NOMINAL:.3f})")
    for c in casos:
        ax.annotate(f"{c['celulas'] / 1e3:.0f} mil células", (c["h_m"], c["cd"]), textcoords="offset points",
                    xytext=(-20, 8), fontsize=8)
    ax.set(xlabel="tamanho representativo de célula h = (V/N)$^{1/3}$ [m]", ylabel="$C_d$",
           xlim=(min(hs) * 0.9, max(hs) * 1.08), ylim=(f1 - 4 * incerteza, f1 + 4 * incerteza))
    ax.set_title("convergência " + ("oscilatória" if oscilatoria else "monotônica"), fontsize=9)
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FAMILIA / "gci_cd.png", dpi=180)

    def virg(x: float, n: int = 3) -> str:
        return f"{x:.{n}f}".replace(".", ",")

    vezes = "$\\times$"
    linhas = " \\\\\n".join(
        "{} & \\num{{{}}} & {} & {}".format(c["caso"].replace("bg_", "").replace("x", vezes), c["celulas"],
                                          virg(c["h_m"], 4), virg(c["cd"], 4))
        for c in casos)
    if oscilatoria:
        linhas_metodo = (
            f"\\multicolumn{{3}}{{l}}{{Razão de convergência $R = \\varepsilon_{{21}}/\\varepsilon_{{32}}$}} & {virg(razao_convergencia, 2)} \\\\\n"
            f"\\multicolumn{{3}}{{l}}{{Incerteza $U = (C_{{d,max}} - C_{{d,min}})/2$}} & {virg(incerteza, 4)} ({virg(100 * incerteza / f1, 1)}\\,\\%) \\\\\n")
        legenda = "convergência oscilatória; incerteza pela amplitude de oscilação (Stern et al., 2001)"
    else:
        linhas_metodo = (
            f"\\multicolumn{{3}}{{l}}{{Ordem aparente $p$}} & {virg(p, 2)} \\\\\n"
            f"\\multicolumn{{3}}{{l}}{{$C_d$ extrapolado (Richardson)}} & {virg(f_ext, 4)} \\\\\n"
            f"\\multicolumn{{3}}{{l}}{{GCI malha fina}} & {virg(100 * gci21, 2)}\\,\\% \\\\\n")
        legenda = "convergência monotônica; GCI de Celik et al. (2008)"
    tex = (
        f"\\newcommand{{\\CdValor}}{{{virg(f1, 3).replace(',', '{,}')} \\pm {virg(incerteza, 3).replace(',', '{,}')}}}\n"
        f"\\newcommand{{\\CdGCI}}{{{virg(100 * incerteza / f1, 1)}\\,\\%}}\n"
        f"\\newcommand{{\\CdA}}{{\\SI{{{virg(f1 * A_REF, 2)}}}{{m^2}}}}\n"
        f"\\newcommand{{\\CdOscilatoria}}{{{'1' if oscilatoria else '0'}}}\n"
        "\\newcommand{\\GCItabela}{%\n\\begin{table}[H]\\centering\\small\n"
        f"\\caption{{Item 19 — família de malhas: {legenda}.}}\n"
        "\\begin{tabular}{lrrr}\\toprule Malha de fundo & Células & $h$ [m] & $C_d$ \\\\\\midrule\n"
        f"{linhas} \\\\\\midrule\n"
        f"\\multicolumn{{3}}{{l}}{{Razões de refino $r_{{21}}$, $r_{{32}}$}} & {virg(r21, 3)}, {virg(r32, 3)} \\\\\n"
        f"{linhas_metodo}"
        "\\bottomrule\\end{tabular}\\end{table}}\n"
    )
    (ROOT / "relatorio/valores_i19.tex").write_text(tex, encoding="utf-8")
    print(json.dumps({k: resumo[k] for k in ("method", "r21", "r32", "razao_convergencia_R", "cd_fina",
                                              "incerteza_absoluta_cd", "incerteza_relativa_cd", "cda_m2",
                                              "diferenca_relativa_modelos_energia")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
