import openai
import os
from util import timeit
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

api_key = os.getenv("OPEN_AI_API_KEY")

@timeit
def translate_transcript(text, lang):
    openai.api_key = api_key

    user_message_content = f"{text}"
    
    if lang != "no":
        instruction = f"You will be provided with the text, and your task is to translate the text in the {lang} language given by the user"
    else:
        instruction = "you do not need to translate"


    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
            "role": "system",
            "content": instruction
            },
            {
            "role": "user",
            "content": user_message_content
            }
        ],
        temperature=0, # Controls the randomness of the response
        max_tokens=2500,
        top_p=1, #It controls the diversity and randomness of the generated text
        frequency_penalty=0, # Adjusts the likelihood of words appearing frequently
        presence_penalty=0. # Adjusts the likelihood of model-generated content being present
    )

    return response