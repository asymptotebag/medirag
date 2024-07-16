import argparse
import evaluate
import logging
import os
import pandas as pd
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain_community.document_loaders import DataFrameLoader
from operator import itemgetter

from app.pipeline import create_rag_chain_with_source, format_docs, PROMPT, GPT_LLM, SEARCH_KWARGS
from core.util import chunk_df, prefix_metadata
from core.federated_retriever import BaselineRetriever
from core.full_df_loader import AllColumnsDataFrameLoader
from core.llm import Dummy, FlanT5, MEDITRON_LLM
from orgs.hospitalA.hosp_bp import HOSP_DATA_PATH as A_HOSP_DATA_PATH, DEPTS as A_DEPTS
from orgs.hospitalB.hosp_bp import HOSP_DATA_PATH as B_HOSP_DATA_PATH, DEPTS as B_DEPTS
from orgs.hospitalC.hosp_bp import HOSP_DATA_PATH as C_HOSP_DATA_PATH, DEPTS as C_DEPTS

logger = logging.getLogger("log")
logger.propagate = False

fileHandler = logging.FileHandler("logs/log.txt")
logger.addHandler(fileHandler)
logger.setLevel(logging.DEBUG)

CLINICAL_TREND_QA_PATH = "eval/clinical_trend_qa.csv"
LLM_EVAL_PATH = "eval/llm_eval.csv"
QDRANT_PATH = "eval/qdrant_baseline/"

METRICS = {
    "rouge": ["rouge1", "rougeL"],
    "bleu": ["bleu"],
}
USERINFOS = [
    {"name": "A.phys", "org": "A", "role": "physician", "dept": "surgery", "sub": "0"},  # access to all resources in hospitals A and B
    {"name": "A.phys.neur", "org": "A", "role": "physician", "dept": "medicine", "affiliations": ["C_neuro"], "sub": "1"},  # access to all resources in hospitals A, B, C
    {"name": "A.tech.rad", "org": "A", "role": "technician", "dept": "radiology", "sub": "2"},  # only access to A's orthopaedics
    {"name": "A.admin", "org": "A", "role": "admin", "sub": "3"},  # only access to A's admissions
    {"name": "A.nurse", "org": "A", "role": "nurse", "dept": "psychiatry", "sub": "4"},  # access to all of A and B
    {"name": "B.phys", "org": "B", "role": "physician", "dept": "cardiology", "sub": "5"},  # access to all of A and B
    {"name": "B.nurse", "org": "B", "role": "nurse", "dept": "medicine", "sub": "6"},  # access to all of B
    {"name": "C.research", "org": "C", "role": "researcher", "dept": "neurology", "sub": "7"},  # access to all of C
]
EVAL_PAIRS = [("centralized_insecure", "federated_insecure")] + [("federated_insecure", f"federated_secure_{user['name']}") for user in USERINFOS] # (ref, pred)

def hosp_dfs(hosp_data_path, depts):    
    dfs = []
    for dept in depts:
        dept_df = pd.read_csv(os.path.join(hosp_data_path, f"{dept}.csv"))
        dfs.append((dept != "admissions", dept_df))
    return dfs

def create_baseline_rag_chain(dfs: list[tuple[bool, pd.DataFrame]], llm=GPT_LLM):
    docs = []
    for (has_text_col, df) in dfs:
        if has_text_col:  # split into chunks if this leaf contains unstructured data
            df = chunk_df(df=df, chunk_col="text")
            prefix_metadata(df=df, chunk_col="text", metadata_cols=["name"])
            docs.extend(DataFrameLoader(df).load())
        else:  # for structured data, all columns go into document page_content
            docs.extend(AllColumnsDataFrameLoader(df).load())
        # print(f"DataFrameLoader returned {len(docs)} docs, last one is:\n{docs[-1]}")

    baseline_retriever = BaselineRetriever(
        docs=docs,
        db_path=QDRANT_PATH,
        search_kwargs=SEARCH_KWARGS,
    )

    rag_chain_from_docs = (
        {
            "context": lambda input: format_docs(input["documents"]),
            "question": itemgetter("question"),
        }
        | PROMPT
        | llm
        | StrOutputParser()
    )

    rag_chain_with_source = RunnableParallel(
        {"documents": baseline_retriever, "question": RunnablePassthrough()}
    ) | {
        "answer": rag_chain_from_docs,
        "documents": lambda input: [doc for doc in input["documents"]],
        "prompt": lambda input: PROMPT.format(context=format_docs(input["documents"]), question=input["question"]),
    }

    return rag_chain_with_source

