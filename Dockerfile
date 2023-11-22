FROM python:3.10-slim

WORKDIR /sumarai

COPY src /sumarai/src
COPY sumarai.py ./sumarai.py
COPY requirements.txt ./requirements.txt
COPY .env ./.env

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        netbase \
        && rm -rf /var/lib/apt/lists/*

RUN pip3 install -r requirements.txt

EXPOSE 8501

# COPY . .

ENTRYPOINT ["streamlit", "run"]

CMD ["sumarai.py"]