"""Generate research paper figures from real experiment data."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.patches import Patch

out_dir = os.path.join(os.path.dirname(__file__), 'figures')
os.makedirs(out_dir, exist_ok=True)

# Real experiment data (verified against JSON results)
methods = {
    'Single-pass':          {'ras': 0.881, 'apr': 71.2, 'ttc': 9210},
    'Rubric-then-Score':    {'ras': 0.863, 'apr': 72.5, 'ttc': 9469},
    'All-Criteria':         {'ras': 0.925, 'apr': 90.0, 'ttc': 13408},
    'Uniform Reattn.':      {'ras': 0.935, 'apr': 90.0, 'ttc': 17814},
    'Best-of-5':            {'ras': 0.957, 'apr': 91.2, 'ttc': 21999},
    'Self-Refine':          {'ras': 0.953, 'apr': 92.5, 'ttc': 13652},
    'FusioN':               {'ras': 0.956, 'apr': 92.5, 'ttc': 15449},
    'EFA -Iteration':       {'ras': 0.943, 'apr': 83.8, 'ttc': 15652},
    'EFA -DynCriteria':     {'ras': 0.943, 'apr': 88.8, 'ttc': 18378},
    'EFA -CMPG':            {'ras': 0.950, 'apr': 92.5, 'ttc': 14579},
    'EFA -FWRL':            {'ras': 0.967, 'apr': 96.2, 'ttc': 17524},
    'EFA (Full)':           {'ras': 0.962, 'apr': 96.2, 'ttc': 16449},
}

baseline_color = '#6baed6'
ablation_color = '#fdae6b'
efa_color = '#2ca02c'

legend_elements = [
    Patch(facecolor=baseline_color, label='Baselines'),
    Patch(facecolor=ablation_color, label='Ablations'),
    Patch(facecolor=efa_color, label='EFA (Full)'),
]


# ============================================================
# FIGURE 2: APR Bar Chart
# ============================================================
def make_apr_chart():
    fig, ax = plt.subplots(figsize=(10, 5))

    names = list(methods.keys())
    aprs = [methods[n]['apr'] for n in names]

    colors = []
    for n in names:
        if n == 'EFA (Full)':
            colors.append(efa_color)
        elif n.startswith('EFA -'):
            colors.append(ablation_color)
        else:
            colors.append(baseline_color)

    bars = ax.barh(range(len(names)), aprs, color=colors,
                   edgecolor='white', linewidth=0.5, height=0.7)

    for bar, apr in zip(bars, aprs):
        weight = 'bold' if apr >= 96.0 else 'normal'
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f'{apr:.1f}%', va='center', ha='left', fontsize=9, fontweight=weight)

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel('All-Pass Rate (APR, %)', fontsize=11)
    ax.set_title('APR Comparison: EFA vs. Baselines and Ablations\n(80 MT-Bench Prompts, MiniMax-M2.5 gen + Qwen-3.5-9B eval)',
                 fontsize=11, fontweight='bold')
    ax.set_xlim(60, 105)
    ax.axvline(x=96.2, color='red', linestyle='--', alpha=0.4, linewidth=1)
    ax.invert_yaxis()
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(f'{out_dir}/apr_comparison.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(f'{out_dir}/apr_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Figure 2: APR bar chart saved")


# ============================================================
# FIGURE 3: Ablation Waterfall
# ============================================================
def make_ablation_chart():
    fig, ax = plt.subplots(figsize=(8, 4.5))

    components = ['Full EFA', '-FWRL\n(0.0pp)', '-CMPG\n(-3.7pp)',
                  '-DynCriteria\n(-7.4pp)', '-Iteration\n(-12.4pp)']
    values = [96.2, 96.2, 92.5, 88.8, 83.8]
    drops = [0, 0.0, -3.7, -7.4, -12.4]
    bar_colors = [efa_color, '#a1d99b', '#fdae6b', '#fd8d3c', '#e6550d']

    bars = ax.bar(range(len(components)), values, color=bar_colors,
                  edgecolor='white', linewidth=1, width=0.6)

    for bar, val, drop in zip(bars, values, drops):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
        if drop < 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                    f'{drop:+.1f}pp', ha='center', va='center',
                    fontsize=9, color='white', fontweight='bold')

    ax.set_xticks(range(len(components)))
    ax.set_xticklabels(components, fontsize=9)
    ax.set_ylabel('All-Pass Rate (APR, %)', fontsize=11)
    ax.set_title('Ablation Study: Component Contribution to APR', fontsize=12, fontweight='bold')
    ax.set_ylim(75, 102)
    ax.axhline(y=96.2, color='red', linestyle='--', alpha=0.3, linewidth=1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(f'{out_dir}/ablation_waterfall.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(f'{out_dir}/ablation_waterfall.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Figure 3: Ablation waterfall saved")


# ============================================================
# FIGURE 4: Cost-Quality Scatter (APR vs TTC)
# ============================================================
def make_cost_quality_chart():
    fig, ax = plt.subplots(figsize=(8, 5.5))

    for name, data in methods.items():
        if name == 'EFA (Full)':
            color, marker, size, zorder = efa_color, '*', 250, 10
        elif name.startswith('EFA -'):
            color, marker, size, zorder = ablation_color, 's', 80, 5
        else:
            color, marker, size, zorder = baseline_color, 'o', 80, 5

        ax.scatter(data['ttc'], data['apr'], c=color, marker=marker, s=size,
                   edgecolors='black', linewidth=0.5, zorder=zorder)

        # Smart label offsets
        ox, oy = 500, -1.5
        ha = 'left'
        if name == 'EFA (Full)':
            ox, oy, ha = -500, -2.8, 'right'
        elif name == 'EFA -FWRL':
            ox, oy = 500, 0.5
        elif name == 'Best-of-5':
            ox, oy = 500, -1.8
        elif name == 'FusioN':
            ox, oy, ha = -500, 0.5, 'right'
        elif name == 'Self-Refine':
            ox, oy = 500, 0.5
        elif name == 'All-Criteria':
            ox, oy, ha = -500, 0.5, 'right'
        elif name == 'Uniform Reattn.':
            ox, oy = 500, 0.5
        elif name == 'Single-pass':
            ox, oy = 500, 0.5
        elif name == 'Rubric-then-Score':
            ox, oy = 500, -1.5

        ax.annotate(name, (data['ttc'] + ox, data['apr'] + oy),
                    fontsize=7.5, alpha=0.85, ha=ha)

    ax.set_xlabel('Total Token Cost (TTC, mean per prompt)', fontsize=11)
    ax.set_ylabel('All-Pass Rate (APR, %)', fontsize=11)
    ax.set_title('Cost-Quality Tradeoff: APR vs. Token Cost', fontsize=12, fontweight='bold')
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(f'{out_dir}/cost_quality_scatter.pdf', dpi=300, bbox_inches='tight')
    plt.savefig(f'{out_dir}/cost_quality_scatter.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Figure 4: Cost-quality scatter saved")


if __name__ == '__main__':
    make_apr_chart()
    make_ablation_chart()
    make_cost_quality_chart()
    print(f"\nAll figures saved to {out_dir}/")
