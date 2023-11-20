import streamlit as st
import time
import sys
import os
st.set_page_config(
   page_title="SumarAI"
)
sys.path.insert(0, os.path.abspath("../"))
from summary import summarize
from translate import translate_transcript
from db.main import query, episode_selected
from db.mainTimestamp import queryTimestamps
from google_translate import translator_text

if "prompt" not in st.session_state:
    st.session_state.prompt = None
    st.session_state.prompt1 = None
    st.session_state.prompt2 = None
    st.session_state.db_result = None
    st.session_state.options = None
    st.session_state.selected_option = None
    st.session_state.selected_option_episode = None
    st.session_state.summary = None
    st.session_state.metadata = None 
    st.session_state.translated = None
    st.session_state.episode_result = None
    st.session_state.optionsEpisode = None
    st.session_state.results = None
    st.session_state.episode = None
    st.session_state.selected_paragraph = None
    st.session_state.translated_prompt = None

st.title("SumarAI - Podcast Summarizer")


def chat(person, msg):
    with st.empty():
        with st.chat_message(person):
            st.write(msg)

chat("assistant", "Hello! Please enter a query to seach for interesting podcast episodes.")
if st.session_state.prompt == None:
    container = st.empty()
    st.session_state.prompt = container.chat_input("I'm looking for podcasts about sports.")
    if st.session_state.prompt:
        container.empty()
if st.session_state.prompt:
    chat("user", st.session_state.prompt)
    chat("assistant", "what is your preferred language?(e.g. French, Finnish).If you do not wish to translate, type 'No'")
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
            st.session_state.episode_result = episode_selected(st.session_state.db_result)

if st.session_state.db_result:
    with st.chat_message("assistant"):
        st.write("Here are the best options: ")

        if st.session_state.options is None:
            options = []
            for i in range(min(3, len(st.session_state.db_result["ids"][0]))):
                metadata = st.session_state.db_result["metadatas"][0][i]
                options.append(metadata)
                #options.append(f"{metadata['show_name']} - {metadata['episode_name']} - {metadata['episode_description']}")

            st.session_state.options = options 
           
        for k, option in enumerate(st.session_state.options):
            with st.expander(f"{option['show_name']} - {option['episode_name']}"):
                if st.button(option['episode_description'],key=f"button_{k}"):
                    if st.session_state.selected_option is None:
                        st.session_state.selected_option = k
                        st.session_state.episode = st.session_state.episode_result.loc[k, "episode_id"]

if st.session_state.selected_option is not None:
    #chat("assistant", "Selected " + st.session_state.options[st.session_state.selected_option])
    metadata_selected = st.session_state.db_result["metadatas"][0][st.session_state.selected_option]
    transcript_selected = st.session_state.db_result["documents"][0][st.session_state.selected_option]
    if st.session_state.summary is None:
        with st.spinner("Summarizing..."):
            st.session_state.summary = summarize(transcript_selected[0:6000])

    
if st.session_state.summary is not None and st.session_state.translated is None:
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

    if st.session_state.results is None:
        chat("assistant", "Do you wish to know more about a specific part of the episode? Please enter you query/topic below.")
        if st.session_state.prompt2 == None:
            container2 = st.empty()
            st.session_state.prompt2 = container2.chat_input()
            if st.session_state.prompt2:
                container2.empty()  
                chat("user", st.session_state.prompt2)
    if st.session_state.prompt2 != "No" and st.session_state.prompt2 is not None:
        episode = st.session_state.episode
        st.session_state.translated_prompt = translator_text(st.session_state.prompt2, "en")
        st.session_state.results = queryTimestamps(st.session_state.translated_prompt, episode)
        if not st.session_state.results.empty:
            if 'startTime' in st.session_state.results.columns:
                with st.chat_message("assistant"):
                    st.write("Here are timestamp details related to your query.")
                    if st.session_state.optionsEpisode is None:
                        options = []
                        for i in range(3):
                            timestamp = st.session_state.results.iloc[i]
                            #options.append(f"{timestamp['startTime']} seconds - {timestamp['endTime']} seconds")
                            #option_text = f"{timestamp['startTime']} seconds - {timestamp['endTime']} seconds"
                            options.append(timestamp)

                        for k, option in enumerate(options):
                            with st.expander(f"{option['startTime']} seconds - {option['endTime']} seconds"):
                                paragraph = translator_text(option['paragraph'], st.session_state.prompt1)
                                st.write(f"{paragraph}")                    



                        # selected_option = st.selectbox("Select a timestamp:", options)
                        # selected_index = options.index(selected_option)
                        # if selected_option:
                        #     timestamp = st.session_state.results.iloc[selected_index]
                        #     #st.write(f"You selected: {selected_option}")
                        #     #st.write(translator_text("Details of selected timestamp:", st.session_state.prompt1))
                        #     with st.expander(f"Start Time: {timestamp['startTime']} seconds - End Time: {timestamp['endTime']} seconds"):
                        #         #st.write(f"End Time: {timestamp['endTime']} seconds")
                        #         paragraph = translator_text(timestamp['paragraph'], st.session_state.prompt1)
                        #         st.write(f"Paragraph: {paragraph}")
            
            else:
                st.write("No 'startTime' column found")

        else:
            with st.chat_message("assistant"):
                st.write("Sorry, there are no available timestamps for this query")

    

        






#pip install -r requirements.txt
#PYTHONPATH=src streamlit run src/web/main.py