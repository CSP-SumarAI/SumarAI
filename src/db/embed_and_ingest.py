import sys
import os
import pandas as pd
import numpy as np
import chromadb
import logging
import boto3
from tqdm import tqdm

from InstructorEmbedding import INSTRUCTOR
from langchain.text_splitter import TokenTextSplitter

sys.path.insert(0, os.path.abspath("../src/data/"))
from src.data.s3_utils import read_from_s3, write_to_s3
from chromadb.config import Settings
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
server_ip = os.getenv("CHROMA_SERVER_IP")
embedding_model = INSTRUCTOR("hkunlp/instructor-large")
text_splitter = TokenTextSplitter(chunk_size=2048, chunk_overlap=0)
s3_client = boto3.client("s3")


def preprocess_transcripts(transcripts_df):
    """ 
    Function that does preprocessing steps:
    - Remove transcripts with less than 1000 characters
    - Split transcripts into chunks of 2048 tokens
    """
    # transcripts_df["transcript"] = transcripts_df["transcript"].apply(lambda x: [x[i:i+20000] for i in range(0, len(x), 20000)])
    transcripts_df["transcript_length"] = transcripts_df["transcript"].apply(lambda x: len(x))
    transcripts_df = transcripts_df[transcripts_df["transcript_length"] > 1000].copy()
    transcripts_df["transcript_chunks"] = transcripts_df["transcript"].apply(lambda x: text_splitter.split_text(x))
    # transcripts_df = transcripts_df.explode("transcript")
    return transcripts_df.reset_index(drop=True)

def create_embeddings(transcripts_df):
    """ 
    Function that creates the embeddings:
    - First creates embedding for each chunk
    - Takes average to get embeddings for one podcast
    """
    instruction = "Represent the Podcast transcript for retrieval: "
    transcripts_count = transcripts_df.shape[0]
    customized_embeddings = np.zeros((transcripts_count, 768))
    for index, row in tqdm(transcripts_df.iterrows()):
        texts_with_instructions = []
        for chunk in row["transcript_chunks"]:
            texts_with_instructions.append([instruction, chunk])
        # calculate embeddings for one podcast
        chunk_embeddings = embedding_model.encode(texts_with_instructions, show_progress_bar=False, batch_size=32)
        customized_embeddings[index,:] = np.average(chunk_embeddings, axis=0).reshape((1,768))

    return customized_embeddings

def ingest_to_chroma(embeddings, transcripts_df):

    # format data that if can be put to the chroma collection
    embeddings = embeddings.tolist()
    documents = transcripts_df["transcript"].tolist()
    ids = transcripts_df["episode"].to_list()
    metadata = transcripts_df[["episode_description", "episode_name", "show_description", "show_name"]].to_dict(orient="records")

    #loading into chroma
    #client = chromadb.PersistentClient(path=persist_directory)
    client = chromadb.HttpClient(host=server_ip, port=8000)

    # create the collection and add documents
    try:
        collection = client.get_collection("transcripts-2", embedding_function=embedding_model)
    except Exception as e:
        collection = client.create_collection("transcripts-2", embedding_function=embedding_model)
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadata,
        ids=ids,
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.info("Started process")
    
    files = s3_client.list_objects(Bucket="sumar-ai", Prefix="transcripts")["Contents"]
    processed_files_df = read_from_s3("processed_files", "metadata")
    processed_files_list = list(processed_files_df.processed_files)
    filenames = [f["Key"] for f in files if f["Key"] not in processed_files_list]
    filenames = filenames[:1]
    logging.info(f"Count of files to process {len(filenames)}.")

    for i, filename in enumerate(filenames):
        filename_csv = filename.split("/")[-1]
        logging.info(f"Started processing file {i+1}: {filename_csv}.")
        transcripts_df = read_from_s3(filename_csv, filetype=None)
        transcripts_df = preprocess_transcripts(transcripts_df)
        # transcripts_df = transcripts_df.head(5)
        # logging.info(f"Transcripts shape for file {i+1}: {transcripts_df.shape}.")
        logging.info(f"Creating embeddings for file {i+1}: {filename_csv}.")
        embeddings = create_embeddings(transcripts_df)
        logging.info(f"Uploading data to chroma for file {i+1}: {filename_csv}.")
        ingest_to_chroma(embeddings, transcripts_df)
        processed_files_df.loc[processed_files_df.index.max() + 1] = filename

    write_to_s3(processed_files_df, "processed_files", "metadata")

    logging.info("Done")