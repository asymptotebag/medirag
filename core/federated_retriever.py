import pandas as pd
import json
import requests
import time
import spacy
from functools import cached_property
from langchain_community.document_loaders import DataFrameLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.pydantic_v1 import BaseModel
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.schema import BaseRetriever, Document
from langchain_community.vectorstores import Qdrant
from py_abac import PDP, AccessRequest
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from core.full_df_loader import AllColumnsDataFrameLoader
from core.util import chunk_df, prefix_metadata
from core.vectorstore_retriever_with_scores import VectorStoreRetrieverWithScores
from requests.exceptions import HTTPError

from concurrent.futures import ProcessPoolExecutor, as_completed, wait

from typing import Any, Dict, List, Optional

import logging
logger = logging.getLogger("log")


CLINICAL_BERT = HuggingFaceEmbeddings(
    model_name="emilyalsentzer/Bio_ClinicalBERT",
    model_kwargs={},
    encode_kwargs={"normalize_embeddings": True},
)

# NOTE: very good results, but expensive
# from langchain_openai import OpenAIEmbeddings
# CLINICAL_BERT = OpenAIEmbeddings(model='text-embedding-3-small', openai_api_key=OPENAI_KEY)

# NOTE: recreate variables for debug only
QDRANT_RECREATE = True
QDRANT_BASE_RECREATE = False

class LeafRetriever(BaseRetriever, BaseModel):
    id: str  # unique identifier
    abac_gate: Optional[PDP] = None  # "right to search": access policies for the entire leaf retriever
    abac_pdp: Optional[PDP] = None  # "right to retrieve": access policies of leaf's resources
    db_path: str  # where (on the client side) the vector database will be persisted
    df: pd.DataFrame  # data stored by this leaf
    text_col: str | None = None  # if None, this leaf assumed to contain unstructured data, else the column in df containing longform text

    @cached_property
    def vectorstore_retriever(self) -> VectorStoreRetriever:
        if self.text_col:  # split into chunks if this leaf contains unstructured data
            self.df = chunk_df(df=self.df, chunk_col=self.text_col)
            prefix_metadata(df=self.df, chunk_col=self.text_col, metadata_cols=["name"])
            docs = DataFrameLoader(self.df).load()
        else:  # for structured data, all columns go into document page_content
            docs = AllColumnsDataFrameLoader(self.df).load()

        # logger.debug(f"DataFrameLoader returned {len(docs)} docs, first one is:\n{docs[0]}")
        t1 = time.perf_counter(), time.process_time()
        vs = (
            Qdrant.from_documents(
                documents=docs,
                embedding=CLINICAL_BERT,
                path=self.db_path,
                collection_name=f"leaf_{self.id}",
            )
            if QDRANT_RECREATE
            else Qdrant(client=QdrantClient(path=self.db_path), collection_name=f"leaf_{self.id}", embeddings=CLINICAL_BERT)
        )
        t2 = time.perf_counter(), time.process_time()

        with open("qdrant_report.txt", "a") as report:
            report.write("****************************\n")
            report.write(f"ID={self.id}\n")
            report.write(f"Real time: {t2[0] - t1[0]:.2f} seconds\n")
            report.write(f"CPU time: {t2[1] - t1[1]:.2f} seconds\n")
            report.write("****************************\n")

        return VectorStoreRetrieverWithScores(vectorstore=vs)
    
    class Config:
        keep_untouched = (cached_property,)  # needed to make BaseModel work with cached_property

    def _get_relevant_documents(
        self, query: str, search_kwargs: Dict[str, Any], userinfo: dict = None, **kwargs
    ) -> List[Document]:
        logger.debug(f"LEAF RETRIEVER REACHED id={self.id}")

        # NOTE: for evaluation only, do not use abac if search_kwargs["secure"] == False
        secure = search_kwargs.get("secure", True)

        # deny-based pdp at the start here too, to avoid searching relevant docs in leaf retrievers we can't access
        router_req_json = {
            "subject": {
                "id": userinfo.get('sub') if userinfo else None,
                "attributes": userinfo or {},
            },
            "resource": {
                "id": self.id,
                "attributes": self.metadata or None,
            },
            "action": {
                "id": "",
                "attributes": {"method": "read"}
            },
            "context": {}
        }
        if secure and self.abac_gate and not self.abac_gate.is_allowed(AccessRequest.from_json(router_req_json)):
            logger.debug(f"DENIED @ {self.id}! userinfo: {userinfo}")
            return []
        logger.debug(f"ALLOWED @ {self.id}! userinfo: {userinfo}")

        # passed gate; perform retrieval
        flt = (
            rest.Filter(
                should=[
                    rest.FieldCondition(
                        key=f"metadata.{attr}",
                        match=rest.MatchAny(any=vals),
                    )
                    for attr, vals in search_kwargs["filters"].items()
                ]
            )
            if "filters" in search_kwargs and len(search_kwargs["filters"]) > 0
            else None
        )

        relevant_docs = self.vectorstore_retriever.get_relevant_documents(query=query, filter=flt, k=search_kwargs.get("fetch_k"), **kwargs)
        # logger.debug(f"\n\nRELEVANT DOCS:\n{relevant_docs}")
        if not secure or not self.abac_pdp:
            return sorted(relevant_docs, key = lambda d : d.metadata["score"], reverse=True)[:search_kwargs["k"]]

        accessible_relevant_docs = []
        for doc in relevant_docs:
            req_json = {
                "subject": {
                    "id": "",
                    "attributes": userinfo or {},
                },
                "resource": {
                    "id": "",
                    "attributes": doc.metadata,
                },
                "action": {
                    "id": "",
                    "attributes": {"method": "read"}
                },
                "context": {}
            }
            request = AccessRequest.from_json(req_json)
            if self.abac_pdp.is_allowed(request):
                # logger.debug(f"ALLOW_DOC: {doc.metadata}")
                doc.metadata.update(self.metadata or {})  # add leaf retriever's metadata to document metadata
                accessible_relevant_docs.append(doc)
            # else:
                # logger.debug(f"DENY_DOC: {doc.metadata}")

        return sorted(accessible_relevant_docs, key = lambda d : d.metadata["score"], reverse=True)[:search_kwargs["k"]]


