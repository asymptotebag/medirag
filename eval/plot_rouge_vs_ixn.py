import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

CLINICAL_TREND_QA_PATH = "eval/clinical_trend_qa.csv"
PLOTS_DIR_PATH = "eval/plots"
SCENARIOS = ["A.phys", "A.nurse", "B.phys", "B.nurse", "C.research"]

def shorten(scenario_name: str): # e.g. federated_secure_A.phys -> fs.A.phys
    splits = scenario_name.split("_")
    return splits[0][0] + splits[1][0] + (f".{splits[2]}" if len(splits) > 2 else "")

def plots(df: pd.DataFrame):
    N_QUERY = len(df.index)
    colors = ["yellowgreen", "teal", "orchid", "red", "orange"]

    ixns = [[df.at[i, f"fi_fs.{scn}_ixn"] for i in range(N_QUERY)] for scn in SCENARIOS]
    rouge1s = [[df.at[i, f"fi_fs.{scn}_rouge1"] for i in range(N_QUERY)] for scn in SCENARIOS]
    print(rouge1s)
    
    fig, ax = plt.subplots()
    for i in range(len(SCENARIOS)):
        ax.scatter(x=ixns[i], y=rouge1s[i], c=colors[i], label=SCENARIOS[i])

    m, b = np.polyfit([ixn for ixn_scn in ixns for ixn in ixn_scn], [rg for rg_scn in rouge1s for rg in rg_scn], deg=1)
    xseq = np.linspace(0, 1, num=100)
    ax.plot(xseq, b + m * xseq, color="gray", lw=2)
    ax.text(0.45, 0.7, f"rouge1 = {round(m,2)}*ixn + {round(b,2)}")

    ax.legend(loc='upper center', bbox_to_anchor=(0.51, 1.15), ncol=3)
    ax.grid(True)
    ax.set_xlabel("ixn")
    ax.set_ylabel("rouge1")
    plt.savefig(f"{PLOTS_DIR_PATH}/select_rouge_vs_ixn.png")

if __name__ == "__main__":
    df = pd.read_csv(CLINICAL_TREND_QA_PATH)
    plots(df)
