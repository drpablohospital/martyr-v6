#!/usr/bin/env python3
"""
forest_plot.py — Forest plot profesional con matplotlib.

Dibuja un forest plot estándar para meta-análisis:
• Cuadrado por estudio, tamaño proporcional al peso (ponderación inversa de varianza).
• Línea de efecto agrupado como diamante.
• Eje vertical con identificadores de estudios.
• Línea vertical en valor nulo (1.0 para RR/OR, 0.0 para MD/d/g).
• Incluye estadísticas heterogeneidad (I², τ², p-valor) en leyenda.

Uso:
    from plots.forest_plot import generate_forest_plot, StudyData, MetaAnalysisResult
    studies = [StudyData(...), ...]
    meta = MetaAnalysisResult(...)
    generate_forest_plot(studies, meta, outfile="output/forest.png")
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans", "Liberation Sans"]

# ── Colores profesionales ──────────────────────────────────────
COLOR_PRIMARY = "#1a5276"    # Azul oscuro
COLOR_RISK = "#c03922b"      # Rojo (no usado aquí, pero disponible)
COLOR_SUCCESS = "#27ae60"    # Verde
COLOR_WARNING = "#f39c12"    # Amarillo
COLOR_NEUTRAL = "#5d6d7e"    # Gris azulado
COLOR_DIAMOND = "#154360"    # Azul muy oscuro para diamante
COLOR_NULLLINE = "#bdc3c7"   # Gris claro
COLOR_STUDY_BOX = "#2e86c1"  # Azul medio para cajas


@dataclass
class StudyData:
    """Datos de un estudio individual para el forest plot."""
    id: str
    label: str
    effect: float
    lower_ci: float
    upper_ci: float
    weight_pct: float  # Peso en porcentaje (0-100)
    n_total: int


@dataclass
class MetaAnalysisResult:
    """Resultado del meta-análisis (efecto agrupado)."""
    pooled_effect: float
    pooled_lower: float
    pooled_upper: float
    i2: float          # I-squared (%)
    tau2: float        # Tau-squared
    p_value: float     # Test de heterogeneidad
    model: str = "RE"  # RE=random-effects, FE=fixed-effects


# ── helpers ────────────────────────────────────────────────────
def _null_value(effect_type: str) -> float:
    """Devuelve el valor nulo según el tipo de efecto."""
    return 1.0 if effect_type.lower() in ("rr", "or", "hr") else 0.0


def _fmt(x: float, decimals: int = 2) -> str:
    return f"{x:.{decimals}f}"


# ── generador principal ────────────────────────────────────────
def generate_forest_plot(
    studies: List[StudyData],
    meta: MetaAnalysisResult,
    *,
    effect_type: str = "OR",
    outfile: Optional[str] = None,
    outdir: str = "../output",
    figsize: Tuple[float, float] = (10, 6),
    dpi: int = 300,
    fmt: str = "png",
    title: str = "Forest Plot",
    show_weights: bool = True,
    color_box: str = COLOR_STUDY_BOX,
    color_diamond: str = COLOR_DIAMOND,
    fontsize: int = 9,
) -> str:
    """
    Genera un forest plot profesional.

    Parámetros
    ----------
    studies : list[StudyData]
        Estudios individuales (debe haber al menos 1).
    meta : MetaAnalysisResult
        Resultado del meta-análisis agrupado.
    effect_type : str
        Tipo de medida de efecto: "OR", "RR", "HR", "MD", "SMD", "g".
    outfile : str | None
        Nombre de archivo de salida (sin extensión). Si es None se autogenera.
    outdir : str
        Directorio de salida relativo a plots/.
    figsize : tuple
        Tamaño de la figura en pulgadas.
    dpi : int
        Resolución para raster (PNG).
    fmt : str
        Formato de salida: "png" | "svg" | "pdf".
    title : str
        Título del gráfico.
    show_weights : bool
        Mostrar columna de pesos en la tabla.
    color_box : str
        Color de las cajas de estudios.
    color_diamond : str
        Color del diamante del efecto agrupado.
    fontsize : int
        Tamaño de fuente base.

    Returns
    -------
    str
        Ruta absoluta del archivo generado.
    """
    if not studies:
        raise ValueError("Se requiere al menos un estudio para generar el forest plot.")

    null_val = _null_value(effect_type)
    n_studies = len(studies)

    # Altura dinámica basada en número de estudios
    fig_h = max(4.5, n_studies * 0.55 + 2.5)
    figsize = (figsize[0], fig_h)

    fig, ax = plt.subplots(figsize=figsize)

    # ── rangos ──────────────────────────────────────────────────
    all_effects = [s.effect for s in studies] + [meta.pooled_effect]
    all_cis = [s.lower_ci for s in studies] + [s.upper_ci for s in studies] + [meta.pooled_lower, meta.pooled_upper]
    lo, hi = min(all_cis), max(all_cis)
    margin = (hi - lo) * 0.15
    x_min, x_max = lo - margin, hi + margin

    # Asegurar que la línea nula esté visible
    x_min = min(x_min, null_val - (hi - lo) * 0.05)
    x_max = max(x_max, null_val + (hi - lo) * 0.05)

    y_positions = list(range(n_studies - 1, -1, -1))
    y_positions_meta = -1  # Debajo del último estudio

    # ── dibujar estudios ───────────────────────────────────────
    for idx, study in enumerate(studies):
        y = y_positions[idx]

        # IC horizontal
        ax.plot(
            [study.lower_ci, study.upper_ci],
            [y, y],
            color=COLOR_NEUTRAL,
            linewidth=1.2,
            solid_capstyle="round",
            zorder=2,
        )

        # Punto central (cuadrado, área ∝ peso)
        area = max(20, study.weight_pct * 8)  # puntos²
        side = math.sqrt(area)
        ax.scatter(
            study.effect,
            y,
            s=area,
            marker="s",
            color=color_box,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )

    # ── diamante meta-análisis ─────────────────────────────────
    diamond_y = y_positions_meta
    diamond_x = [meta.pooled_lower, meta.pooled_effect, meta.pooled_upper, meta.pooled_effect]
    diamond_y_pts = [diamond_y, diamond_y + 0.35, diamond_y, diamond_y - 0.35]
    ax.fill(diamond_x, diamond_y_pts, color=color_diamond, edgecolor="white", linewidth=1.2, zorder=4)

    # ── línea vertical nula ────────────────────────────────────
    ax.axvline(x=null_val, color=COLOR_NULLLINE, linestyle="--", linewidth=1.0, zorder=1)

    # ── ejes ────────────────────────────────────────────────────
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(diamond_y - 1.2, n_studies + 0.8)
    ax.set_yticks(list(range(n_studies)) + [diamond_y])
    ax.set_yticklabels([s.label for s in studies] + ["Pooled"], fontsize=fontsize)

    # Formato eje X
    effect_label = effect_type.upper()
    ax.set_xlabel(f"Effect ({effect_label})", fontsize=fontsize + 1)
    ax.tick_params(axis="x", labelsize=fontsize)

    # ── tabla de datos a la derecha (texto) ────────────────────
    # Añadimos tabla con efecto [IC] y peso
    table_lines = []
    for s in studies:
        weight_str = f"{_fmt(s.weight_pct)}%" if show_weights else ""
        line = f"{_fmt(s.effect)} [{_fmt(s.lower_ci)}–{_fmt(s.upper_ci)}]"
        table_lines.append((line, weight_str))
    pooled_line = f"{_fmt(meta.pooled_effect)} [{_fmt(meta.pooled_lower)}–{_fmt(meta.pooled_upper)}]"
    table_lines.append((pooled_line, f"{_fmt(meta.i2)}%" if show_weights else ""))

    # Segunda columna de anotaciones
    for i, (txt, wtxt) in enumerate(table_lines):
        y = list(range(n_studies - 1, -1, -1)) + [diamond_y]
        # Texto del efecto
        ax.text(
            x_max + (x_max - x_min) * 0.02,
            y[i],
            txt,
            va="center",
            ha="left",
            fontsize=fontsize - 0.5,
            color=COLOR_NEUTRAL,
            transform=ax.transData,
        )

    # ── título y leyenda de heterogeneidad ─────────────────────
    model_name = "Random-Effects" if meta.model == "RE" else "Fixed-Effect"
    het_text = (
        f"Model: {model_name} | "
        f"I² = {_fmt(meta.i2)}% | "
        f"τ² = {_fmt(meta.tau2, 3)} | "
        f"p = {_fmt(meta.p_value, 3)}"
    )
    ax.set_title(title, fontsize=fontsize + 3, fontweight="bold", color=COLOR_PRIMARY, pad=10)
    ax.text(
        0.5, 1.02, het_text,
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=fontsize - 0.5,
        color=COLOR_NEUTRAL,
        style="italic",
    )

    # ── grid ligero ────────────────────────────────────────────
    ax.xaxis.grid(True, linestyle=":", alpha=0.4, color=COLOR_NULLLINE)
    ax.set_axisbelow(True)

    # ── eliminar spines superior y derecho ─────────────────────
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.5)
    ax.spines["bottom"].set_linewidth(0.5)

    plt.tight_layout()

    # ── guardar ────────────────────────────────────────────────
    # Si outdir es relativo, resolver desde directorio de trabajo actual
    output_dir = os.path.abspath(outdir)
    os.makedirs(output_dir, exist_ok=True)

    if outfile is None:
        slug = title.lower().replace(" ", "_").replace("-", "_")
        outfile = f"forest_{slug}"

    path = os.path.join(output_dir, f"{outfile}.{fmt}")
    if fmt.lower() == "png":
        fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    else:
        fig.savefig(path, bbox_inches="tight", facecolor="white")

    plt.close(fig)
    return os.path.abspath(path)


# ── demo / test ────────────────────────────────────────────────
if __name__ == "__main__":
    demo_studies = [
        StudyData("s1", "Goyal et al. 2015", 0.73, 0.55, 0.97, 18.5, 358),
        StudyData("s2", "Berkhemer et al. 2015", 0.49, 0.28, 0.84, 14.2, 500),
        StudyData("s3", "Saver et al. 2016", 0.65, 0.39, 1.08, 11.3, 196),
        StudyData("s4", "Campbell et al. 2015", 0.54, 0.32, 0.93, 12.8, 70),
        StudyData("s5", "Jovin et al. 2015", 0.81, 0.47, 1.41, 9.4, 112),
    ]
    demo_meta = MetaAnalysisResult(
        pooled_effect=0.64,
        pooled_lower=0.49,
        pooled_upper=0.83,
        i2=42.3,
        tau2=0.028,
        p_value=0.12,
        model="RE",
    )
    out = generate_forest_plot(demo_studies, demo_meta, effect_type="OR", title="Endovascular Therapy vs Medical Therapy")
    print(f"Forest plot generado: {out}")
