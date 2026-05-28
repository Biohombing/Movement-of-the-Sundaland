"""
services/pdf_exporter.py
Export calculation results to a formatted PDF report using matplotlib.
No external PDF library required — uses only matplotlib (already a dependency).

Output includes:
  - Title page with app info, Euler Pole params, and timestamp
  - Results table (Name, Lat, Lon, vN, vE, vT, Azimuth, Direction)
  - Velocity magnitude bar chart
  - Footer with scientific references
"""

import io
import os
from datetime import datetime
from typing import List

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyArrowPatch

from models.data_models import PlateVelocity


# ── Colours ──────────────────────────────────────────────────────────────────
C_BLUE    = '#2979C7'
C_DARK    = '#1a1a2e'
C_LIGHT   = '#f5f5f5'
C_ACCENT  = '#5599dd'
C_TEXT    = '#222222'
C_SUBTEXT = '#555555'
C_GRID    = '#dddddd'


def _wrap(text: str, width: int = 90) -> str:
    """Simple word-wrap for long strings."""
    words = text.split()
    lines, line = [], []
    for w in words:
        if sum(len(x)+1 for x in line) + len(w) > width:
            lines.append(' '.join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(' '.join(line))
    return '\n'.join(lines)


def export_pdf(
    results: List[PlateVelocity],
    filepath: str,
    euler_info: dict = None,
    app_version: str = '2.1.0',
) -> None:
    """
    Generate a multi-page PDF report from plate velocity results.

    Parameters
    ----------
    results     : list of PlateVelocity dataclass instances
    filepath    : output .pdf path
    euler_info  : dict with Euler Pole metadata (name, lat, lon, omega, etc.)
    app_version : app version string for footer
    """
    if not results:
        raise ValueError("No results to export.")

    euler_info = euler_info or {}
    now        = datetime.now().strftime('%d %B %Y  %H:%M')

    with PdfPages(filepath) as pdf:

        # ══════════════════════════════════════════════════════════════════════
        # PAGE 1 — Cover + Summary Table
        # ══════════════════════════════════════════════════════════════════════
        fig = plt.figure(figsize=(11.69, 8.27))   # A4 landscape
        fig.patch.set_facecolor('white')

        gs = gridspec.GridSpec(
            3, 1, figure=fig,
            height_ratios=[0.18, 0.72, 0.10],
            hspace=0.04,
            left=0.04, right=0.96, top=0.97, bottom=0.03,
        )

        # ── Header bar ───────────────────────────────────────────────────────
        ax_hdr = fig.add_subplot(gs[0])
        ax_hdr.set_facecolor(C_BLUE)
        ax_hdr.set_xlim(0, 1); ax_hdr.set_ylim(0, 1)
        ax_hdr.axis('off')
        ax_hdr.text(0.015, 0.72, 'GeoPlate Analyst — Sundaland',
                    color='white', fontsize=16, fontweight='bold',
                    va='center', transform=ax_hdr.transAxes)
        ax_hdr.text(0.015, 0.28,
                    f'Tectonic Plate Velocity Report  |  '
                    f'ITRF2020 Euler Pole Method  |  Generated: {now}',
                    color='#c8dcf8', fontsize=9,
                    va='center', transform=ax_hdr.transAxes)
        # Euler pole info on right
        ep_name  = euler_info.get('name', 'N/A')
        ep_omega = euler_info.get('omega', 0.0)
        ep_lat   = euler_info.get('lat', 0.0)
        ep_lon   = euler_info.get('lon_180', euler_info.get('lon', 0.0))
        ep_src   = euler_info.get('source', 'ITRF2020-PMM')
        ew = 'E' if ep_lon >= 0 else 'W'
        ns = 'N' if ep_lat >= 0 else 'S'
        ep_str = (f'Plate: {ep_name}  |  '
                  f'φ={abs(ep_lat):.2f}°{ns}  λ={abs(ep_lon):.2f}°{ew}  '
                  f'ω={ep_omega:.4f}°/Ma')
        ax_hdr.text(0.985, 0.5, ep_str,
                    color='#e0ecff', fontsize=8.5, va='center', ha='right',
                    transform=ax_hdr.transAxes)

        # ── Table ─────────────────────────────────────────────────────────────
        ax_tbl = fig.add_subplot(gs[1])
        ax_tbl.axis('off')

        col_labels = ['No.', 'Location', 'Lat (°)', 'Lon (°)',
                      'vN (mm/yr)', 'vE (mm/yr)', 'vT (mm/yr)',
                      'Azimuth (°)', 'Direction']
        col_widths = [0.04, 0.17, 0.08, 0.08, 0.10, 0.10, 0.10, 0.10, 0.13]

        rows = []
        for i, r in enumerate(results, 1):
            rows.append([
                str(i),
                r.name,
                f'{r.lat:+.4f}',
                f'{r.lon:+.4f}',
                f'{r.vN:+.3f}',
                f'{r.vE:+.3f}',
                f'{r.vT:.3f}',
                f'{r.azimuth:.1f}',
                r.compass,
            ])

        # Draw header row
        x = 0.01
        y_hdr = 0.97
        row_h = 0.038
        for j, (lbl, w) in enumerate(zip(col_labels, col_widths)):
            ax_tbl.add_patch(plt.Rectangle(
                (x, y_hdr - row_h), w - 0.005, row_h,
                transform=ax_tbl.transAxes,
                facecolor=C_DARK, edgecolor='white', linewidth=0.5,
            ))
            ax_tbl.text(x + w/2 - 0.0025, y_hdr - row_h/2, lbl,
                        ha='center', va='center', fontsize=7.5,
                        color='white', fontweight='bold',
                        transform=ax_tbl.transAxes)
            x += w

        # Draw data rows
        for i, row in enumerate(rows):
            y_row = y_hdr - row_h * (i + 2)
            if y_row < 0.02:
                ax_tbl.text(0.5, 0.01,
                            f'… {len(rows)-i} more rows — see page 2',
                            ha='center', va='bottom', fontsize=8,
                            color=C_SUBTEXT, transform=ax_tbl.transAxes)
                break
            bg = '#f0f4fa' if i % 2 == 0 else 'white'
            x = 0.01
            for j, (val, w) in enumerate(zip(row, col_widths)):
                ax_tbl.add_patch(plt.Rectangle(
                    (x, y_row), w - 0.005, row_h,
                    transform=ax_tbl.transAxes,
                    facecolor=bg, edgecolor=C_GRID, linewidth=0.3,
                ))
                ha = 'left' if j == 1 else 'center'
                xv = x + 0.005 if j == 1 else x + w/2 - 0.0025
                # Colour vT by magnitude
                color = C_TEXT
                if j == 6:
                    vt = float(val)
                    vmax = max(r.vT for r in results)
                    ratio = vt / vmax if vmax > 0 else 0
                    color = plt.cm.RdYlGn(0.2 + 0.6 * ratio)
                ax_tbl.text(xv, y_row + row_h/2, val,
                            ha=ha, va='center', fontsize=7.5,
                            color=color, transform=ax_tbl.transAxes)
                x += w

        # ── Footer ───────────────────────────────────────────────────────────
        ax_ftr = fig.add_subplot(gs[2])
        ax_ftr.axis('off')
        ax_ftr.set_facecolor(C_LIGHT)
        ref_txt = (
            'References:  '
            '① Altamimi et al. (2023) ITRF2020-PMM. J.Geodesy 97(5),48. '
            'doi:10.1007/s00190-023-01737-x  |  '
            '② Simons et al. (2007) J.Geophys.Res. 112,B12402  |  '
            '③ Bird (2003) Geochem.Geophys.Geosyst. 4(3),1027'
        )
        ax_ftr.text(0.01, 0.6, ref_txt, fontsize=6.5, color=C_SUBTEXT,
                    transform=ax_ftr.transAxes)
        ax_ftr.text(0.99, 0.6, f'GeoPlate Analyst v{app_version}  |  Page 1',
                    fontsize=6.5, color=C_SUBTEXT, ha='right',
                    transform=ax_ftr.transAxes)

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

        # ══════════════════════════════════════════════════════════════════════
        # PAGE 2 — Charts: Bar + Velocity Rose
        # ══════════════════════════════════════════════════════════════════════
        fig2 = plt.figure(figsize=(11.69, 8.27))
        fig2.patch.set_facecolor('white')

        gs2 = gridspec.GridSpec(
            2, 2, figure=fig2,
            height_ratios=[0.06, 0.94],
            hspace=0.12, wspace=0.12,
            left=0.06, right=0.97, top=0.96, bottom=0.06,
        )

        # Header strip
        ax_hdr2 = fig2.add_subplot(gs2[0, :])
        ax_hdr2.set_facecolor(C_BLUE)
        ax_hdr2.axis('off')
        ax_hdr2.text(0.01, 0.5,
                     f'GeoPlate Analyst — Velocity Analysis Charts  |  {now}',
                     color='white', fontsize=10, fontweight='bold',
                     va='center', transform=ax_hdr2.transAxes)
        ax_hdr2.text(0.99, 0.5, f'Page 2',
                     color='#c8dcf8', fontsize=9, ha='right', va='center',
                     transform=ax_hdr2.transAxes)

        names  = [r.name for r in results]
        vTs    = [r.vT   for r in results]
        vNs    = [r.vN   for r in results]
        vEs    = [r.vE   for r in results]
        azims  = [r.azimuth for r in results]

        # ── Chart 1: Total Velocity bar chart ────────────────────────────────
        ax_bar = fig2.add_subplot(gs2[1, 0])
        cmap   = plt.cm.RdYlGn
        vmax   = max(vTs) if vTs else 1
        colors = [cmap(0.2 + 0.6 * v / vmax) for v in vTs]
        bars   = ax_bar.barh(names, vTs, color=colors, edgecolor='white',
                              linewidth=0.5, height=0.65)
        for bar, vt in zip(bars, vTs):
            ax_bar.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                        f'{vt:.2f}', va='center', ha='left', fontsize=8,
                        color=C_TEXT, fontweight='bold')
        ax_bar.set_xlabel('Total Velocity (mm/yr)', fontsize=9, color=C_TEXT)
        ax_bar.set_title('Total Plate Velocity per Location', fontsize=10,
                         fontweight='bold', color=C_DARK, pad=8)
        ax_bar.set_xlim(0, max(vTs) * 1.18 if vTs else 10)
        ax_bar.tick_params(labelsize=8)
        ax_bar.spines[['top', 'right']].set_visible(False)
        ax_bar.set_facecolor('#fafafa')
        ax_bar.grid(axis='x', color=C_GRID, linewidth=0.5)
        ax_bar.set_axisbelow(True)

        # ── Chart 2: Velocity Component (vN vs vE) scatter ───────────────────
        ax_sc = fig2.add_subplot(gs2[1, 1])
        sc = ax_sc.scatter(vEs, vNs, c=vTs, cmap='RdYlGn',
                           s=100, zorder=3, edgecolors=C_DARK, linewidths=0.5,
                           vmin=min(vTs)*0.8, vmax=max(vTs)*1.1)
        for i, name in enumerate(names):
            ax_sc.annotate(name, (vEs[i], vNs[i]),
                           textcoords='offset points', xytext=(5, 4),
                           fontsize=7, color=C_SUBTEXT)
        # Zero crosshair
        ax_sc.axhline(0, color=C_GRID, linewidth=0.8, linestyle='--')
        ax_sc.axvline(0, color=C_GRID, linewidth=0.8, linestyle='--')
        ax_sc.set_xlabel('vE — East component (mm/yr)', fontsize=9, color=C_TEXT)
        ax_sc.set_ylabel('vN — North component (mm/yr)', fontsize=9, color=C_TEXT)
        ax_sc.set_title('Velocity Components (vN vs vE)', fontsize=10,
                        fontweight='bold', color=C_DARK, pad=8)
        ax_sc.spines[['top', 'right']].set_visible(False)
        ax_sc.set_facecolor('#fafafa')
        ax_sc.grid(color=C_GRID, linewidth=0.4)
        ax_sc.set_axisbelow(True)
        cbar = fig2.colorbar(sc, ax=ax_sc, fraction=0.03, pad=0.02)
        cbar.set_label('vT (mm/yr)', fontsize=8)
        cbar.ax.tick_params(labelsize=7)

        # Footer page 2
        fig2.text(0.5, 0.01,
                  'References: Altamimi et al. (2023) · Simons et al. (2007) · Bird (2003)',
                  ha='center', fontsize=6.5, color=C_SUBTEXT)

        pdf.savefig(fig2, bbox_inches='tight')
        plt.close(fig2)

        # ── PDF metadata ─────────────────────────────────────────────────────
        d = pdf.infodict()
        d['Title']   = 'GeoPlate Analyst — Plate Velocity Report'
        d['Author']  = 'GeoPlate Analyst v' + app_version
        d['Subject'] = 'Sundaland Tectonic Plate Velocity (ITRF2020-PMM)'
        d['Keywords']= 'Euler Pole, ITRF2020, Sundaland, plate velocity'
        d['CreationDate'] = datetime.now()
