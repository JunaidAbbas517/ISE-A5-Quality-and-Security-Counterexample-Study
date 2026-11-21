"""Report figures. Run from the repository root:  python report/make_figures.py
Flow figures are drawn from fixed text; the results chart is read from results/raw/ (no typed numbers).
Palette: validated categorical slots 1-2 (#2a78d6 blue, #eb6834 orange) on surface #fcfcfb.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'report' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)

SURFACE, INK, INK2, MUTED, GRID, AXIS = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
BLUE, ORANGE = '#2a78d6', '#eb6834'
BLUE_T, ORANGE_T, GREY_T = '#e3eefb', '#fde7dd', '#f1f0ec'
plt.rcParams.update({'font.family': 'Arial', 'font.size': 10, 'text.color': INK, 'axes.edgecolor': AXIS,
                     'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': INK2,
                     'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE})


def box(ax, x, y, w, h, title, body='', fill=GREY_T, edge=AXIS, title_color=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.06',
                                fc=fill, ec=edge, lw=1.2))
    ax.text(x + w / 2, y + h - 0.16, title, ha='center', va='top', fontsize=10, weight='bold', color=title_color)
    if body:
        ax.text(x + w / 2, y + h - 0.46, body, ha='center', va='top', fontsize=8.4, color=INK2, linespacing=1.35)


def arrow(ax, x1, y1, x2, y2, color=MUTED, text='', style='-|>', ls='-'):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13, color=color, lw=1.4,
                                 linestyle=ls, shrinkA=2, shrinkB=2))
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, text, ha='center', va='bottom', fontsize=8, color=INK2)


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis('off')
    return fig, ax


def fig_study_flow():
    fig, ax = canvas(10, 2.7)
    steps = [
        ('1  Freeze', 'claim, threat model,\n67 cases, 10 mutants,\nthresholds, stop rule\nhashed before run', GREY_T, AXIS),
        ('2  Baseline', 'frozen app\n3 runs, identical\n3 counterexamples\nall controls pass', ORANGE_T, ORANGE),
        ('3  Oracle check', '10 guard mutants\n8 killed = 0.80\n(threshold 0.80)\nM08, M09 survive', GREY_T, AXIS),
        ('4  One fix', 'migration 001\n2 policies changed\ncases & oracle\nunchanged', BLUE_T, BLUE),
        ('5  Rerun', 'same procedure\n3 runs, identical\n0 counterexamples\nall controls pass', BLUE_T, BLUE),
        ('6  Report', 'comparison,\nresidual risk,\nrecovery plan\n(then STOP)', GREY_T, AXIS),
    ]
    w, gap, y, h = 1.45, 0.17, 0.6, 1.75
    for i, (t, b, f, e) in enumerate(steps):
        x = 0.12 + i * (w + gap)
        box(ax, x, y, w, h, t, b, f, e)
        if i:
            arrow(ax, x - gap, y + h / 2, x, y + h / 2)
    ax.text(0.12, 0.25, 'Harness defects only may be fixed after the freeze (logged in protocol/DEVIATIONS.md). '
            'Post-hoc cases are reported separately and not counted.', fontsize=8, color=MUTED)
    fig.savefig(OUT / 'fig1-study-flow.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def fig_threat_model():
    fig, ax = canvas(10, 4.2)
    box(ax, 0.15, 2.5, 2.2, 1.4, 'Attacker client', 'curl / script / devtools\npublic anon key\n+ own JWT (any role)', ORANGE_T, ORANGE)
    box(ax, 0.15, 0.6, 2.2, 1.4, 'Browser app (UI)', 'hides buttons\n(non-active instructor\nsees "waiting" page)', GREY_T, AXIS)
    box(ax, 3.3, 1.35, 2.0, 1.6, 'PostgREST / RPC', 'SET LOCAL ROLE\nanon | authenticated\nrequest.jwt sub = uid\n(no rules of its own)', GREY_T, AXIS)
    box(ax, 6.2, 0.6, 3.6, 3.3, 'PostgreSQL = the only enforcement',
        'column privileges (grant / revoke)\n\nrow-level security policies\n(using / with check)\n\n'
        'security definer RPC checks\nchange_deadline, grade_submission,\nsubmit_assignment, set_instructor_status\n\n'
        'tested here: 67 cases as 8 actors', BLUE_T, BLUE)
    arrow(ax, 2.35, 3.05, 3.3, 2.4, ORANGE, '')
    arrow(ax, 2.35, 1.3, 3.3, 1.8, MUTED, '')
    arrow(ax, 5.3, 2.1, 6.2, 2.1, MUTED, 'SQL as role')
    ax.text(2.45, 3.25, 'bypasses UI', fontsize=8, color=INK2)
    ax.text(0.15, 4.05, 'Actors: anon, student S1/S2, instructor T1/T2, pending P, revoked R, admin A, Auth sign-up',
            fontsize=8.5, color=INK2)
    fig.savefig(OUT / 'fig2-threat-model.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def fig_counterexample():
    fig, ax = canvas(10, 3.9)
    box(ax, 0.1, 2.55, 1.95, 1.15, 'Admin revokes R', "set_instructor_status\n(R, 'rejected')", GREY_T, AXIS)
    box(ax, 2.45, 2.55, 2.1, 1.15, 'R calls REST API', 'DELETE /rest/v1/courses\n?id=eq.CR  (IN-05)', ORANGE_T, ORANGE)
    box(ax, 4.95, 2.55, 2.25, 1.15, 'Before: courses_delete', 'using (instructor_id\n = auth.uid())  only', ORANGE_T, ORANGE)
    box(ax, 7.6, 2.55, 2.3, 1.15, '1 row deleted + cascade', 'enrolments, assignments,\nsubmissions, grades gone', ORANGE_T, ORANGE,
        title_color=INK)
    arrow(ax, 2.05, 3.12, 2.45, 3.12)
    arrow(ax, 4.55, 3.12, 4.95, 3.12, ORANGE)
    arrow(ax, 7.2, 3.12, 7.6, 3.12, ORANGE)
    box(ax, 4.95, 0.55, 2.25, 1.35, 'After: migration 001', 'using (instructor_id = auth.uid()\n and is_instructor_of(id))\n'
        '-> requires status active', BLUE_T, BLUE)
    box(ax, 7.6, 0.55, 2.3, 1.35, '0 rows, no change', 'IN-04 rename, IN-05 delete,\nIN-10 archive all PASS;\n'
        'IN-15 re-approval still works', BLUE_T, BLUE)
    arrow(ax, 3.5, 2.55, 4.95, 1.25, BLUE)
    arrow(ax, 7.2, 1.25, 7.6, 1.25, BLUE)
    ax.text(0.1, 1.0, 'Same request,\nsame actor,\nsame fixture', fontsize=9, color=INK2, linespacing=1.4)
    ax.text(0.1, 0.15, 'The UI never shows these actions to a non-active instructor, so only a direct API call reaches the hole.',
            fontsize=8, color=MUTED)
    fig.savefig(OUT / 'fig3-counterexample-flow.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


def latest(config):
    files = sorted((ROOT / 'results' / 'raw').glob(f'*-{config}-run1.json'))
    return json.loads(files[-1].read_text(encoding='utf-8'))


def fig_results():
    claims = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7']
    names = {'C1': 'C1 role/email', 'C2': 'C2 deadline path', 'C3': 'C3 isolation', 'C4': 'C4 pending/revoked',
             'C5': 'C5 sign-up role', 'C6': 'C6 anonymous', 'C7': 'C7 grades/submit'}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    for ax, cfg, title in zip(axes, ['before', 'after'], ['Before (frozen app)', 'After (+ migration 001)']):
        res = latest(cfg)['results']
        held = [sum(1 for r in res if r['claim'] == c and r['kind'] != 'control' and r['verdict'] == 'PASS') for c in claims]
        broke = [sum(1 for r in res if r['claim'] == c and r['kind'] != 'control' and r['verdict'] == 'FAIL') for c in claims]
        y = list(range(len(claims)))[::-1]
        ax.barh(y, held, color=BLUE, height=0.55, label='attack blocked')
        ax.barh(y, broke, left=[h + 0.15 if b else h for h, b in zip(held, broke)], color=ORANGE, height=0.55,
                label='counterexample')
        for yi, h, b in zip(y, held, broke):
            ax.text(h + b + (0.45 if b else 0.3), yi, f'{h}' + (f' + {b}' if b else ''), va='center', fontsize=8.5, color=INK2)
        ax.set_yticks(y, [names[c] for c in claims])
        ax.set_title(f"{title}: {sum(broke)} counterexample{'s' if sum(broke) != 1 else ''}", fontsize=10.5,
                     loc='left', color=INK)
        ax.set_xlim(0, 19)
        ax.set_xticks(range(0, 19, 3))
        ax.xaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for s in ('top', 'right', 'left'):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis='y', length=0)
        ax.set_xlabel('attack cases')
    axes[1].legend(loc='lower right', frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(OUT / 'fig4-results.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    fig_study_flow()
    fig_threat_model()
    fig_counterexample()
    fig_results()
    print('wrote', sorted(p.name for p in OUT.glob('*.png')))
