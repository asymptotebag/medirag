import argparse
import numpy as np
import pandas as pd
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
from app.pipeline import create_rag_chain_with_source
from core.federated_retriever import RootRetriever, RouterRetriever, LeafRetriever
from eval.scalability.create_scale_app import create_scale_app

QUESTIONS = [  # all general evaluation questions
    "For patients admitted to this practice who report heavy alcohol consumption, what are some of the most common diagnoses?",
    "For patients receiving general surgery, what are the most common chief complaints?",
    "What are some complications experienced by patients who underwent coronary artery bypass?",
    "What are some common diagnoses for patients reporting abdominal pain?",
    "What are the most significant risk factors for stroke among neurology patients?",
    "Is Medicare or Medicaid more widely used for insurance among patients at Hospital A?",
    "For patients admitted for cardiology or cardiothoracic services, what was the most common surgical procedure performed?",
    "What are the most severe withdrawal symptoms experienced by patients with a history of drug or alcohol use, and how were withdrawal symptoms treated?",
    "Is it more common for patients to present to the emergency department for orthopedic surgery due to a mechanical fall, or due to pain from preexisting health conditions?",
]
DATA_DF = pd.read_csv("data.csv")
USERINFO = {"name": "A.phys", "org": "A", "role": "physician", "dept": "surgery", "sub": "0"}  # attributes don't matter for this test
# N_VALS = [1, 5, 10, 15, 20]
# D_VALS = [0, 1, 2, 3, 4]

def gen_org_subtrees(df, n=1, d=0):
    # return list of len n of each hospital's subtree
    org_subtrees = []
    org_dfs = np.array_split(df, n) # split by width
    if d == 0: # each subtree is a leaf
        print("creating a leaf for each subtree")
        return [LeafRetriever(id=f"{n}{d}{i}", db_path=f"qdrant/{n}/{d}/{i}", df=org_df, text_col="text") for i, org_df in enumerate(org_dfs)]

    for i, org_df in enumerate(org_dfs): # split by depth
        n_leaf = 2**d
        leaf_dfs = np.array_split(org_df, n_leaf)
        leaf_nodes = [LeafRetriever(id=f"{n}{d}{i}{j}", db_path=f"qdrant/{n}/{d}/{i}/{j}", df=leaf_df, text_col="text") for j, leaf_df in enumerate(leaf_dfs)]
        level_nodes = leaf_nodes
        for _ in range(d):
            # pair up level_nodes side by side as children to a new router
            new_level = []
            for left_i in range(0, len(level_nodes), 2):
                left, right = level_nodes[left_i], level_nodes[left_i+1]
                new_level.append(RouterRetriever(id="", children=[left, right]))
            level_nodes = new_level

        assert len(level_nodes) == 1
        org_root = level_nodes[0]

        org_app = create_scale_app(name=f"scale_{i}", uri=f"http://127.0.0.1:{5001+i}/api/retrieve", org_retriever=org_root)
        pid = os.fork()
        if pid == 0:
            org_app.run(port=5001+i)
            print("THIS SHOULD NOT PRINT OUT!")
        org_subtrees.append(org_root)

    return org_subtrees


# measure: qdrant creation time, retrieval time (on same plot, 1 plot for each axis)
def profile(N, D):
    # test width
    gen_org_subtrees(df=DATA_DF, n=N, d=D)
    org_retrieve_uris = {f"http://127.0.0.1:{5001+i}/api/retrieve" for i in range(N)}
    chain = create_rag_chain_with_source(userinfo=USERINFO, hospital_retrieve_uris=org_retrieve_uris)
    for qi, q in enumerate(QUESTIONS):
        with open("retrieval_report.txt", "a") as ret_f:
            with open("qdrant_report.txt", "a") as qdrant_f:
                ret_f.write(f"========================================\nN={N} D={D} Q={qi+1}\n")
                qdrant_f.write(f"========================================\nN={N} D={D}\n")
                response = chain.invoke(q)
                ret_f.write("========================================\n")
                qdrant_f.write("========================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='Scalability Eval',
                    description='Scalability evaluation of retrieval/qdrant creation times on different federation widths/depths')

    parser.add_argument('-n', type=int, help="width of retrieval tree (i.e. number of hospital servers)")
    parser.add_argument('-d', type=int, help="depth of retrieval tree (i.e. number of router retriever levels in a hospital tree)")

    args = parser.parse_args()
    if args.n is not None and args.d is not None:
        profile(N=args.n, D=args.d)   
    else:
        print("Please specify a retrieval tree width (-n) and depth (-d) to profile")
    