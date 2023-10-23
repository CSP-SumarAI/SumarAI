import json
import sys
import os
import pathlib
import pandas as pd
import awswrangler as wr
import boto3
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

bucket = os.getenv('S3_BUCKET')
region = os.getenv('REGION')

root = str(pathlib.Path().absolute()).split("notebooks")[0]
path = root + 'notebooks/csv/transcripts-0[0-9].csv'

my_session = boto3.Session(region_name=region, profile_name='my-dev-profile')

def write_to_s3(df, filename, filetype):
    path1 = f"s3://{bucket}/{filetype}/{filename}.csv"

    wr.s3.to_csv(df, path1, index=False, boto3_session=my_session)
    
df = pd.read_csv(path, index_col=0)

def parse_times_and_speakers(filepath):
    root = str(pathlib.Path().absolute()).split("notebooks")[0]
    rootpath = root + filepath
    for path in filepath, rootpath:
        try:                                                           
            with open(path) as data_file:    
                data = json.load(data_file)
                break
        except Exception as e:
            continue
    else:                                               
        raise Exception
    
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

def parse_transcript(filepath):
    root = str(pathlib.Path().absolute()).split("notebooks")[0]
    rootpath = root + filepath
    for path in filepath, rootpath:
        try:                                                           
            with open(path) as data_file:    
                data = json.load(data_file)
                break
        except Exception as e:
            continue
    else:                                               
        raise Exception
    df = pd.json_normalize(data['results'], 'alternatives').dropna(subset=['transcript', 'words']).drop(columns=['confidence', 'words'])
    df = pd.DataFrame([' '.join(df['transcript'].to_list())], columns=['transcript'])
    df['show'] = "show_" + filepath.split("show_")[1].split("/")[0]
    df['episode'] = filepath.split("show_")[1].split("/")[1].split(".")[0]

    return df

def main():
    directory = str(pathlib.Path().absolute()).split("notebooks")[0] \
                + 'podcasts-no-audio-13GB/spotify-podcasts-2020/podcasts-transcripts/0'

    dir = os.listdir(directory)
    dir.sort()
    dir = dir[:11]

    dflist = []
    i = 0
    for subdir in dir:
        subdirpath = os.path.join(directory, subdir)
        if os.path.isdir(subdirpath):
            print(subdir)
            for showdir in os.listdir(subdirpath):
                filepath = os.path.join(subdirpath, showdir)
                if os.path.isdir(filepath):
                    for filename in os.listdir(filepath):
                        f = os.path.join(filepath, filename)
                        # checking if it is a file
                        if os.path.isfile(f):
                            dflist.append(parse_transcript(f))
                            i += 1
                            #if i%10 == 0:
                            #    print(i)
                                
    transcriptdf = pd.concat(dflist, axis=0)

if __name__ == "__main__":
    main()