def eval_scenario(rag_chain, scenario: str, eval_df: pd.DataFrame, llm_eval_df: pd.DataFrame, llm_name: str, user: str | None = None):
    scenario_name = scenario + '_' + user if user else scenario
    print(f"evaluating {scenario_name} scenario", end="")
    logger.debug(f"\n\n*** EVALUATING SCENARIO: {scenario_name.upper()} ***\n")

    for i, query in enumerate(eval_df["question"]):
        prompt_name = f"{shorten(scenario_name)}_{i}"
        prompt_idx = len(llm_eval_df.index)
        if "scenario" in llm_eval_df.columns:
            idxs = llm_eval_df[llm_eval_df["scenario"] == prompt_name].index  # already exists?
            if len(idxs) > 0:
                prompt_idx = idxs.values[0]
        llm_eval_df.at[prompt_idx, "scenario"] = prompt_name

        print(".", end="")
        sys.stdout.flush()
        logger.debug(f"scenario: {prompt_name} idx: {prompt_idx}\nquery:{query}")
        
        response = rag_chain.invoke(query)
        eval_df.at[i, f"{scenario_name}"] = response["answer"]
        logger.debug(f"answer:{response['answer']}\n")

        llm_eval_df.at[prompt_idx, "prompt"] = response["prompt"]
        llm_eval_df.at[prompt_idx, llm_name] = response["answer"]

        retrieved_docs = set()
        for doc in response["documents"]:
            doc_meta = doc['kwargs']['metadata']
            # if from discharger summary, metadata contains note_id and text_index; else is from admissions
            retrieved_docs.add(f"{doc_meta.get('note_id', doc_meta.get('org', 'x')+'-'+'adm')}:{doc_meta.get('text_index', doc_meta.get('row'))}")
        
        eval_df.at[i, f"{shorten(scenario_name)}_docs"] = "[" + ",".join(retrieved_docs) + "]"

    print()

def shorten(scenario_name: str): # e.g. federated_secure_A.phys -> fs.A.phys
    splits = scenario_name.split("_")
    return splits[0][0] + splits[1][0] + (f".{splits[2]}" if len(splits) > 2 else "")

def compute_metric(metric: str, ref_scenario: str, pred_scenario: str, eval_df: pd.DataFrame):
    eval_metric = evaluate.load(metric)
    try:
        for i, (ref_text, pred_text) in enumerate(zip(eval_df[ref_scenario].tolist(), eval_df[pred_scenario].tolist())):
            score_dict = eval_metric.compute(predictions=[pred_text], references=[ref_text])
            logger.debug(score_dict)
            for subscore in METRICS[metric]: # e.g. for rouge, ["rouge1", "rougeL"]
                col_name = f"{shorten(ref_scenario)}_{shorten(pred_scenario)}_{subscore}"  # e.g. ci_fi_rouge1
                if col_name not in eval_df.columns:
                    eval_df[col_name] = ""
                eval_df.at[i, col_name] = score_dict[subscore]
    except KeyError:
        return

def compute_doc_intersection(ref_scenario: str, pred_scenario: str, eval_df: pd.DataFrame):
    ref_docs_col = f"{shorten(ref_scenario)}_docs"
    pred_docs_col = f"{shorten(pred_scenario)}_docs"
    ixn_col_name = f"{shorten(ref_scenario)}_{shorten(pred_scenario)}_ixn"  # e.g. ci_fi_ixn
    logger.debug(f"IXN: {ref_docs_col} ^ {pred_docs_col} -> {ixn_col_name}")

    try: 
        for i in range(len(eval_df.index)):
            ref_docs = set([doc_id for doc_id in eval_df[ref_docs_col][i][1:-1].split(",")])
            pred_docs = set([doc_id for doc_id in eval_df[pred_docs_col][i][1:-1].split(",")])
            ixn = ref_docs & pred_docs
            eval_df.at[i, ixn_col_name] = len(ixn) / len(ref_docs) if len(ref_docs) > 0 else 1.0
            logger.debug(f"{i}: {eval_df.at[i, ixn_col_name]} ref={ref_docs} pred={pred_docs}")
    except KeyError:
        return

def eval_meditron():
    logger.debug("\n\n *** EVALUATING SCENARIO: baseline CI with MEDITRON LLM ***")
    llm_eval_df = pd.read_csv(LLM_EVAL_PATH)
    for i, prompt in enumerate(llm_eval_df["prompt"]):
        response = MEDITRON_LLM.invoke(prompt)
        logger.debug(f"\n\n ***** #{i} ***** \n {response} \n")
        llm_eval_df.at[i, "meditron-7b"] = response
    llm_eval_df.to_csv(LLM_EVAL_PATH, index=False)

