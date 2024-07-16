from langchain_core.vectorstores import VectorStoreRetriever
from langchain.docstore.document import Document
from typing import Any, Dict, List


class VectorStoreRetrieverWithScores(VectorStoreRetriever):
    def _get_relevant_documents(
        self, query: str, k: int = 4, **kwargs
    ) -> List[Document]:
        if self.search_type == "similarity" or self.search_type == "similarity_score_threshold":
            docs_and_similarities = (
                self.vectorstore.similarity_search_with_relevance_scores(
                    query, k=k, **kwargs
                )
            )
            docs = []
            for doc, sim in docs_and_similarities:
                doc.metadata["score"] = sim
                docs.append(doc)
        else:
            raise ValueError(f"search_type of {self.search_type} not allowed.")
        return docs