class RouterRetriever(BaseRetriever, BaseModel):
    id: str
    children: List[BaseRetriever]  # contains LeafRetrievers or RouterRetrievers, depending on level
    abac_gate: Optional[PDP] = None  # each retriever manages its own deny-based pdp and should return docs=[] if denied (rather than managing access for its children)

    def _get_relevant_documents(
        self, query: str, search_kwargs: Dict[str, Any], userinfo: dict = None, **kwargs
    ) -> List[Document]:
        # NOTE: for evaluation only, do not use abac if search_kwargs["secure"] == False
        secure = search_kwargs.get("secure", True)

        # create request json based on requesting user's info, match against abac_pdp
        router_req_json = {
            "subject": {
                "id": userinfo.get('sub') if userinfo else None,
                "attributes": userinfo or {},
            },
            "resource": {
                "id": self.id,
                "attributes": self.metadata or None,
            },
            "action": {
                "id": "",
                "attributes": {"method": "read"}
            },
            "context": {}
        }
        if secure and self.abac_gate and not self.abac_gate.is_allowed(AccessRequest.from_json(router_req_json)):
            logger.debug(f"DENIED @ {self.id}! userinfo: {userinfo}")
            return []

        logger.debug(f"ALLOWED @ {self.id}! userinfo: {userinfo}")
        docs = []
        for child in self.children:
            docs.extend(child.get_relevant_documents(query=query, userinfo=userinfo, search_kwargs=search_kwargs, **kwargs))

        # Truncate to top K documents by similarity score across all children retrievers
        # NOTE: we assume that cross-retriever similarity scores can be compared
        # as long as we use the same embedding scheme (ClinicalBERT) for all
        return sorted(docs, key = lambda d : d.to_json()["kwargs"]["metadata"]["score"], reverse=True)[:search_kwargs["k"]]


class RootRetriever(BaseRetriever, BaseModel):
    hospital_retrieve_uris: List[str]
    userinfo: dict
    search_kwargs: Dict[str, Any]

    def _retrieve(self, retrieve_uri, params):
        print(f"PARALLEL RETRIEVE: {retrieve_uri}")
        try:
            resp = requests.get(retrieve_uri, params=params)
            resp.raise_for_status()
            resp_json = resp.json()
            return resp_json.get("docs", [])
        except HTTPError as e:
            logger.debug(f"HTTPError retrieve_uri={retrieve_uri}: {e}")
        except:
            logger.debug(f"Error occurred retrieve_uri={retrieve_uri}")


    def _get_relevant_documents(
        self, query: str, **kwargs
    ) -> List[Document]:
        t1 = time.perf_counter(), time.process_time()
        docs = []
        self.search_kwargs["filters"] = {}  # for qdrant filtering, { doc attribute : [list of possible values]} e.g. { "name" : ["Edward Fisher", "Janet Aguilar"]}

        # use spacy's ner to detect queries about specific people
        ner = spacy.load("en_core_web_sm")
        names = [(ent.text[:ent.text.rfind("'")] if "'" in ent.text else ent.text) for ent in ner(query).ents if ent.label_ == "PERSON"]
        if names:
            # logger.debug(f"names detected in query: {names}")
            self.search_kwargs["filters"]["name"] = names

        retrieve_futs = []
        with ProcessPoolExecutor() as executor:
            params = {'query': query, 'userinfo': json.dumps(self.userinfo), 'search_kwargs': json.dumps(self.search_kwargs)}
            for retrieve_uri in self.hospital_retrieve_uris:
                retrieve_futs.append(executor.submit(self._retrieve, retrieve_uri, params))
            # for fut in as_completed(retrieve_futs):
            done, not_done = wait(retrieve_futs)
            while len(done) > 0:
                fut = done.pop()
                docs.extend(fut.result())
            # executor.shutdown()

        # Truncate to top K documents by similarity score across all children retrievers
        # NOTE: we assume that cross-retriever similarity scores can be compared
        # as long as we use the same embedding scheme (ClinicalBERT) for all
        final_k = sorted(docs, key = lambda d : d["kwargs"]["metadata"]["score"], reverse=True)[:self.search_kwargs["k"]]
        t2 = time.perf_counter(), time.process_time()

        with open("retrieval_report.txt", "a") as report:
            report.write("****************************\n")
            report.write(f"N_URIS={len(self.hospital_retrieve_uris)}\n")
            report.write(f"Real time: {t2[0] - t1[0]:.2f} seconds\n")
            report.write(f"CPU time: {t2[1] - t1[1]:.2f} seconds\n")
            report.write("****************************\n")

        logger.debug(f"\n\nFINAL K DOCS:\n{final_k}")
        return final_k


