import json
import sys
import os
import pathlib
import pandas as pd
import awswrangler as wr
import boto3
import tarfile
import logging

sys.path.insert(0, os.path.abspath("../src/data/"))
from src.data.s3_utils import write_to_s3
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

bucket = os.getenv('S3_BUCKET')
region = os.getenv('REGION')
local_mode = os.getenv('LOCAL_MODE', False)
parse_mode = os.getenv('PARSE_MODE', 'default')

root = str(pathlib.Path().absolute()).split("notebooks")[0]
directory = root + '/podcasts-no-audio-13GB/'
metadatafile = 'metadata.tsv'
tarfiles = ['podcasts-transcripts-0to2.tar.gz', 'podcasts-transcripts-3to5.tar.gz', 'podcasts-transcripts-6to7.tar.gz']
        
def parse_times_and_speakers(filepath, file=None, filename=None):
    if filepath:
        root = str(pathlib.Path().absolute()).split("notebooks")[0]
        rootpath = root + filepath
        for path in filepath, rootpath, file:
            try:                                                           
                with open(path) as data_file:    
                    data = json.load(data_file)
                    break
            except Exception as e:
                print(e)
                continue
    else:
        data = json.load(file)
        filepath = filename
    
    df = pd.json_normalize(data['results'], 'alternatives').dropna(subset=['transcript', 'words'])
    df['startTime'] = df.words.apply(lambda x: min([float(v[:-1]) for i in x for k, v in i.items() if k == 'startTime']))
    df['endTime'] = df.words.apply(lambda x: max([float(v[:-1]) for i in x for k, v in i.items() if k == 'endTime']))

    # Last alternatives tag has the speakerTag information so it has to be parsed separately
    df2 = pd.json_normalize(data['results'][-1], ['alternatives', 'words'], errors='ignore')
    df2['startTime'] = df2.startTime.apply(lambda x: float(x[:-1]))
    df2 = df2.groupby('startTime')['speakerTag'].agg('max').reset_index()

    # Join speakerTags
    df = df.merge(df2[['startTime', 'speakerTag']], left_on='startTime', right_on='startTime').drop(columns=['words', 'confidence'])

    # Add show and episode ids
    df['show'] = "show_" + filepath.split("show_")[1].split("/")[0]
    df['episode'] = filepath.split("show_")[1].split("/")[1].split(".")[0]
    return df

def parse_transcript(filepath, file=None, filename=None):
    if filepath:
        root = str(pathlib.Path().absolute()).split("notebooks")[0]
        rootpath = root + filepath
        for path in filepath, rootpath, file:
            try:                                                           
                with open(path) as data_file:    
                    data = json.load(data_file)
                    break
            except Exception as e:
                print(e)
                continue
    else:
        data = json.load(file)
        filepath = filename
    df = pd.json_normalize(data['results'], 'alternatives').dropna(subset=['transcript', 'words']).drop(columns=['confidence', 'words'])
    df = pd.DataFrame([' '.join(df['transcript'].to_list())], columns=['transcript'])
    df['show'] = "show_" + filepath.split("show_")[1].split("/")[0]
    df['episode'] = filepath.split("show_")[1].split("/")[1].split(".")[0]

    return df

def join_metadata(df):
    path = directory + metadatafile
    metadatadf = pd.read_csv(path, sep='\t')
    transcript_meta_df = df.merge(metadatadf, how='inner', left_on=['show', 'episode'], right_on=['show_filename_prefix', 'episode_filename_prefix'])
    
    return transcript_meta_df

def concat_and_upload(dflist, sourcefile, fileid):
    transcriptdf = pd.concat(dflist, axis=0)
    if parse_mode == 'timestamps':
        filetype = 'transcript_timestamps'
    else:
        transcriptdf = join_metadata(transcriptdf)
        filetype = 'transcripts'
    transcriptdf['source_file'] = sourcefile
    s3filename = sourcefile.split(sep='.tar')[0] + '-' + str(fileid)
    if local_mode:
        transcriptdf.to_csv(f'notebooks/csv/{filetype}-{s3filename}.csv') 
    else:
        write_to_s3(transcriptdf, s3filename, filetype)
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.info(f'Started processing tarfile. Local mode {local_mode}')
    tar = tarfile.open(directory + tarfiles[0])

    df_list = []
    tar_member = tar.next()
    file_id = 1
    while tar_member:
        file = tar.extractfile(tar_member)
        if file and tar_member.name.split(sep='.')[-1] == 'json':
            filename = tar_member.name
            if parse_mode == 'timestamps' and file_id > 23:
                transcriptdf = parse_times_and_speakers(filepath=None, file=file, filename=filename)
            else:
                transcriptdf = pd.DataFrame({'A' : []})
                # transcriptdf = parse_transcript(filepath=None, file=file, filename=filename)
            df_list.append(transcriptdf)
        if len(df_list) == 1000:
            if file_id > 23:
                logging.info(f'Uploading csv-file nr. {file_id}')
                concat_and_upload(df_list, tarfiles[0], file_id)
            else:
                logging.info(f'Skipped upload for csv-file nr. {file_id}')
            df_list = []
            file_id += 1
        tar_member = tar.next()    
    tar.close()
    logging.info(f'Uploading last csv-file nr. {file_id}')
    concat_and_upload(df_list, tarfiles[0], file_id)