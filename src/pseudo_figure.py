# import seaborn as sns

# # latency breakdown for CPU-centric, offload-centric, and ultra-low latency
# def latency_breakdown(lat_dict):
#     for name, 

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def plot_clustered_stacked(dfall, labels=None, title="multiple stacked bar plot",  H="/", **kwargs):
    """Given a list of dataframes, with identical columns and index, create a clustered stacked bar plot. 
labels is a list of the names of the dataframe, used for the legend
title is a string for the title of the plot
H is the hatch used for identification of the different dataframe"""

    n_df = len(dfall)
    n_col = len(dfall[0].columns) 
    n_ind = len(dfall[0].index)
    axe = plt.subplot(111)

    for df in dfall : # for each data frame
        axe = df.plot(kind="bar",
                      linewidth=0,
                      stacked=True,
                      ax=axe,
                      legend=False,
                      grid=False,
                      **kwargs)  # make bar plots

    h,l = axe.get_legend_handles_labels() # get the handles we want to modify
    for i in range(0, n_df * n_col, n_col): # len(h) = n_col * n_df
        for j, pa in enumerate(h[i:i+n_col]):
            for rect in pa.patches: # for each index
                rect.set_x(rect.get_x() + 1 / float(n_df + 1) * i / float(n_col))
                rect.set_hatch(H * int(i / n_col)) #edited part     
                rect.set_width(1 / float(n_df + 1))

    axe.set_xticks((np.arange(0, 2 * n_ind, 2) + 1 / float(n_df + 1)) / 2.)
    axe.set_xticklabels(df.index, rotation = 0)
    axe.set_title(title)

    # Add invisible data to add another legend
    n=[]        
    for i in range(n_df):
        n.append(axe.bar(0, 0, color="gray", hatch=H * i))

    l1 = axe.legend(h[:n_col], l[:n_col], loc=[0, 0.5])
    if labels is not None:
        # l2 = plt.legend(n, labels, loc=[1.01, 0.1])
        l2 = plt.legend(n, labels, loc=[0.6, 0.7])
    axe.add_artist(l1)
    return axe

# create fake dataframes
df1 = pd.DataFrame(np.array([[5, 10, 1], [5, 10, 1.5]]),
                   index=["SmartSage", "GList"],
                   columns=["SSD read", "PCIe", "Other(CPU/Accel)"])
df2 = pd.DataFrame(np.array([[5, 1, 1], [5, 0, 1.5]]),
                   index=["SmartSage", "GList"],
                   columns=["SSD read", "PCIe", "Other(CPU/Accel)"])

# Then, just call :
sns.set_theme()
axes = plot_clustered_stacked([df1, df2],["cpu-centric", "offload"], title="Latency Breakdown")

plt.savefig("test.png")
