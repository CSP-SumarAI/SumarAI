import json
import sys
import os
import pathlib
import pandas as pd
import awswrangler as wr
import boto3
import tarfile
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

bucket = os.getenv('S3_BUCKET')
region = os.getenv('REGION')
localmode = os.getenv('LOCAL_MODE', False)

root = str(pathlib.Path().absolute()).split("notebooks")[0]
directory = root + '/podcasts-no-audio-13GB/'
metadatafile = 'metadata.tsv'
tarfiles = ['podcasts-transcripts-0to2.tar.gz', 'podcasts-transcripts-3to5.tar.gz', 'podcasts-transcripts-6to7.tar.gz']

my_session = boto3.Session(region_name=region, profile_name='my-dev-profile')

def write_to_s3(df, filename, filetype=None):
    filetype = 'transcripts'
    path1 = f"s3://{bucket}/{filetype}/{filename}.csv"

    wr.s3.to_csv(df, path1, index=False, boto3_session=my_session)
    

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
    transcriptdf = join_metadata(transcriptdf)
    transcriptdf['source_file'] = sourcefile
    if localmode:
        transcriptdf.to_csv('notebooks/csv/testfile.csv') 
    else:
        s3filename = sourcefile.split(sep='.tar')[0] + '-' + str(fileid)
        write_to_s3(transcriptdf, s3filename)
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.info('Started processing tarfile')
    tar = tarfile.open(directory + tarfiles[0])

    df_list = []
    tar_member = tar.next()
    file_id = 1
    while tar_member:
        file = tar.extractfile(tar_member)
        if file and tar_member.name.split(sep='.')[-1] == 'json':
            filename = tar_member.name
            transcriptdf = parse_transcript(filepath=None, file=file, filename=filename)
            df_list.append(transcriptdf)
        if len(df_list) == 1000:
            logging.info(f'Uploading csv-file nr. {file_id}')
            concat_and_upload(df_list, tarfiles[0], file_id)
            df_list = []
            file_id += 1
        tar_member = tar.next()    
    tar.close()
    logging.info(f'Uploading last csv-file nr. {file_id}')
    concat_and_upload(df_list, tarfiles[0], file_id)