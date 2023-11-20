from util import timeit
from InstructorEmbedding import INSTRUCTOR
import chromadb
from dotenv import load_dotenv, find_dotenv
import os
import pandas as pd

load_dotenv(override=True)

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



model_name = "hkunlp/instructor-large"
model = INSTRUCTOR(model_name)
ef = chromadb.utils.embedding_functions.InstructorEmbeddingFunction(model_name=model_name)
server_ip = os.getenv('CHROMA_SERVER_IP')
client = chromadb.HttpClient(host=server_ip, port=8000)
#print("Current collections in chromadb server: ", client.list_collections())
timestamp_collection = client.get_collection(name="transcript-timestamps", embedding_function=ef)

if timestamp_collection == None:
    raise Exception("Could not get collection")