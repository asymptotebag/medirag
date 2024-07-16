import logging
import os
import pandas as pd
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from app.pipeline import create_rag_chain_with_source, GPT_LLM

logger = logging.getLogger("log")
logger.propagate = False

fileHandler = logging.FileHandler("logs/log.txt")
logger.addHandler(fileHandler)
logger.setLevel(logging.DEBUG)

CLINICAL_TREND_QA_PATH = "eval/ragas_dataset.csv"
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

def eval_scenario(rag_chain, scenario: str, eval_df: pd.DataFrame, user: str | None = None):
    scenario_name = scenario + '_' + user if user else scenario
    print(f"evaluating {scenario_name} scenario", end="")
    logger.debug(f"\n\n*** EVALUATING SCENARIO: {scenario_name.upper()} ***\n")

    for i, query in enumerate(eval_df["question"]):    
        response = rag_chain.invoke(query)
        eval_df.at[i, f"{scenario_name}"] = response["answer"]
        eval_df.at[i, f"{scenario_name}_docs"] = str([doc['kwargs']['page_content'] for doc in response["documents"]])

    print()

def main(llm):
    eval_df = pd.read_csv(CLINICAL_TREND_QA_PATH)

    # NOTE since this is insecure we can provide any userinfo to achieve same result
    fi_chain = create_rag_chain_with_source(userinfo=USERINFOS[0], llm=llm, secure=False)
    eval_scenario(
        rag_chain=fi_chain, 
        scenario="federated_insecure", 
        eval_df=eval_df, 
    )

    for userinfo in USERINFOS:
        fs_chain = create_rag_chain_with_source(userinfo=userinfo, llm=llm)
        eval_scenario(
            rag_chain=fs_chain, 
            scenario=f"federated_secure", 
            eval_df=eval_df, 
            user=userinfo['name']
        )

    eval_df.to_csv(CLINICAL_TREND_QA_PATH, index=False)


if __name__ == "__main__":
    main(llm=GPT_LLM)