"""
BaselineRetriever class for evaluation/testing purposes only.
Initialize with a list of Documents,
e.g. by appending the output of DataFrameLoaders on all CSVs to include in the retriever.
"""
class BaselineRetriever(BaseRetriever, BaseModel):
    docs: List[Document]
    db_path: str  # where (on the client side) the vector database will be persisted
    search_kwargs: Dict[str, Any]
    abac_gate: Optional[PDP] = None
    abac_pdp: Optional[PDP] = None

    @cached_property
    def vectorstore_retriever(self) -> VectorStoreRetriever:
        vs = (
            Qdrant.from_documents(
                documents=self.docs,
                embedding=CLINICAL_BERT,
                path=self.db_path,
                collection_name=f"baseline",
            )
            if QDRANT_BASE_RECREATE
            else Qdrant(client=QdrantClient(path=self.db_path), collection_name="baseline", embeddings=CLINICAL_BERT)
        )

        return VectorStoreRetrieverWithScores(vectorstore=vs)
    
    class Config:
        keep_untouched = (cached_property,)  # needed to make BaseModel work with cached_property

    def _get_relevant_documents(
        self, query: str, userinfo: dict = None, **kwargs
    ) -> List[Document]:
        # should be the same method as leaf retriever
        # deny-based pdp at the start here too, to avoid searching relevant docs in leaf retrievers we can't access
        router_req_json = {
            "subject": {
                "id": userinfo.get('sub') if userinfo else None,
                "attributes": userinfo or {},
            },
            "resource": {
                "id": "baseline",
                "attributes": self.metadata or None,
            },
            "action": {
                "id": "",
                "attributes": {"method": "read"}
            },
            "context": {}
        }
        if self.abac_gate and not self.abac_gate.is_allowed(AccessRequest.from_json(router_req_json)):
            logger.debug(f"DENIED! userinfo: {userinfo}")
            return []
        
        self.search_kwargs["filters"] = {}  # for qdrant filtering, { doc attribute : [list of possible values]} e.g. { "name" : ["Edward Fisher", "Janet Aguilar"]}
        # use spacy's ner to detect queries about specific people
        ner = spacy.load("en_core_web_sm")
        names = [(ent.text[:ent.text.rfind("'")] if "'" in ent.text else ent.text) for ent in ner(query).ents if ent.label_ == "PERSON"]
        if names:
            logger.debug(f"names detected in query: {names}")
            self.search_kwargs["filters"]["name"] = names

        # passed gate; perform retrieval
        flt = (
            rest.Filter(
                should=[
                    rest.FieldCondition(
                        key=f"metadata.{attr}",
                        match=rest.MatchAny(any=vals),
                    )
                    for attr, vals in self.search_kwargs["filters"].items()
                ]
            )
            if "filters" in self.search_kwargs and len(self.search_kwargs["filters"]) > 0
            else None
        )
        
        relevant_docs = self.vectorstore_retriever.get_relevant_documents(query=query, filter=flt, k=self.search_kwargs.get("fetch_k"), **kwargs)
        # logger.debug(f"\n\nRELEVANT DOCS:\n{relevant_docs}")
        if not self.abac_pdp:
             relevant_docs = sorted(relevant_docs, key = lambda d : d.metadata["score"], reverse=True)
             return [d.to_json() for d in relevant_docs][:self.search_kwargs["k"]]

        accessible_relevant_docs = []
        for doc in relevant_docs:
            req_json = {
                "subject": {
                    "id": "",
                    "attributes": userinfo or {},
                },
                "resource": {
                    "id": "",
                    "attributes": doc.metadata,
                },
                "action": {
                    "id": "",
                    "attributes": {"method": "read"}
                },
                "context": {}
            }
            request = AccessRequest.from_json(req_json)
            if self.abac_pdp.is_allowed(request):
                doc.metadata.update(self.metadata or {})  # add leaf retriever's metadata to document metadata
                accessible_relevant_docs.append(doc)

        accessible_relevant_docs = sorted(accessible_relevant_docs, key = lambda d : d.metadata["score"], reverse=True)
        final_k = [d.to_json() for d in accessible_relevant_docs][:self.search_kwargs["k"]]
        logger.debug(f"\n\nFINAL K DOCS:\n{final_k}")
        return final_k