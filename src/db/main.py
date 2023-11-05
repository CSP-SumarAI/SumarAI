from util import timeit
from InstructorEmbedding import INSTRUCTOR
import chromadb
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

@timeit
def load_model():
    return INSTRUCTOR('hkunlp/instructor-large')

@timeit
def query(prompt):
    query_texts=[['Represent the statement for retrieving podcast documents: ', prompt]]
    query_embedding = model.encode(query_texts).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    return results

model = load_model()
client = chromadb.HttpClient(host=os.getenv("CHROMA_SERVER_IP"), port=8000)
collection = client.get_collection("transcripts-2", embedding_function=model)
if collection == None:
    raise Exception("Could not get collection")