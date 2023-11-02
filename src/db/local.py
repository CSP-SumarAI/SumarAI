import pandas as pd
import chromadb
from util import timeit
from InstructorEmbedding import INSTRUCTOR

@timeit
def add_embeddings(collection):
    instruction = "Represent the podcast transcript document for retrieval: "

    # read transcript data
    path = 'notebooks/csv/transcripts-0[0-9].csv'
    transcripts_df = pd.read_csv(path, index_col=0)

    # Create list of instruction - transcript pairs (100 first episodes)
    transcripts_df  = transcripts_df.head(100)
    texts_with_instructions = []
    for index, row in transcripts_df.iterrows():
        texts_with_instructions.append([instruction, row["transcript"]])

    # calculate embeddings (100 first episodes took about 6 min)
    customized_embeddings = model.encode(texts_with_instructions)

    embeddings = customized_embeddings.tolist()
    documents = transcripts_df["transcript"].tolist()
    ids = transcripts_df.index.astype(str).to_list()
    metadata = transcripts_df[['episode_description', 'episode_uri', "show_name", "episode_name"]].to_dict(orient='records')

    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadata,
        ids=ids,
    )

@timeit
def get_or_create_collection(client):
    collection = client.get_or_create_collection("transcripts", embedding_function=model)
    print(f"Loaded transcripts collection with {collection.count()} items")
    if collection.count() == 0:
        print("Collection has 0 items, adding embeddings")
        add_embeddings(collection)
        print(f"Collection now has {collection.count()} items")

    return collection

@timeit
def load_model():
    return INSTRUCTOR('hkunlp/instructor-large')

@timeit
def query(prompt):
    query_texts=[['Represent the statement for retrieving podcast documents: ', prompt]]
    query_embedding = model.encode(query_texts).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=1
    )

    return results

model = load_model()
client = chromadb.PersistentClient(path=".cache/chromadb")
collection = get_or_create_collection(client)