def main(args, llm, llm_name):
    try:
        llm_eval_df = pd.read_csv(LLM_EVAL_PATH)
    except: 
        llm_eval_df = pd.DataFrame()

    eval_df = pd.read_csv(CLINICAL_TREND_QA_PATH)
    dfs = (
        hosp_dfs(hosp_data_path=A_HOSP_DATA_PATH, depts=A_DEPTS) +
        hosp_dfs(hosp_data_path=B_HOSP_DATA_PATH, depts=B_DEPTS) +
        hosp_dfs(hosp_data_path=C_HOSP_DATA_PATH, depts=C_DEPTS)
    )

    if args.baseline:
        baseline_chain = create_baseline_rag_chain(dfs, llm=llm)
        eval_scenario(
            rag_chain=baseline_chain, 
            scenario="centralized_insecure", 
            eval_df=eval_df, 
            llm_eval_df=llm_eval_df, 
            llm_name=llm_name
        )

    if args.federated_insecure:
        # NOTE since this is insecure we can provide any userinfo to achieve same result
        fi_chain = create_rag_chain_with_source(userinfo=USERINFOS[0], llm=llm, secure=False)
        eval_scenario(
            rag_chain=fi_chain, 
            scenario="federated_insecure", 
            eval_df=eval_df, 
            llm_eval_df=llm_eval_df, 
            llm_name=llm_name
        )

    if args.federated_secure:
        for userinfo in USERINFOS:
            fs_chain = create_rag_chain_with_source(userinfo=userinfo, llm=llm)
            eval_scenario(
                rag_chain=fs_chain, 
                scenario=f"federated_secure", 
                eval_df=eval_df, 
                llm_eval_df=llm_eval_df, 
                llm_name=llm_name, 
                user=userinfo['name']
            )

    if args.eval_llm:
        llm_eval_df.to_csv(LLM_EVAL_PATH, index=False)
    else:
        # compute similarity metrics (ROUGE, BLEU)
        for ref_scenario, pred_scenario in EVAL_PAIRS:
            compute_doc_intersection(
                ref_scenario=ref_scenario,
                pred_scenario=pred_scenario, 
                eval_df=eval_df
            )

            for metric in METRICS:
                compute_metric(
                    metric=metric,
                    ref_scenario=ref_scenario,
                    pred_scenario=pred_scenario,
                    eval_df=eval_df,
                )
        eval_df.to_csv(CLINICAL_TREND_QA_PATH, index=False)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='MediRAG Eval',
                    description='Evaluation of centralized_insecure RAG, federated_insecure RAG, and federated_secure RAG')
    
    """
    Evaluation between 3 scenarios (CI, FI, FS with different userinfos)
    ClinicalBERT Embeddings
    GPT 3.5 LLM for Generation

    Results recorded in clinical_trend_qa.csv
    """
    parser.add_argument('-b', '--baseline',
                    action='store_true')  # eval baseline centralized_insecure RAG
    parser.add_argument('-f', '--federated-insecure',
                    action='store_true')  # eval federated_insecure RAG
    parser.add_argument('-s', '--federated-secure',
                    action='store_true')  # eval federated_secure RAG
    parser.add_argument('-a', '--all',
                    action='store_true')  # eval all scenarios

    """
    Evaluation of LLM response quality (GPT 3.5 vs. Flan-T5-Large vs. Meditron)
    on the same scenarios.
    Uses smaller document chunk sizes/less documents/etc. to accomodate 
    smallest Flan-T5 context window size (512 tokens)
        qdrant_small

    Results recorded in llm_eval.csv
    """
    parser.add_argument('-l', '--eval-llm',
                    action='store_true')  # eval inter-LLM responses on same scenario
    parser.add_argument('--flant5', 
                    action='store_true')  # eval scenarios with Flan-T5-Large LLM for generation
                                          # if not set, GPT 3.5 LLM is used for generation (default)
    parser.add_argument('-m', '--meditron',
                    action="store_true")  # eval with Meditron 7B LLM for generation
                                          # NOTE: the Meditron LLM inference endpoint has been shut down after evaluation
                                          # to minimize costs, so a new endpoint may be needed to reproduce the Meditron results.
    args = parser.parse_args()

    if args.all or args.eval_llm:
        args.baseline = True
        args.federated_insecure = True
        args.federated_secure = True

    if args.meditron and os.path.isfile(LLM_EVAL_PATH):
        eval_meditron()
    else:
        (llm, llm_name) = (FlanT5(), "flan-t5") if args.flant5 else (GPT_LLM, "gpt-3.5")
        logger.debug(f"*** Evaluation Type: {'LLMs' if args.eval_llm else 'Scenarios'}, Generation LLM: {llm_name} ***\n")
        main(args, llm=llm, llm_name=llm_name)