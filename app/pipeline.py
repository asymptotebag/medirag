from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from operator import itemgetter

import os
import sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from app.config import REGISTERED_HOSPITAL_ENDPOINTS
from app.secret import OPENAI_KEY
from core.federated_retriever import RootRetriever

# build rag chain
TEMPLATE = """You are an assistant for clinical question answering. Read the following clinical note excerpts:
           {context}

           The above notes may not all be relevant. If no notes were provided, or there is insufficient information to answer, please say so without stating false information.
           Please answer in your own words, providing evidence from the relevant notes: {question}"""
PROMPT = ChatPromptTemplate.from_template(TEMPLATE)
SEARCH_KWARGS = {"k": 10, "fetch_k": 20}
# SEARCH_KWARGS = {"k": 4, "fetch_k": 20}

GPT_LLM = ChatOpenAI(model="gpt-3.5-turbo-0125", openai_api_key=OPENAI_KEY, temperature=0)

def format_docs(docs):
    return "\n\n".join(doc["kwargs"]["page_content"] for doc in docs)
    
def create_rag_chain_with_source(userinfo, hospital_retrieve_uris=REGISTERED_HOSPITAL_ENDPOINTS, llm=GPT_LLM, secure=True): 
    root_retriever = RootRetriever(hospital_retrieve_uris=hospital_retrieve_uris,
                                   userinfo=userinfo,
                                   search_kwargs=(SEARCH_KWARGS | {"secure": secure}))

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
        {"documents": root_retriever, "question": RunnablePassthrough()}
    ) | {
        "answer": rag_chain_from_docs,
        "documents": lambda input: [doc for doc in input["documents"]],
        "prompt": lambda input: PROMPT.format(context=format_docs(input["documents"]), question=input["question"]),
    }

    return rag_chain_with_source
