from util import timeit
from InstructorEmbedding import INSTRUCTOR
import chromadb
from dotenv import load_dotenv, find_dotenv
import os
import pandas as pd
import streamlit as st

load_dotenv(find_dotenv())

@timeit
def load_model():
    return INSTRUCTOR(model_name)

@timeit
def query(prompt, n=3):
    query_texts=[["Represent the statement for retrieving podcast documents: ", prompt]]
    query_embedding = model.encode(query_texts).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n,
    )

    for k in results.keys():
        if results[k]:
            results[k][0] = results[k][0][n-3:n]
    return results

@timeit
def queryTimestamps(prompt, episode):

    query_texts=[["Represent the Podcast query for retrieving relevant paragraphs: ",prompt]]
    query_embedding = model.encode(query_texts).tolist()
    results2 = timestamp_collection.query(
        query_embeddings=query_embedding,
        n_results=5,
        where={"episode": episode},
)
    result2_df = pd.json_normalize(results2["metadatas"][0])
    result2_df["paragraph"] = results2["documents"][0]    
    return result2_df
    

def episode_selected(result):
    result_df = pd.json_normalize(result["metadatas"][0])
    result_df["episode_id"] = result["ids"][0]

    return result_df

@st.cache_data
def collection_size():
    episode_count = collection.count()
    timestamped_count = len(pd.DataFrame(timestamp_collection.get(include=["metadatas"])["metadatas"]).episode.unique())
    return episode_count, timestamped_count


model_name = "hkunlp/instructor-large"
model = load_model()
ef = chromadb.utils.embedding_functions.InstructorEmbeddingFunction(model_name=model_name)
client = chromadb.HttpClient(host=os.getenv("CHROMA_SERVER_IP"), port=8000)
collection = client.get_collection("transcripts-2", embedding_function=ef)
if collection == None:
    raise Exception("Could not get trancsript collection")
timestamp_collection = client.get_collection(name="transcript-timestamps", embedding_function=ef)
if timestamp_collection == None:
    raise Exception("Could not get timestamp collection")