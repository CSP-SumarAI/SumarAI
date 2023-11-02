import openai

def summarize(text):
    api_key = "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"
    openai.api_key = api_key

    user_message_content = text

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
            "role": "system",
            "content": "You will be provided with transcript of podcast show, and your task is to summarize the transcript as follows:\n\n-elaborate summary of transcript\n-Name of the show"
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