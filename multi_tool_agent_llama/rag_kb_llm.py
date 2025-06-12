# imports

import os
import glob
from dotenv import load_dotenv
import gradio as gr
import traceback, sys

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import numpy as np
import plotly.graph_objects as go
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
db_name = "vector_db_llama"

# Load environment variables in a file called .env

load_dotenv()
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # folder of rag_kb.py
DOC_DIR  = BASE_DIR / "knowledge-base-slack"        # adjust if nested higher
folders  = [p for p in DOC_DIR.iterdir() if p.is_dir()]


if not folders:
    raise FileNotFoundError(
        f"No Markdown folders found under {DOC_DIR}. "
        "Check the path or move rag_kb.py next to the data."
    )

def add_metadata(doc, doc_type):
    doc.metadata["doc_type"] = doc_type
    return doc

text_loader_kwargs = {'encoding': 'utf-8'}

documents = []
for folder in folders:
    doc_type = os.path.basename(folder)
    loader = DirectoryLoader(folder, glob="**/*.md", loader_cls=TextLoader, loader_kwargs=text_loader_kwargs)
    folder_docs = loader.load()
    documents.extend([add_metadata(doc, doc_type) for doc in folder_docs])

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(documents)

print(f"Total number of chunks: {len(chunks)}")
print(f"Document types found: {set(doc.metadata['doc_type'] for doc in documents)}")

from langchain_huggingface import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


if os.path.exists(db_name):
    Chroma(persist_directory=db_name, embedding_function=embeddings).delete_collection()


vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=db_name)
print(f"Vectorstore created with {vectorstore._collection.count()} documents")


collection = vectorstore._collection
count = collection.count()

sample_embedding = collection.get(limit=1, include=["embeddings"])["embeddings"][0]
dimensions = len(sample_embedding)
print(f"There are {count:,} vectors with {dimensions:,} dimensions in the vector store")

result = collection.get(include=['embeddings', 'documents', 'metadatas'])
vectors = np.array(result['embeddings'])
documents = result['documents']
metadatas = result['metadatas']
doc_types = [metadata['doc_type'] for metadata in metadatas]
doc_type_set = set(doc_types)  # Renamed variable to avoid conflict
print(doc_type_set)
colors = [['blue'][['team_a'].index(t)] for t in doc_types]

def get_initials(llm = None):
    if llm is None:
        llm = ChatOpenAI(temperature=0.7, name='llama3.2', base_url='http://localhost:11434/v1', api_key='ollama')
    retriever = vectorstore.as_retriever()
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever, memory=memory)
    return conversation_chain



def chat(question: str, history=None, llm = None):
    conversation_chain = get_initials(llm)
    if history is None:
        history = []                       # empty history for first turn
    result = conversation_chain.invoke(
        {"question": question, "chat_history": history}
    )
    return result["answer"]