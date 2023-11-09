import sys
import os
import pandas as pd
import numpy as np
import chromadb
import logging
import boto3
from tqdm import tqdm
import tiktoken

from InstructorEmbedding import INSTRUCTOR
from langchain.text_splitter import TokenTextSplitter

sys.path.insert(0, os.path.abspath("../src/data/"))
from src.data.s3_utils import read_from_s3, write_to_s3
from chromadb.config import Settings
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
server_ip = os.getenv("CHROMA_SERVER_IP")
text_splitter = TokenTextSplitter(chunk_size=2048, chunk_overlap=0)
encoding = tiktoken.get_encoding("gpt2")
s3_client = boto3.client("s3")
ingest_mode = os.getenv("INGEST_MODE", "default")
ingest_file_count = int(os.getenv("INGEST_FILE_COUNT", 1))

if ingest_mode == "timestamps":
    embedding_model = INSTRUCTOR("hkunlp/instructor-large")
else:
    embedding_model = INSTRUCTOR("hkunlp/instructor-large")

def preprocess_transcripts(transcripts_df):
    """ 
    Function that does preprocessing steps:
    - Remove transcripts with less than 1000 characters
    - Split transcripts into chunks of 2048 tokens
    """
    if ingest_mode == "timestamps":
        transcripts_df["episode_speaker"] = transcripts_df["episode"] + transcripts_df["speakerTag"].astype(str)
        transcripts_df["transcript"] = np.where(transcripts_df["episode_speaker"] == transcripts_df["episode_speaker"].shift(-1), transcripts_df["transcript"] + " " + transcripts_df["transcript"].shift(-1), transcripts_df["transcript"])
        transcripts_df["group"] = (transcripts_df["episode_speaker"] != transcripts_df["episode_speaker"].shift()).cumsum()
        transcripts_df.set_index(transcripts_df.groupby("group").cumcount(), inplace = True)
        transcripts_df["transcript"] = np.where(transcripts_df.index%2==0, transcripts_df["transcript"], np.nan)
        transcripts_df["endTime"] = np.where(pd.isna(transcripts_df.transcript.shift(-1)), transcripts_df["endTime"].shift(-1), transcripts_df["endTime"])
        transcripts_df["paragraph_length"] = transcripts_df.endTime - transcripts_df.startTime
        transcripts_df = transcripts_df.dropna().reset_index(drop=True)
        transcripts_df["token_count"] = transcripts_df.transcript.apply(lambda x: len(encoding.encode(x)))
        transcripts_df = transcripts_df[(transcripts_df.token_count > 20)]
    else:
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
    for index, row in transcripts_df.iterrows():
        logging.info(f"Creating embeddings for episode {index+1}/{transcripts_count}.")
        texts_with_instructions = []
        for chunk in row["transcript_chunks"]:
            texts_with_instructions.append([instruction, chunk])
        # calculate embeddings for one podcast
        chunk_embeddings = embedding_model.encode(texts_with_instructions, show_progress_bar=False, batch_size=32)
        customized_embeddings[index,:] = np.average(chunk_embeddings, axis=0).reshape((1,768))

    return customized_embeddings

def create_embeddings_timestamps(transcripts_df):
    """ 
    Function that creates the embeddings for shorter timestamped trancript parts:
    """
    instruction = "Represent the Podcast paragraph for retrieval: "
    texts_with_instructions = []
    for index, row in transcripts_df.iterrows():
        texts_with_instructions.append([instruction, row["transcript"]])
    customized_embeddings = embedding_model.encode(texts_with_instructions, show_progress_bar=False, batch_size=32)
    return customized_embeddings

def ingest_to_chroma(embeddings, transcripts_df):

    # format data that if can be put to the chroma collection
    embeddings = embeddings.tolist()
    documents = transcripts_df["transcript"].tolist()

    if ingest_mode == "timestamps":
        ids = transcripts_df["id"].to_list()
        metadata = transcripts_df[["episode", "startTime", "endTime", "speakerTag"]].to_dict(orient="records")
        collection_name = "transcript-timestamps"
    else:
        ids = transcripts_df["episode"].to_list()
        metadata = transcripts_df[["episode_description", "episode_name", "show_description", "show_name"]].to_dict(orient="records")
        collection_name = "transcripts-2"

    #loading into chroma
    #client = chromadb.PersistentClient(path=persist_directory)
    client = chromadb.HttpClient(host=server_ip, port=8000)

    # create the collection and add documents
    try:
        collection = client.get_collection(collection_name, embedding_function=embedding_model)
    except Exception as e:
        collection = client.create_collection(collection_name, embedding_function=embedding_model)
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadata,
        ids=ids,
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.info(f"Started process. Ingestion mode: {ingest_mode}")
    
    processing_log_file = "processed_files_timestamps" if ingest_mode == "timestamps" else "processed_files"
    filetype = "transcript_timestamps" if ingest_mode == "timestamps" else "transcripts"
    files = s3_client.list_objects(Bucket="sumar-ai", Prefix=filetype)["Contents"]
    processed_files_df = read_from_s3(processing_log_file, "metadata")
    processed_files_list = list(processed_files_df.processed_files)
    filenames = [f["Key"] for f in files if f["Key"] not in processed_files_list]
    filenames = filenames[:ingest_file_count]
    logging.info(f"Count of files to process {len(filenames)}.")

    for i, filename in enumerate(filenames):
        filename_csv = filename.split("/")[-1]
        logging.info(f"Started processing file {i+1}: {filename_csv}.")
        transcripts_df = read_from_s3(filename_csv, filetype=filetype)
        # transcripts_df = transcripts_df.head(200)
        transcripts_df = preprocess_transcripts(transcripts_df)
        logging.info(f"Transcripts dataframe shape for file {filename_csv}: {transcripts_df.shape}.")
        logging.info(f"Creating embeddings for file {i+1}: {filename_csv}.")
        if ingest_mode == "timestamps":
            embeddings_list = []
            df_list = []
            transcripts_df["id"] = transcripts_df["episode"] + transcripts_df.index.astype(str)
            episodes = transcripts_df.episode.unique()
            grouped = transcripts_df.groupby(transcripts_df.episode)
            for j, episode in enumerate(episodes):
                logging.info(f"Creating embeddings for episode {j+1}/{len(episodes)}.")
                episode_df = grouped.get_group(episode)
                embeddings_list.append(create_embeddings_timestamps(episode_df))
                df_list.append(episode_df)
                if len(embeddings_list) == 100:
                    embeddings = np.concatenate(embeddings_list, axis=0)
                    df = pd.concat(df_list, axis=0)
                    logging.info(f"Shape of embeddings array {embeddings.shape}.")
                    logging.info(f"Uploading data to chroma for episodes {j-98}-{j+1} from file {filename_csv}.")
                    ingest_to_chroma(embeddings, df)
                    embeddings_list = []
                    df_list = []
        else:
            embeddings = create_embeddings(transcripts_df)
            logging.info(f"Uploading data to chroma for file {i+1}: {filename_csv}.")
            ingest_to_chroma(embeddings, transcripts_df)
        processed_files_df.loc[processed_files_df.index.max() + 1] = filename

    write_to_s3(processed_files_df, processing_log_file, "metadata")

    logging.info("Done")