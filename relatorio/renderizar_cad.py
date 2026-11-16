"""Renderiza as imagens de CAD e de CFD do relatório a partir da geometria do projeto.

Uso (na raiz do repositório):
    .venv/bin/python relatorio/renderizar_cad.py \
        --cache /home/mhc/motorhome_referencias_tarefas \
        --cfd-vtk /home/mhc/motorhome_referencias_tarefas/cfd-familia-gci-20261116/bg_55x20x10/case/VTK/case_344

Geometrias: exterior L3H2 adaptado (cache aurora-L3H2-01, derivado de razor24/Dogan Ulus,
MPL-2.0 e CC-BY-4.0), layouts A/B, rotas e teto Maxeon (entregas/), painéis portáteis
(cache cad-portatil-01), banco de serviços e chapas de fixação (STEP, malhados com gmsh).
Os layouts e o teto usam um referencial do compartimento de carga; a translação para o
referencial do veículo foi obtida casando o deck solar com a superfície do CFD.
Renderização por sombreamento de Lambert em matplotlib (sem dependência de GPU).
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "entregas"
OUT = ROOT / "relatorio/figuras"
# compartimento de carga -> veículo (casamento do deck solar com o STL do CFD)
CARGA_PARA_VEICULO = np.array([-3.482, 0.0, 0.648])
TETO_Y = -0.91          # teto/rotas usam y a partir da lateral
LUZ = np.array([-0.35, -0.55, 0.76]) / np.linalg.norm([-0.35, -0.55, 0.76])

CORES = {
    "energia": (0.20, 0.42, 0.78), "agua": (0.22, 0.70, 0.82), "eletro": (0.93, 0.55, 0.20),
    "clima": (0.82, 0.25, 0.25), "movel": (0.80, 0.66, 0.47), "banho": (0.92, 0.92, 0.95),
    "solar": (0.10, 0.16, 0.30), "bolsa": (0.35, 0.38, 0.42), "cama": (0.62, 0.70, 0.55),
}
ROTULOS = {
    "geladeira_AC": "geladeira", "cassete": "cassete", "boiler": "boiler", "inversor": "inversor",
    "tanque_limpa": "água limpa", "tanque_cinza": "água cinza", "US5000_2": "banco 48 V",
    "lava_seca": "lava e seca", "hvac": "A/C", "cama_colchao": "cama", "cama_conversivel_colchao": "cama conversível",
    "portatil_bolsa_2": "painéis portáteis", "base_banho": "banho", "tampo": "bancada",
}


def categoria(nome: str) -> str:
    for chave, cat in (("US5000", "energia"), ("inversor", "energia"), ("tanque", "agua"), ("boiler", "agua"),
                       ("bomba", "agua"), ("geladeira", "eletro"), ("cooktop", "eletro"), ("lava", "eletro"),
                       ("hvac", "clima"), ("MAXEON", "solar"), ("bolsa", "bolsa"), ("cama", "cama"),
                       ("assento", "cama"), ("cassete", "banho"), ("banho", "banho")):
        if chave in nome:
            return cat
    return "movel"


MATERIAIS = {"Body": (0.94, 0.95, 0.96), "Body_Glass": (0.16, 0.22, 0.30), "Black_Plastic": (0.20, 0.21, 0.23),
             "Tire": (0.09, 0.09, 0.10), "Chrome": (0.78, 0.79, 0.82), "Metal": (0.70, 0.71, 0.74)}


def cor_material(geom) -> tuple[float, float, float]:
    v = geom.visual
    nome = getattr(getattr(v, "material", None), "name", None)
    if nome in MATERIAIS:
        return MATERIAIS[nome]
    try:
        if hasattr(v, "material"):
            m = v.material
            c = getattr(m, "baseColorFactor", None)
            if c is None:
                c = m.main_color
            c = np.asarray(c, dtype=float)[:3]
            if c.max() > 1.0:
                c = c / 255.0
            return tuple(np.clip(c, 0.08, 1.0))
        c = np.asarray(v.main_color, dtype=float)[:3] / 255.0
        return tuple(np.clip(c, 0.08, 1.0))
    except (AttributeError, TypeError, ValueError):
        return (0.80, 0.82, 0.85)


def partes(caminho: Path, deslocamento=(0.0, 0.0, 0.0), cor=None, por_nome=None, filtro=None):
    """Lista de (nome, triângulos n×3×3, rgb) de um GLB/STL/STEP."""
    if caminho.suffix.lower() in (".step", ".stp"):
        caminho = step_para_stl(caminho)
    cena = trimesh.load(caminho)
    saida = []
    if isinstance(cena, trimesh.Trimesh):
        itens = [("malha", cena, np.eye(4))]
    else:
        itens = []
        for no in cena.graph.nodes_geometry:
            matriz, nome_geom = cena.graph[no]
            itens.append((nome_geom, cena.geometry[nome_geom], matriz))
    for nome, geom, matriz in itens:
        base = nome.split("_", 1)[1] if nome[:1].isdigit() and "_" in nome else nome
        if filtro and not filtro(base):
            continue
        tri = trimesh.transform_points(geom.vertices, matriz)[geom.faces] + np.asarray(deslocamento)
        rgb = cor or (por_nome(base) if por_nome else cor_material(geom))
        saida.append((base, tri, rgb))
    return saida


def step_para_stl(caminho: Path) -> Path:
    import gmsh

    destino = Path(tempfile.gettempdir()) / (caminho.stem + "_render.stl")
    if destino.exists():
        return destino
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.03)
    gmsh.open(str(caminho))
    gmsh.model.mesh.generate(2)
    gmsh.write(str(destino))
    gmsh.finalize()
    return destino


def desenhar(ax, lista, alfa=None, aresta=None):
    tris, cores = [], []
    for nome, tri, rgb in lista:
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        luz = 0.42 + 0.58 * np.abs(n @ LUZ)
        c = np.clip(np.asarray(rgb)[None, :] * luz[:, None], 0, 1)
        a = np.full((len(tri), 1), 1.0 if alfa is None else alfa.get(nome, 1.0) if isinstance(alfa, dict) else alfa)
        tris.append(tri)
        cores.append(np.hstack([c, a]))
    tri = np.concatenate(tris)
    pc = Poly3DCollection(tri, facecolors=np.concatenate(cores), edgecolors=aresta or "none",
                          linewidths=0.15 if aresta else 0)
    ax.add_collection3d(pc)
    return tri


def enquadrar(ax, tri, elev, azim, margem=0.05, zoom=1.0):
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    centro, faixa = (lo + hi) / 2, (hi - lo) * (1 + margem)
    for f, c, r in ((ax.set_xlim, centro[0], faixa[0]), (ax.set_ylim, centro[1], faixa[1]), (ax.set_zlim, centro[2], faixa[2])):
        f(c - r / 2, c + r / 2)
    aspecto = faixa.copy()
    if elev >= 89:          # vista superior: a altura não aparece, achatar para não sobrar margem
        aspecto[2] = 0.02 * faixa[:2].max()
    ax.set_box_aspect(aspecto, zoom=zoom)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def figura_3d(n=1, tamanho=(9, 5)):
    fig = plt.figure(figsize=tamanho, facecolor="white")
    axs = [fig.add_subplot(1, n, i + 1, projection="3d", computed_zorder=False) for i in range(n)]
    fig.subplots_adjust(left=0, right=1, bottom=0, top=0.93, wspace=0)
    return fig, axs


def salvar(fig, nome):
    fig.savefig(OUT / nome, dpi=170, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    print("ok", nome)


ROTULOS_INTERIOR = {"lava_seca", "geladeira_AC", "cassete", "tampo", "cama_colchao", "cama_conversivel_colchao",
                    "US5000_2", "tanque_limpa"}
NOMES_CATEGORIA = {"energia": "energia 48 V", "agua": "água", "eletro": "eletrodomésticos", "clima": "A/C",
                   "movel": "mobiliário", "banho": "banheiro", "bolsa": "portáteis guardados", "cama": "cama/assentos"}


def legenda(ax):
    from matplotlib.patches import Patch

    ax.legend(handles=[Patch(color=CORES[k], label=v) for k, v in NOMES_CATEGORIA.items()], loc="lower left",
              fontsize=7, frameon=False, ncol=2)


def rotular(ax, lista, deslocamento_z=0.12, so=None):
    vistos = set()
    for nome, tri, _ in lista:
        if nome in ROTULOS and nome not in vistos and (so is None or nome in so):
            vistos.add(nome)
            p = tri.reshape(-1, 3)
            c = p.mean(0)
            ax.text(c[0], c[1], p[:, 2].max() + deslocamento_z, ROTULOS[nome], fontsize=7, ha="center",
                    zorder=10, bbox={"fc": "white", "ec": "0.6", "lw": 0.4, "pad": 1.2, "alpha": 0.85})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=Path("/home/mhc/motorhome_referencias_tarefas"))
    ap.add_argument("--cfd-vtk", type=Path)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ext_glb = args.cache / "aurora-L3H2-01/aurora_L3H2_proposta_m.glb"
    carga = CARGA_PARA_VEICULO
    teto = carga + np.array([0.0, TETO_Y, 0.0])
    exterior = partes(ext_glb)
    modulos = partes(E / "desenvolvimento_2026-11-09/teto_maxeon/alternativa1540_plana.glb", teto, cor=CORES["solar"])
    corte_teto = lambda n: "MAXEON" not in n
    lay_a = partes(E / "integrado_maxeon1540/integracao/A_fixa.glb", carga, por_nome=lambda n: CORES[categoria(n)], filtro=corte_teto)
    lay_b = partes(E / "integrado_maxeon1540/integracao/B_conversivel_noite.glb", carga,
                   por_nome=lambda n: CORES[categoria(n)], filtro=corte_teto)

    # 1. exterior com teto solar, duas vistas
    fig, axs = figura_3d(2, (12, 4.6))
    for ax, azim, tit in ((axs[0], 32, "dianteira"), (axs[1], -140, "traseira")):
        tri = desenhar(ax, exterior)
        desenhar(ax, modulos)
        enquadrar(ax, tri, 16, azim, zoom=1.25)
        ax.set_title(f"Vista {tit}", fontsize=9)
    fig.suptitle("Aurora Solar — exterior com teto de 4 módulos Maxeon (1540 Wp)", fontsize=10)
    salvar(fig, "cad_exterior.png")

    # 2. estacionado, portáteis abertos no solo
    solo = partes(args.cache / "cad-portatil-01/solar_portatil_solo.glb", cor=CORES["solar"])
    fig, axs = figura_3d(1, (9, 5.4))
    tri = desenhar(axs[0], solo + exterior)
    desenhar(axs[0], modulos)
    enquadrar(axs[0], tri, 28, -62, zoom=1.3)
    axs[0].set_title("Estacionado: teto 1540 Wp + 4 painéis portáteis de 400 W abertos (≈ 13,9 kWh/dia em 21/06)", fontsize=9)
    salvar(fig, "cad_estacionado.png")

    # 3. interiores em corte (carroceria fantasma)
    fantasma = [(n, t, (0.55, 0.60, 0.68)) for n, t, _ in exterior]
    for nome_fig, lay, titulo in (("cad_interior_A.png", lay_a, "Layout A (cama fixa) — escolhido"),
                                  ("cad_interior_B.png", lay_b, "Layout B (cama conversível) — comparador")):
        fig, axs = figura_3d(1, (10, 5.4))
        alfa = {n: 0.045 for n, _, _ in fantasma}
        alfa.update({n: 0.35 for n, _, _ in lay if "cama" in n or n in ("estrado", "ponte_cama")})
        tri = desenhar(axs[0], fantasma + lay, alfa=alfa)
        enquadrar(axs[0], tri, 34, -58, zoom=1.35)
        rotular(axs[0], lay, so=ROTULOS_INTERIOR)
        legenda(axs[0])
        axs[0].set_title(f"{titulo}: interior em corte, carroceria transparente", fontsize=9)
        salvar(fig, nome_fig)

    # 4. plantas A e B
    fig = plt.figure(figsize=(10, 6.6), facecolor="white")
    axs = [fig.add_subplot(2, 1, i + 1, projection="3d", computed_zorder=False) for i in range(2)]
    fig.subplots_adjust(left=0, right=1, bottom=0, top=0.95, hspace=0.02)
    for ax, lay, tit in ((axs[0], lay_a, "Layout A"), (axs[1], lay_b, "Layout B")):
        alfa = {n: 0.3 for n, _, _ in lay if "cama" in n or n in ("estrado", "ponte_cama")}
        tri = desenhar(ax, lay, alfa=alfa, aresta=(0.2, 0.2, 0.2, 0.35))
        enquadrar(ax, tri, 90, -90, zoom=1.4)
        ax.set_proj_type("ortho")
        rotular(ax, lay, 0.05, so=ROTULOS_INTERIOR | {"lava_seca", "boiler", "inversor", "hvac", "tanque_cinza"})
        ax.set_title(f"{tit} — planta (frente do veículo à direita, cama transparente)", fontsize=9)
    legenda(axs[1])
    salvar(fig, "cad_plantas.png")

    # 5. rotas de cabos e água
    def cor_rota(n):
        if "cabo_positivo" in n:
            return (0.85, 0.12, 0.12)
        if "cabo_retorno" in n:
            return (0.10, 0.10, 0.10)
        if any(k in n for k in ("tanque_bomba", "bomba_boiler", "principal_pia")):
            return (0.15, 0.55, 0.95)
        return (0.78, 0.80, 0.84)
    rotas = partes(E / "integrado_maxeon1540/rotas_instalacoes/layoutA_rotas_reserva.glb",
                   carga + np.array([0.0, -0.897, 0.0]), por_nome=cor_rota)
    alfa = {n: (1.0 if any(k in n for k in ("cabo", "tanque_bomba", "bomba_boiler", "principal_pia")) else 0.35)
            for n, _, _ in rotas}
    fig, axs = figura_3d(1, (10, 5))
    instal = lambda n: any(k in n for k in ("cabo", "tanque_bomba", "bomba_boiler", "principal_pia"))
    tri = desenhar(axs[0], [x for x in rotas if not instal(x[0])], alfa=alfa)
    desenhar(axs[0], [x for x in rotas if instal(x[0])])
    enquadrar(axs[0], tri, 30, -55, zoom=1.35)
    rotular(axs[0], rotas)
    axs[0].set_title("Rotas reservadas: cabos 48 V (vermelho +, preto −) e água (azul), layout A", fontsize=9)
    salvar(fig, "cad_rotas.png")

    # 6. teto em planta
    fig, axs = figura_3d(1, (10, 3.6))
    tri = desenhar(axs[0], exterior)
    desenhar(axs[0], modulos)
    enquadrar(axs[0], tri, 90, -90, zoom=1.1)
    axs[0].set_proj_type("ortho")
    axs[0].set_title("Teto: 2× SPR-MAX3-380 + 2× SPR-MAX3-390, deck de 4,24 × 1,69 m a 40 mm do teto", fontsize=9)
    salvar(fig, "cad_teto.png")

    # 7. banco de serviços e chapas de fixação (STEP)
    banco = partes(E / "integrado_maxeon1540/bancos_24_48_cad/A_banco_3modulos.step", cor=CORES["energia"])
    chapas = partes(E / "desenvolvimento_2026-11-09/fixacoes_redimensionadas/chapas_locais_condicionais.step",
                    cor=(0.62, 0.64, 0.68))
    fig, axs = figura_3d(2, (12, 4.2))
    tri = desenhar(axs[0], banco, aresta=(0.1, 0.1, 0.15, 0.25))
    enquadrar(axs[0], tri, 25, -60, zoom=1.2)
    axs[0].set_title("Banco de serviços: 3× Pylontech US5000 no suporte (STEP)", fontsize=9)
    tri = desenhar(axs[1], chapas, aresta=(0.1, 0.1, 0.15, 0.25))
    enquadrar(axs[1], tri, 30, -50, zoom=1.2)
    axs[1].set_title("18 chapas de fixação dimensionadas (STEP, 33,1 kg)", fontsize=9)
    salvar(fig, "cad_banco_fixacoes.png")

    if args.cfd_vtk:
        cfd(args.cfd_vtk)


def cfd(pasta: Path) -> None:
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    u_inf = 22.222222

    def ler_vtp(arquivo):
        r = vtk.vtkXMLPolyDataReader()
        r.SetFileName(str(arquivo))
        r.Update()
        tri = vtk.vtkTriangleFilter()
        tri.SetInputData(r.GetOutput())
        tri.Update()
        c2p = vtk.vtkCellDataToPointData()
        c2p.SetInputData(tri.GetOutput())
        c2p.Update()
        pd = tri.GetOutput()
        pts = vtk_to_numpy(pd.GetPoints().GetData())
        cel = vtk_to_numpy(pd.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
        p = vtk_to_numpy(pd.GetCellData().GetArray("p"))
        return pts[cel], p

    tri_c, p_c = ler_vtp(pasta / "boundary/aurora.vtp")
    tri_d, p_d = ler_vtp(pasta / "boundary/pvdeck.vtp")
    tri = np.concatenate([tri_c, tri_d])
    cp = np.concatenate([p_c, p_d]) / (0.5 * u_inf**2)
    norm = matplotlib.colors.Normalize(-1.0, 1.0)
    cmap = plt.get_cmap("turbo")
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    luz = 0.55 + 0.45 * np.abs(n @ LUZ)
    cores = cmap(norm(cp))
    cores[:, :3] *= luz[:, None]
    fig, axs = figura_3d(2, (12, 4.4))
    for ax, azim, tit in ((axs[0], 35, "frente"), (axs[1], -145, "traseira")):
        el, az = np.radians(18), np.radians(azim)
        olho = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        # normais dos patches do OpenFOAM apontam para fora do fluido, isto é, para dentro do veículo
        vis = n @ olho < 0
        ax.add_collection3d(Poly3DCollection(tri[vis], facecolors=cores[vis], edgecolors="none"))
        enquadrar(ax, tri, 18, azim, zoom=1.25)
        ax.set_title(f"$C_p$ na superfície — {tit}", fontsize=9)
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=axs, shrink=0.6, label="$C_p = p/(\\frac{1}{2}U_\\infty^2)$", pad=0.01)
    salvar(fig, "cfd_cp.png")

    r = vtk.vtkXMLUnstructuredGridReader()
    r.SetFileName(str(pasta / "internal.vtu"))
    r.Update()
    plano = vtk.vtkPlane()
    plano.SetOrigin(0, 0.001, 0)
    plano.SetNormal(0, 1, 0)
    corte = vtk.vtkCutter()
    corte.SetCutFunction(plano)
    corte.SetInputConnection(r.GetOutputPort())
    corte.Update()
    tf = vtk.vtkTriangleFilter()
    tf.SetInputData(corte.GetOutput())
    tf.Update()
    pd = tf.GetOutput()
    pts = vtk_to_numpy(pd.GetPoints().GetData())
    cel = vtk_to_numpy(pd.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    u = vtk_to_numpy(pd.GetCellData().GetArray("U"))
    umag = np.linalg.norm(u, axis=1) / u_inf
    fig, ax = plt.subplots(figsize=(11, 3.4))
    tc = ax.tripcolor(pts[:, 0], pts[:, 2], cel, facecolors=umag, cmap="viridis", vmin=0, vmax=1.3, shading="flat")
    ax.set_facecolor("0.78")   # sem células dentro do veículo: o fundo cinza é a silhueta
    ax.set(xlim=(-10, 5), ylim=(0, 4.5), xlabel="x [m] (escoamento da direita para a esquerda)", ylabel="z [m]", aspect="equal")
    ax.set_title("Velocidade no plano de simetria, $|U|/U_\\infty$ (80 km/h, malha fina)", fontsize=9)
    fig.colorbar(tc, ax=ax, label="$|U|/U_\\infty$", pad=0.01)
    fig.tight_layout()
    fig.savefig(OUT / "cfd_plano.png", dpi=170)
    plt.close(fig)
    print("ok cfd_plano.png")


if __name__ == "__main__":
    main()
