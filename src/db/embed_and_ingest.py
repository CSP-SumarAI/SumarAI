import sys
import os
import pandas as pd
import chromadb
import logging
import boto3

from InstructorEmbedding import INSTRUCTOR

sys.path.insert(0, os.path.abspath('../src/data/'))
from src.data.s3_utils import read_from_s3
from chromadb.config import Settings
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
server_ip = os.getenv('CHROMA_SERVER_IP')
embedding_model = INSTRUCTOR('hkunlp/instructor-large')
s3_client = boto3.client('s3')

def preprocess_transcripts(transcripts_df):
    """ 
    Function that does preprocessing steps:
    - Split transcripts into chunks of 20000 characters
    - Explode to new rows
    - Remove transcripts with less than 1000 characters
    """
    transcripts_df['transcript'] = transcripts_df['transcript'].apply(lambda x: [x[i:i+20000] for i in range(0, len(x), 20000)])
    transcripts_df = transcripts_df.explode('transcript')
    transcripts_df['transcript_length'] = transcripts_df['transcript'].apply(lambda x: len(x))
    transcripts_df = transcripts_df[transcripts_df['transcript_length'] > 1000].reset_index(drop=True)
    return transcripts_df

def create_embeddings(transcripts_df):
    instruction = "Represent the Podcast transcript for retrieval: "
    texts_with_instructions = []
    for index, row in transcripts_df.iterrows():
        texts_with_instructions.append([instruction, row["transcript"]])

    # calculate embeddings (100 first episodes took about 6 min)
    customized_embeddings = embedding_model.encode(texts_with_instructions, show_progress_bar=True, batch_size=20)

    return customized_embeddings

def ingest_to_chroma(embeddings, transcripts_df):

    # format data that if can be put to the chroma collection
    embeddings = embeddings.tolist()
    documents = transcripts_df["transcript"].tolist()
    ids = transcripts_df.index.astype(str).to_list()
    metadata = transcripts_df[['episode_description', 'episode_name']].to_dict(orient='records')

    #loading into chroma
    #client = chromadb.PersistentClient(path=persist_directory)
    client = chromadb.HttpClient(host=server_ip, port=8000)

    # create the collection and add documents
    try:
        client.delete_collection("transcripts")
    except Exception as e:
        pass
    collection = client.create_collection("transcripts", embedding_function=embedding_model)
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadata,
        ids=ids,
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.info('Started process')
    
    files = s3_client.list_objects(Bucket='sumar-ai', Prefix='transcripts')['Contents']
    processed_files_df = read_from_s3('processed_files', 'metadata')
    processed_files_list = list(processed_files_df.processed_files)
    filenames = [f['Key'] for f in files if f['Key'] not in processed_files_list]
    logging.info(f'Count of files to process {len(filenames)}.')

    for i, filename in enumerate(filenames):
        filename = filename.split('/')[-1]
        logging.info(f'Started processing file {i+1}: {filename}.')
        transcripts_df = read_from_s3(filename, filetype=None)
        transcripts_df = preprocess_transcripts(transcripts_df)
        logging.info(f'Creating embeddings for file {i+1}: {filename}.')
        embeddings = create_embeddings(transcripts_df)
        logging.info(f'Uploading data to chroma for file {i+1}: {filename}.')
        ingest_to_chroma(embeddings, transcripts_df)

    logging.info('Done')