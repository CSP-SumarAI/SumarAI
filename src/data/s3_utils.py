import awswrangler as wr
import os
import pathlib
import pandas as pd
import boto3
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

bucket = os.getenv('S3_BUCKET')
region = os.getenv('REGION')
aws_profile = os.getenv('AWS_PROFILE')

if os.getenv('LOCAL_MODE', False):
    my_session = boto3.Session(region_name=region, profile_name=aws_profile)
else:
    my_session = None

def read_from_s3(filename, filetype=None):
    if filetype == None:
        filetype = 'transcripts'
    path1 = f"s3://{bucket}/{filetype}/{filename}"

    df = wr.s3.read_csv(path=path1, boto3_session=my_session)

    return df

def write_to_s3(df, filename, filetype=None):
    if filetype == None:
        filetype = 'transcripts'
    path1 = f"s3://{bucket}/{filetype}/{filename}.csv"

    wr.s3.to_csv(df, path1, index=False, boto3_session=my_session)