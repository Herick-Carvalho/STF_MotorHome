"""I30 closure: motor-feed cable temperature at the motor's maximum power.

The earlier study swept phase currents of 300/450/600 A and fixed film
coefficients. Here the RMS phase current at peak power is estimated from the
DC bus voltage with the SVPWM linear-modulation limit, V_LL,rms = V_dc/sqrt(2),
I = P_mech / (eta_motor * sqrt(3) * V_LL * PF), and the outer boundary uses
natural convection on a horizontal cylinder (Churchill-Chu) plus radiation in
still air at 25 C, iterated on the computed surface temperature. The r-theta
field comes from the same solver used before (motorhome.cabos_polares).
Steady state at peak power is conservative: the 205 kW peak is short-duration.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from motorhome.cabos_polares import Cabo, resolver

SIGMA = 5.670374419e-8
G = 9.81
# Dry air at 1 atm (Incropera, Table A.4): T [K], k [W/m K], nu [m2/s], Pr
AIR = np.array([
    [300, 0.0263, 15.89e-6, 0.707], [350, 0.0300, 20.92e-6, 0.700],
    [400, 0.0338, 26.41e-6, 0.690], [450, 0.0373, 32.39e-6, 0.686],
    [500, 0.0407, 38.79e-6, 0.684], [550, 0.0439, 45.57e-6, 0.683],
    [600, 0.0469, 52.69e-6, 0.685],
])


def ar(t_k: float) -> tuple[float, float, float]:
    return tuple(float(np.interp(t_k, AIR[:, 0], AIR[:, i])) for i in (1, 2, 3))


def h_externo(ts_k: float, ta_k: float, d_m: float, emissividade: float) -> tuple[float, float]:
    """Natural convection (Churchill-Chu, horizontal cylinder) and linearised radiation."""
    tf = (ts_k + ta_k) / 2
    k, nu, pr = ar(tf)
    alpha = nu / pr
    ra = G * (1 / tf) * max(ts_k - ta_k, 1e-6) * d_m**3 / (nu * alpha)
    nu_d = (0.60 + 0.387 * ra**(1 / 6) / (1 + (0.559 / pr)**(9 / 16))**(8 / 27))**2
    h_conv = nu_d * k / d_m
    h_rad = emissividade * SIGMA * (ts_k**2 + ta_k**2) * (ts_k + ta_k)
    return h_conv, h_rad


def resolver_acoplado(cabo: Cabo, corrente: float, ta_k: float, emissividade: float,
                      nr: int = 32, nt: int = 128) -> dict:
    ts = ta_k + 30.0
    for _ in range(100):
        h_conv, h_rad = h_externo(ts, ta_k, 2 * cabo.raio_externo_m, emissividade)
        r = resolver(cabo, corrente, nr, nt, h_conv + h_rad, ta_k)
        ts_new = float(np.mean(r["temperatura_superficie_k"]))
        if abs(ts_new - ts) < 1e-6:
            break
        ts = 0.5 * ts + 0.5 * ts_new
    else:
        raise RuntimeError("surface temperature iteration did not converge")
    return {"h_conv_w_m2k": h_conv, "h_rad_w_m2k": h_rad, "temperatura_superficie_c": ts_new - 273.15,
            "temperatura_max_c": r["temperatura_max_k"] - 273.15,
            "temperatura_media_feixe_c": r["temperatura_media_feixe_k"] - 273.15,
            "joule_w_m": r["joule_w_m"], "residuo_w_m": r["residuo_w_m"], "_campo": r}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/cabos_tracao_proposta.yaml")
    parser.add_argument("--destino", type=Path,
                        default=ROOT / "entregas/integrado_maxeon1540/i30_corrente_maxima")
    args = parser.parse_args()
    cfg = yaml.safe_load(args.config.read_text())
    m = cfg["model"]
    globais = yaml.safe_load((ROOT / "config/parametros_globais.yaml").read_text())["parameters"]
    p_mech = globais["motor_peak_kw"]["value"] * 1000
    v_dc_nom = globais["traction_voltage_v"]["value"]
    ta = m["ambient_k"]
    base = Cabo(m["bundle_radius_m"], m["outer_radius_m"], m["bundle_k_assumed_w_mk"],
                m["insulation_k_assumed_w_mk"], m["resistance20_ohm_m"], m["alpha_assumed_per_k"],
                m["reference_k"])
    alt = cfg["alternative_manufacturer_same_table"]
    cabo150 = replace(base, raio_feixe_m=alt["conductor_diameter_max_mm"] / 2000,
                      raio_externo_m=alt["cable_diameter_nominal_mm"] / 2000,
                      resistencia20_ohm_m=alt["resistance20_max_ohm_km"] / 1000)
    opcoes = {"1x120": (base, 1), "1x150": (cabo150, 1), "2x120": (base, 2)}

    rows = []
    for eta, pf, vdc, emis in itertools.product((0.92, 0.95, 0.97), (0.85, 0.90, 0.95),
                                                 (0.875 * v_dc_nom, v_dc_nom), (0.8, 0.9)):
        v_ll = vdc / np.sqrt(2)
        corrente = p_mech / (eta * np.sqrt(3) * v_ll * pf)
        for nome, (cabo, paralelos) in opcoes.items():
            r = resolver_acoplado(cabo, corrente / paralelos, ta, emis)
            r.pop("_campo")
            rows.append({"eta_motor": eta, "fator_potencia": pf, "v_dc_v": vdc, "v_ll_rms_v": v_ll,
                         "emissividade": emis, "corrente_fase_rms_a": corrente, "opcao": nome,
                         "corrente_por_cabo_a": corrente / paralelos, **r,
                         "acima_150c": r["temperatura_max_c"] > 150.0})

    nominal = {"eta": 0.95, "pf": 0.90, "vdc": v_dc_nom, "emis": 0.9}
    nom_i = p_mech / (nominal["eta"] * np.sqrt(3) * nominal["vdc"] / np.sqrt(2) * nominal["pf"])
    campos = {nome: resolver_acoplado(cabo, nom_i / par, ta, nominal["emis"]) for nome, (cabo, par) in opcoes.items()}

    args.destino.mkdir(parents=True, exist_ok=True)
    with (args.destino / "sensibilidade.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for nome, res in campos.items():
        c = res["_campo"]
        nr = len(c["r_m"])
        perfil = c["temperatura_k"].reshape(nr, -1).mean(axis=1) if c["temperatura_k"].ndim == 1 else c["temperatura_k"].mean(axis=1)
        axes[0].plot(np.asarray(c["r_m"]) * 1000, perfil - 273.15, label=f"{nome}: Tmax {res['temperatura_max_c']:.0f} °C")
    axes[0].axhline(150, ls="--", c="k", lw=0.8)
    axes[0].text(0.3, 152, "limite do isolamento RADOX 155 (150 °C)", fontsize=8)
    axes[0].set(xlabel="raio [mm]", ylabel="temperatura [°C]",
                title=f"Perfil radial, I = {nom_i:.0f} A RMS (205 kW)")
    axes[0].legend(fontsize=8)
    c = campos["1x120"]["_campo"]
    th = np.asarray(c["theta_rad"]); rr = np.asarray(c["r_m"])
    tt = np.asarray(c["temperatura_k"]).reshape(len(rr), len(th)) - 273.15
    axes[1].remove()
    ax = fig.add_subplot(1, 2, 2, projection="polar")
    pc = ax.pcolormesh(th, rr * 1000, tt, shading="nearest", cmap="inferno")
    ax.set_title("Campo r–θ [°C], 1×120 mm² por fase (raio em mm)", fontsize=9)
    ax.set_rticks([2, 4, 6, 8]); ax.set_rlabel_position(200); ax.tick_params(labelsize=7)
    fig.colorbar(pc, ax=ax, label="°C")
    fig.tight_layout()
    fig.savefig(args.destino / "campo_corrente_maxima.png", dpi=150)

    resumo = {
        "script": "scripts/fechar_i30_corrente_maxima.py",
        "method": "I_fase = P_mec/(eta_m*sqrt(3)*V_LL*FP), V_LL,rms = V_dc/sqrt(2) (limite SVPWM linear); contorno: convecção natural Churchill–Chu + radiação, ar parado 25 °C; campo r–θ do solver do projeto",
        "motor_peak_mechanical_w": p_mech,
        "nominal": {**nominal, "corrente_fase_rms_a": nom_i,
                    **{f"{n}_temperatura_max_c": campos[n]["temperatura_max_c"] for n in campos},
                    **{f"{n}_h_total_w_m2k": campos[n]["h_conv_w_m2k"] + campos[n]["h_rad_w_m2k"] for n in campos}},
        "faixa_corrente_fase_rms_a": [min(r["corrente_fase_rms_a"] for r in rows), max(r["corrente_fase_rms_a"] for r in rows)],
        "faixa_temperatura_max_c": {n: [min(r["temperatura_max_c"] for r in rows if r["opcao"] == n),
                                        max(r["temperatura_max_c"] for r in rows if r["opcao"] == n)] for n in opcoes},
        "max_abs_residuo_w_m": max(abs(r["residuo_w_m"]) for r in rows),
        "limits": ["Regime permanente na potência de pico é conservador: o pico de 205 kW é de curta duração.",
                   "Sem perdas AC/PWM (efeito pelicular), feixe de cabos, conduíte ou condução axial.",
                   "Fator de potência, eficiência e tensão do barramento são varridos; mapa OEM não publicado."],
    }
    (args.destino / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resumo["nominal"], ensure_ascii=False, indent=1))
    print(json.dumps(resumo["faixa_temperatura_max_c"]))


if __name__ == "__main__":
    main()
