import streamlit as st
import time
import sys
import os
st.set_page_config(
   page_title="SumarAI"
)
sys.path.insert(0, os.path.abspath("../src/"))
from summary import summarize
from translate import translate_transcript
from db.main import query
from google_translate import translator_text

if "prompt" not in st.session_state:
    st.session_state.prompt = None
    st.session_state.db_result = None
    st.session_state.options = None
    st.session_state.selected_option = None
    st.session_state.summary = None
    st.session_state.metadata = None
    st.session_state.prompt1 = None
    st.session_state.translated = None

st.title("SumarAI")


def chat(person, msg):
    with st.empty():
        with st.chat_message(person):
            st.write(msg)

chat("assistant", "Hello! Please enter a query")
if st.session_state.prompt == None:
    container = st.empty()
    st.session_state.prompt = container.chat_input("query")
    if st.session_state.prompt:
        container.empty()
if st.session_state.prompt:
    chat("user", st.session_state.prompt)
    chat("assistant", "what is your preferred language?(e.g. French, Finnish).If you do not wish to translate, type No")
    if st.session_state.prompt1 == None:
        container1 = st.empty()
        st.session_state.prompt1 = container1.chat_input("language")
        if st.session_state.prompt1:
            container1.empty() 

if st.session_state.prompt1 is not None:
    chat("user", st.session_state.prompt1)
    chat("assistant", "Thank you, please stand by for a moment")
    if st.session_state.db_result is None:
            st.session_state.db_result = query(st.session_state.prompt)

if st.session_state.db_result:
    with st.chat_message("assistant"):
        st.write("Here are the best options: ")

        if st.session_state.options is None:
            options = []
            for i in range(min(3, len(st.session_state.db_result["ids"][0]))):
                metadata = st.session_state.db_result["metadatas"][0][i]
                options.append(f"{metadata['show_name']} - {metadata['episode_name']}")

            st.session_state.options = options 
            
        for k, option in enumerate(st.session_state.options):
            if st.button(option,key=f"button_{k}"):
                if st.session_state.selected_option is None:
                    st.session_state.selected_option = k

if st.session_state.selected_option is not None:
    #chat("assistant", "Selected " + st.session_state.options[st.session_state.selected_option])
    metadata_selected = st.session_state.db_result["metadatas"][0][st.session_state.selected_option]
    transcript_selected = st.session_state.db_result["documents"][0][st.session_state.selected_option]
    if st.session_state.summary is None:
        with st.spinner("Summarizing..."):
            st.session_state.summary = summarize(transcript_selected[0:6000])

# if st.session_state.summary is not None:
#     with st.chat_message("assistant"):
#         st.write("Here is it's summary: ")
#         st.write(f"{metadata_selected['show_name']} - {metadata_selected['episode_name']}")
#         st.write(st.session_state.summary["choices"][0]["message"]["content"])
    
    
if st.session_state.summary is not None:
    # chat("assistant", "what is your preferred language?(e.g. French, Finnish).If you do not wish to translate, type No")
    # if st.session_state.prompt1 == None:
    #     container1 = st.empty()
    #     st.session_state.prompt1 = container1.chat_input()
    #     if st.session_state.prompt1:
    #         container1.empty()  

    if st.session_state.prompt1 == "No":
         
        with st.chat_message("assistant"):
            st.write(f"Summary: ")
            st.write(f"{metadata_selected['show_name']} - {metadata_selected['episode_name']}")
            st.write(st.session_state.summary["choices"][0]["message"]["content"])

    if st.session_state.prompt1 != "No":
        
        summary_selected = st.session_state.summary["choices"][0]["message"]["content"]
        chat("assistant", "Thank you, please stand by for a moment for the translation")
        with st.spinner("Translating..."):
            metadata_translated = f"{metadata_selected['show_name']}{metadata_selected['episode_name']}" 
            st.session_state.metadata = translate_transcript(metadata_translated, st.session_state.prompt1)
            #st.session_state.translated = translate_transcript(summary_selected,st.session_state.prompt1)
            language = st.session_state.prompt1
            st.session_state.translated = translator_text(summary_selected,language)

if st.session_state.translated is not None:
    with st.chat_message("assistant"):
        st.write(f"Here is it's summary in {st.session_state.prompt1}: ")
        #st.write(f"{metadata_selected['show_name']} - {metadata_selected['episode_name']}")
        st.write(st.session_state.metadata["choices"][0]["message"]["content"])
        #st.write(st.session_state.translated["choices"][0]["message"]["content"])
        st.write(st.session_state.translated)






#pip install -r requirements.txt
#PYTHONPATH=src streamlit run src/web/main.py