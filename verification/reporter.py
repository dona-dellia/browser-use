from os import listdir
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors, ticker, colormaps

import itertools
from tasks import evaluate_task_perfom

ROOT = "../verification/US/"
ENRICHMENT = ["raw", "E1"]

def get_Us_names(path):
    """
    """
    uss = [int(f) for f in listdir(ROOT)]
    uss = sorted(uss)
    uss = ['US/'+str(f) for f in uss]
    return uss

def get_precision_for_all_US():
    """
    """
    pass

def get_precision_by_US(id_us, type):
    """
    """
    precision = evaluate_task_perfom(id_us, type)
    return precision

def execute_all_US():
    """
    """
    uss = get_Us_names(ROOT)
    combinations = list(itertools.product(uss, ENRICHMENT))
    paths = [a+'/'+b+'/' for a,b in combinations]

    for us in paths:
        name = us.split('/')[-2]+".txt"
        with open('../verification/'+us+name, 'r') as file:
            us_task = file.read()
        
        print(us)
        print(us_task)

def execute_US_by_id(us_id):
    """
    """
    pass

def heatmap(data, row_labels, col_labels, ax=None,
            cbar_kw=None, cbarlabel="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (M, N).
    row_labels
        A list or array of length M with the labels for the rows.
    col_labels
        A list or array of length N with the labels for the columns.
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current Axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to `matplotlib.Figure.colorbar`.  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    if ax is None:
        ax = plt.gca()

    if cbar_kw is None:
        cbar_kw = {}

    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    # Create colorbar
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # Show all ticks and label them with the respective list entries.
    ax.set_xticks(range(data.shape[1]), labels=col_labels,
                  rotation=-30, ha="right", rotation_mode="anchor")
    ax.set_yticks(range(data.shape[0]), labels=row_labels)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False)

    # Turn spines off and create white grid.
    ax.spines[:].set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar

def compare_models():
    """
    """
    np.random.seed(19680801)
    
    vegetables = ["US-"+str(i) for i in range(1,8,1)]
    x = [f"V{i}" for i in range(1, 8)]

    fig, ((ax, ax2)) = plt.subplots(1, 2, figsize=(10, 6))

    # Replicate the above example with a different font size and colormap.

    data = np.random.randint(2, 100, size=(7, 7))

    im, _ = heatmap(data, vegetables, x, ax=ax,
                    cmap="YlGn", cbarlabel="Llama 11b")
    
    # Create some new data, give further arguments to imshow (vmin),
    # use an integer format on the annotations and provide some colors.

    data = np.random.randint(2, 100, size=(7, 7))
    y = [f"US-{i}" for i in range(1, 8)]
    im, _ = heatmap(data, y, x, ax=ax2, vmin=0,
                    cmap="YlGn", cbarlabel="Llama 70b")

    # Sometimes even the data itself is categorical. Here we use a
    # `matplotlib.colors.BoundaryNorm` to get the data into classes
    # and use this to colorize the plot, but also to obtain the class
    # labels from an array of classes.

    #data = np.random.randn(6, 6)
    #y = [f"Prod. {i}" for i in range(10, 70, 10)]
    #x = [f"Cycle {i}" for i in range(1, 7)]

    #qrates = list("ABCDEFG")
    #norm = colors.BoundaryNorm(np.linspace(-3.5, 3.5, 8), 7)
    #fmt = ticker.FuncFormatter(lambda x, pos: qrates[::-1][norm(x)])

    #im, _ = heatmap(data, y, x, ax=ax3,
    #                cmap=colormaps["PiYG"].resampled(7), norm=norm,
    #                cbar_kw=dict(ticks=np.arange(-3, 4), format=fmt),
    #                cbarlabel="Quality Rating")

    # We can nicely plot a correlation matrix. Since this is bound by -1 and 1,
    # we use those as vmin and vmax. We may also remove leading zeros and hide
    # the diagonal elements (which are all 1) by using a
    # `matplotlib.ticker.FuncFormatter`.

    #corr_matrix = np.corrcoef(harvest)
    #im, _ = heatmap(corr_matrix, vegetables, vegetables, ax=ax4,
    #                cmap="PuOr", vmin=-1, vmax=1,
    #                cbarlabel="correlation coeff.")

    plt.tight_layout()
    plt.show()

def compare_enrichment():
    """
    """

if __name__ == '__main__':
    compare_models()
    
    results = []
    us_precision = []
    uss = []
    UNTIL_US = 1

    for i in range(1,UNTIL_US+1,1):
        uss.append("US-"+str(i))
        for type in ENRICHMENT:
            #print(i,type)
            result = get_precision_by_US(i, type)
            us_precision.append(round(result["precision"],2))
        results.append(us_precision)
        us_precision = []

    print(results)
    
    harvest = np.array(results)

    fig, ax = plt.subplots()
    enrichment = ENRICHMENT
    
    # Show all ticks and label them with the respective list entries
    ax.set_xticks(range(len(enrichment)), labels=enrichment,
                rotation=45, ha="right", rotation_mode="anchor")
    ax.set_yticks(range(len(uss)), labels=uss)

    # Loop over data dimensions and create text annotations.
    for i in range(len(uss)):
        for j in range(len(enrichment)):
            text = ax.text(j, i, harvest[i, j],
                        ha="center", va="center", color="b")

    im, cbar = heatmap(harvest, uss, enrichment,  ax=ax,
                    cmap="YlGn", cbarlabel="model 11b [us/precision]")
    #texts = annotate_heatmap(im, valfmt="{x:.1f} t")

    fig.tight_layout()
    plt.show()