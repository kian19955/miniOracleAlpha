import json

import numpy as np
import matplotlib.pyplot as plt
import mplcursors
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from pandas import read_csv

from constants import ga_his_dir_path


def plot_logbook(filename_id: str):
    def parse_array(s):
        """Convert string representation of arrays into numpy arrays."""
        s = s.strip().lstrip('[').rstrip(']')
        if s == "":
            return np.array([])
        return np.array([float(x) for x in s.split()])

    # Read the CSV file.
    df = read_csv(ga_his_dir_path / (filename_id + "_logbook.csv"), converters={
        'avg': parse_array,
        'std': parse_array,
        'min': parse_array,
        'max': parse_array
    })

    # Identify dataset changes for vertical dashed lines
    df['dataset_change'] = df['dataset_i'] != df['dataset_i'].shift(1)
    change_gens = df.loc[df['dataset_change'] & df.index.notnull(), 'gen']

    metrics = ['avg', 'std', 'min', 'max']
    metric_colors = {
        'avg': 'blue',
        'std': 'orange',
        'min': 'red',
        'max': 'green'
    }

    # Get the number of objectives from the first row of 'avg'
    n_objectives = len(df.iloc[0]['avg'])

    # --- INDIVIDUAL PLOTS FOR EACH METRIC (Red/Green coloring) ---
    for metric in metrics:
        fig, axes = plt.subplots(n_objectives, 1, sharex=True, figsize=(8, 3 * n_objectives))
        if n_objectives == 1:
            axes = [axes]

        for obj in range(n_objectives):
            x_values = df['gen'].values
            y_values = df[metric].apply(lambda arr: arr[obj]).values

            # Plot segment-by-segment to color increases green, decreases red
            for i in range(len(x_values) - 1):
                x_seg = [x_values[i], x_values[i + 1]]
                y_seg = [y_values[i], y_values[i + 1]]

                if y_seg[1] > y_seg[0]:
                    color = 'green'
                elif y_seg[1] < y_seg[0]:
                    color = 'red'
                else:
                    color = 'gray'  # Neutral if values are equal

                axes[obj].plot(x_seg, y_seg, marker='o', color=color)

            axes[obj].set_ylabel(f'{metric} (Objective {obj})')
            axes[obj].grid(True)

            # Vertical lines for dataset changes
            for gen_val in change_gens:
                axes[obj].axvline(x=gen_val, color='gray', linestyle='--', alpha=0.5)

        axes[-1].set_xlabel('Generation')
        fig.suptitle(f'{metric} over Generations', fontsize=14)
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        plt.show()

    # --- COMBINED PLOTS FOR EACH OBJECTIVE (Fixed Colors) ---
    fig, axes = plt.subplots(n_objectives, 1, sharex=True, figsize=(10, 3 * n_objectives))
    if n_objectives == 1:
        axes = [axes]

    for obj in range(n_objectives):
        ax = axes[obj]
        for metric in metrics:
            x_values = df['gen'].values
            y_values = df[metric].apply(lambda arr: arr[obj]).values
            ax.plot(x_values, y_values, marker='o', label=metric, color=metric_colors[metric])

        # Vertical lines for dataset changes
        for gen_val in change_gens:
            ax.axvline(x=gen_val, color='gray', linestyle='--', alpha=0.5)

        ax.set_ylabel(f'Objective {obj}')
        ax.grid(True)
        ax.legend()

    axes[-1].set_xlabel('Generation')
    fig.suptitle('All Metrics per Objective', fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()


def plot_population(filename_id: str, params: list[str] = None):
    """
    Plots multiple figures, each containing:
    1. A scatter plot of population fitness (Objective 0 vs. Objective 1).
    2. A scatter plot of a single parameter's distribution by rank.
    - Color intensity reflects rank (lower rank = darker, higher = lighter).
    - Hovering over points shows individual ID and value.
    """
    file_path = ga_his_dir_path / (filename_id + "_population.json")

    with open(file_path, "r") as f:
        pop_data = json.load(f)

    ids = list(map(str, sorted(map(int, pop_data.keys()))))
    ranks = list(range(1, len(ids) + 1))  # Rank 1 is best

    obj0, obj1 = [], []
    param_values = {p: [] for p in params} if params else {}

    for rank, ind_id in enumerate(ids, start=1):
        ind_info = pop_data[ind_id]
        fitness = ind_info.get("fitness", [])

        if len(fitness) >= 2:
            obj0.append(fitness[0])
            obj1.append(fitness[1])
        else:
            obj0.append(fitness[0])
            obj1.append(fitness[0])

        if params:
            dna = ind_info.get("individual", {}).get("dna", {})
            for p in params:
                param_values[p].append((ind_id, dna.get(p, np.nan), rank))

    cmap = cm.plasma_r  # Reversed for dark-to-light coloring
    norm = mcolors.Normalize(vmin=1, vmax=len(ids))

    for param in (params or [None]):  # Loop through parameters or just fitness plot
        fig, axes = plt.subplots(2, 1, figsize=(8, 8), sharex=False)

        # --- Fitness Scatter Plot ---
        ax_fitness = axes[0]
        scatter = ax_fitness.scatter(obj0, obj1, c=ranks, cmap=cmap, norm=norm, edgecolors='black')
        ax_fitness.set_xlabel("Objective 0")
        ax_fitness.set_ylabel("Objective 1")
        ax_fitness.set_title("Population Fitness (Color = Rank)")
        ax_fitness.grid(True, linestyle="--", alpha=0.5)

        cursor = mplcursors.cursor(scatter, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(f"ID: {ids[sel.index]}"))

        cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax_fitness)
        cbar.set_label("Rank (1 = Best)")

        # --- Parameter Plot ---
        if param:
            ax_param = axes[1]
            values = np.array([val[1] for val in param_values[param]])
            ranks_list = [val[2] for val in param_values[param]]
            ids_list = [val[0] for val in param_values[param]]

            scatter_param = ax_param.scatter(values, ranks_list, c=ranks_list, cmap=cmap, norm=norm, edgecolors='black')
            ax_param.set_xlabel(param)
            ax_param.set_ylabel("Rank (1 = Best)")
            ax_param.invert_yaxis()
            ax_param.set_title(f"{param} Distribution (Color = Rank)")
            ax_param.grid(True, linestyle="--", alpha=0.5)

            cursor_param = mplcursors.cursor(scatter_param, hover=True)
            cursor_param.connect("add", lambda sel, p=param, vals=values, ids=ids_list, ranks=ranks_list:
            sel.annotation.set_text(f"ID: {ids[sel.index]}\n{p}: {vals[sel.index]}\nRank: {ranks[sel.index]}")
                                 )

            cbar_param = plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax_param)
            cbar_param.set_label("Rank (1 = Best)")

        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    evo_id = "G500_PS100_20250213_211636"
    plot_logbook(evo_id)
    plot_population(evo_id, ["weight_impact", "slow_period"])
