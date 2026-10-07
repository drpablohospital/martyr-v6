#!/usr/bin/env python3
"""
funnel_plot.py — Funnel plot para detección de sesgo de publicación.

Dibuja un funnel plot estándar con:
• Eje X: medida de efecto (log-OR, MD, etc.).
• Eje Y: precisión = 1 / SE (mayor valor = mayor precisión arriba).
• Líneas de pseudo-intervalos de confianza (±1.96 SE).
• Opción contour-enhanced (colores por significancia estadística).
• Marca del efecto agrupado como línea vertical.

Uso:
    from plots.funnel_plot import generate_funnel_plot, FunnelStudy
    studies = [FunnelStudy(...), ...]
    generate_funnel_plot(studies, pooled_effect=0.5, se_range=1.2, outfile="funnel.png")
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
COLOR_PRIMARY = "#1a5276"
COLOR_RISK = "#c0392b"
COLOR_SUCCESS = "#27ae60"
COLOR_WARNING = "#f39c12"
COLOR_NEUTRAL = "#5d6d7e"
COLOR_NULLLINE = "#bdc3c7"
COLOR_STUDY_DOT = "#2e86c1"


@dataclass
class FunnelStudy:
    """Datos mínimos para un punto en el funnel plot."""
    label: str
    effect: float   # Efecto en escala original (o log si se prefiere)
    se: float       # Error estándar
    n: int


# ── generador principal ──────────────────────────────────────
def generate_funnel_plot(
    studies: List[FunnelStudy],
    *,
    pooled_effect: float,
    se_range: Optional[float] = None,
    effect_type: str = "OR",
    outfile: Optional[str] = None,
    outdir: str = "../output",
    figsize: Tuple[float, float] = (8, 8),
    dpi: int = 300,
    fmt: str = "png",
    title: str = "Funnel Plot",
    contour_enhanced: bool = True,
    show_labels: bool = False,
    alpha: float = 0.75,
    dotsize: float = 60.0,
    color_dot: str = COLOR_STUDY_DOT,
    color_funnel: str = COLOR_PRIMARY,
    fontsize: int = 9,
) -> str:
    """
    Genera un funnel plot profesional.

    Parámetros
    ----------
    studies : list[FunnelStudy]
        Estudios con efecto y SE conocido.
    pooled_effect : float
        Efecto agrupado (línea vertical central).
    se_range : float | None
        Rango máximo de SE para el eje Y. Si None, se calcula automáticamente.
    effect_type : str
        Tipo de medida (OR, RR, MD, SMD, g). Solo informativo.
    outfile : str | None
        Nombre de archivo de salida (sin extensión).
    outdir : str
        Directorio de salida.
    figsize : tuple
        Tamaño figura (por defecto cuadrado para funnel simétrico).
    dpi : int
        Resolución raster.
    fmt : str
        Formato: png | svg | pdf.
    title : str
        Título.
    contour_enhanced : bool
        Activar fondo con contornos de significancia.
    show_labels : bool
        Mostrar etiquetas de texto junto a cada punto.
    alpha : float
        Transparencia de puntos (0–1).
    dotsize : float
        Tamaño base de puntos en scatter.
    color_dot : str
        Color de los puntos.
    color_funnel : str
        Color de las líneas del funnel.
    fontsize : int
        Tamaño base de fuente.

    Returns
    -------
    str
        Ruta absoluta del archivo generado.
    """
    if not studies:
        raise ValueError("Se requiere al menos un estudio.")

    precisions = [1.0 / max(s.se, 1e-12) for s in studies]
    effects = [s.effect for s in studies]
    ses = [s.se for s in studies]

    # Rango de SE para eje Y
    if se_range is None:
        se_range = max(ses) * 1.15
    se_min = 0.0

    fig, ax = plt.subplots(figsize=figsize)

    # ── contornos de pseudo-IC (funnel) ────────────────────────
    se_vals = np.linspace(se_min, se_range, 400)

    if contour_enhanced:
        # Fondo con 3 zonas de significancia para contour-enhanced
        # |effect - pooled| < 1.0 * SE  →  no significativo (p>0.05 a dos lados)
        # |effect - pooled| > 1.0 * SE  →  significativo
        # |effect - pooled| > 1.96 * SE →  muy significativo
        # Pero en funnel plot "contour-enhanced" clásico se usa log-OR con precisión.
        # Lo adaptamos visualmente: 3 bandas de colores diferenciados.
        for z, color, alpha_bg in [(2.576, "#fadbd8", 0.35), (1.96, "#d5f5e3", 0.35), (1.0, "#d6eaf8", 0.35)]:
            upper = pooled_effect + z * se_vals
            lower = pooled_effect - z * se_vals
            ax.fill_betweenx(se_vals, lower, upper, color=color, alpha=alpha_bg, zorder=1)

    # Líneas de funnel
    for z, style, lw in [(1.96, "--", 1.0), (1.0, ":", 0.8)]:
        upper = pooled_effect + z * se_vals
        lower = pooled_effect - z * se_vals
        ax.plot(upper, se_vals, color=color_funnel, linestyle=style, linewidth=lw, zorder=2)
        ax.plot(lower, se_vals, color=color_funnel, linestyle=style, linewidth=lw, zorder=2)

    # Línea central (efecto agrupado)
    ax.axvline(x=pooled_effect, color=COLOR_RISK, linestyle="-", linewidth=1.2, zorder=2)

    # ── puntos de estudios ─────────────────────────────────────
    sizes = [max(20, min(300, s.n / 2)) for s in studies]
    ax.scatter(
        effects,
        ses,
        s=sizes,
        c=color_dot,
        edgecolor="white",
        linewidth=0.8,
        alpha=alpha,
        zorder=4,
    )

    if show_labels:
        for s in studies:
            ax.text(
                s.effect + se_range * 0.015,
                s.se,
                s.label,
                fontsize=fontsize - 1.5,
                color=COLOR_NEUTRAL,
                va="center",
            )

    # ── ejes ────────────────────────────────────────────────────
    ax.set_xlabel(f"Effect ({effect_type.upper()})", fontsize=fontsize + 1)
    ax.set_ylabel("Standard Error (SE)", fontsize=fontsize + 1)
    ax.set_ylim(se_range, se_min)  # Invertir: alta precisión arriba (SE pequeño)
    ax.tick_params(axis="both", labelsize=fontsize)

    # Título
    ax.set_title(title, fontsize=fontsize + 3, fontweight="bold", color=COLOR_PRIMARY, pad=12)

    # ── leyenda inline ─────────────────────────────────────────
    legend_text = (
        f"Pooled effect = {pooled_effect:.2f}\n"
        f"Studies = {len(studies)}"
    )
    ax.text(
        0.02, 0.02, legend_text,
        transform=ax.transAxes,
        fontsize=fontsize - 0.5,
        verticalalignment="bottom",
        horizontalalignment="left",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#f8f9f9", edgecolor=COLOR_NULLLINE, alpha=0.9),
    )

    # ── estética ───────────────────────────────────────────────
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.5)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.xaxis.grid(True, linestyle=":", alpha=0.3, color=COLOR_NULLLINE)
    ax.set_axisbelow(True)

    plt.tight_layout()

    # ── guardar ────────────────────────────────────────────────
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, outdir)
    os.makedirs(output_dir, exist_ok=True)

    if outfile is None:
        slug = title.lower().replace(" ", "_").replace("-", "_")
        outfile = f"funnel_{slug}"

    path = os.path.join(output_dir, f"{outfile}.{fmt}")
    if fmt.lower() == "png":
        fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    else:
        fig.savefig(path, bbox_inches="tight", facecolor="white")

    plt.close(fig)
    return os.path.abspath(path)


# ── demo ───────────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    demo = []
    for i in range(15):
        n = np.random.randint(40, 600)
        se = 2.0 / math.sqrt(n)
        eff = np.random.normal(0.65, se * 0.8)
        demo.append(FunnelStudy(f"Study {i+1}", eff, se, n))

    out = generate_funnel_plot(
        demo,
        pooled_effect=0.64,
        effect_type="OR",
        title="Funnel Plot — Endovascular Therapy",
        contour_enhanced=True,
    )
    print(f"Funnel plot generado: {out}")
