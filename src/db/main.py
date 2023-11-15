from util import timeit
from InstructorEmbedding import INSTRUCTOR
import chromadb
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

@timeit
def load_model():
    return INSTRUCTOR(model_name)

@timeit
def query(prompt):
    query_texts=[["Represent the statement for retrieving podcast documents: ", prompt]]
    query_embedding = model.encode(query_texts).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    return results

model_name = "hkunlp/instructor-large"
model = load_model()
ef = chromadb.utils.embedding_functions.InstructorEmbeddingFunction(model_name=model_name)
client = chromadb.HttpClient(host=os.getenv("CHROMA_SERVER_IP"), port=8000)
collection = client.get_collection("transcripts-2", embedding_function=ef)
if collection == None:
    raise Exception("Could not get collection")