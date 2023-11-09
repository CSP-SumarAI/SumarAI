import streamlit as st
import time
st.set_page_config(
   page_title="SumarAI"
)

from summary import summarize
from translate import translate_transcript
from db.main import query


if "prompt" not in st.session_state:
    st.session_state.prompt = None
    st.session_state.prompt1 = None
    st.session_state.db_result = None
    st.session_state.options = None
    st.session_state.selected_option = None
    st.session_state.summary = None
    st.session_state.translated = None
    st.session_state.metadata = None

st.title("SumarAI")


def chat(person, msg):
    with st.chat_message(person):
        st.write(msg)

chat("assistant", "Hello! Please enter a query")
if st.session_state.prompt == None:
    container = st.empty()
    st.session_state.prompt = container.chat_input()
    if st.session_state.prompt:
        container.empty()


if st.session_state.prompt:
    chat("user", st.session_state.prompt)
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

if st.session_state.summary is not None:
    with st.chat_message("assistant"):
        st.write("Here is it's summary: ")
        st.write(f"{metadata_selected['show_name']} - {metadata_selected['episode_name']}")
        st.write(st.session_state.summary["choices"][0]["message"]["content"])



#st.session_state.translated = None

if st.session_state.summary is not None:
    preferred_language = st.text_input("Enter your preferred language (e.g.Finnish, French, Spanish):")
    if st.button("Translate"):
        if preferred_language:
            summary_selected = st.session_state.summary["choices"][0]["message"]["content"]
            with st.spinner("Translating..."):
                st.session_state.translated = translate_transcript(summary_selected, preferred_language)
                st.write(f"Here is the summary in {preferred_language} language:")
                st.write(st.session_state.translated["choices"][0]["message"]["content"])
            
        else:
            st.write("Please enter a preferred language.")








#PYTHONPATH=src streamlit run src/web/main.py