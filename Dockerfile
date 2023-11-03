# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /sumarai

# Copy the current directory contents into the container at /app
COPY src /sumarai/src
# COPY Pipfile ./Pipfile
# COPY Pipfile.lock ./Pipfile.lock
COPY requirements.txt ./requirements.txt
COPY .env ./.env

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt
#RUN pip install pipenv
#RUN pipenv run pip freeze > requirements.txt
#RUN pip install -r requirements.txt

# The app listens at port 8080
# EXPOSE 8080

# Run embed_and_ingest as module when the container launches
CMD python -m src.db.embed_and_ingest
# CMD ["python", "-m src.db.embed_and_ingest"]
