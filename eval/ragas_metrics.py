import ast
import os
import pandas as pd
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from app.secret import OPENAI_KEY
from ragas import evaluate
from ragas.metrics import (
    context_relevancy,
    answer_relevancy,
    faithfulness,
)
from datasets import Dataset
os.environ["OPENAI_API_KEY"] = OPENAI_KEY

ragas_dataset = pd.read_csv("eval/ragas_dataset.csv")
# original_dataset = pd.read_csv("eval/clinical_trend_qa.csv")
# for col in ragas_dataset.columns:
#     if col in original_dataset.columns:
#         ragas_dataset[col] = original_dataset[col]
# ragas_dataset.to_csv("eval/ragas_dataset1.csv", index=False)

scenarios = [
    "federated_insecure",
    "federated_secure_A.phys.neur",
    "federated_secure_A.phys",
    "federated_secure_A.tech.rad",
    "federated_secure_A.admin",
    "federated_secure_A.nurse",
    "federated_secure_B.phys",
    "federated_secure_B.nurse",
    "federated_secure_C.research",
]

for scenario in scenarios:
    data = {
        "question": ragas_dataset['question'].tolist(),
        "answer": ragas_dataset[scenario].tolist(),
        "contexts": [ast.literal_eval(docs_str) for docs_str in ragas_dataset[f"{scenario}_docs"]],
    }
    # print(data)
    dataset = Dataset.from_dict(data)

    result = evaluate(
        dataset,
        metrics=[
            context_relevancy,
            faithfulness,
            answer_relevancy,
        ],
    )

    df = result.to_pandas()
    df.to_csv(f"eval/ragas_results/{scenario}.csv")