import streamlit as st
st.set_page_config(
   page_title="SumarAI"
)

from summary import summarize
from db.local import query


if "prompt" not in st.session_state:
    st.session_state.prompt = None
    st.session_state.db_result = None
    st.session_state.options = None
    st.session_state.selected_option = None


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
    st.session_state.db_result = query(st.session_state.prompt)


if st.session_state.db_result:
    with st.chat_message("assistant"):
        st.write("Here is the best options: ")
        metadata = st.session_state.db_result["metadatas"][0][0]
        metadata1 = st.session_state.db_result["metadatas"][0][1]
        metadata2 = st.session_state.db_result["metadatas"][0][2]

        if st.session_state.options is None:
            st.session_state.options = [ f"{metadata['show_name']}", f"{metadata1['show_name']}", f"{metadata2['show_name']}"]
        
        for k, option in enumerate(st.session_state.options):
            disabled = st.session_state.selected_option is not None and k != st.session_state.selected_option
            if st.button(option,key=f"button_{k}", disabled=disabled):
                if st.session_state.selected_option is None:
                    st.session_state.selected_option = k
                    st.rerun()

if st.session_state.selected_option is not None:
    #chat("assistant", "Selected " + st.session_state.options[st.session_state.selected_option])
    st.session_state.db_result = query(st.session_state.options[st.session_state.selected_option])
    r = st.session_state.options[st.session_state.selected_option]
    if st.session_state.db_result:
        with st.chat_message("assistant"):
            metadata_selected = st.session_state.db_result["metadatas"][0][0]
            st.write("Summarizing the selected " + st.session_state.options[st.session_state.selected_option])
            summary = summarize(r)
            st.write("Here is it's summary: ")
            st.write(f"{metadata_selected['show_name']} - {metadata_selected['episode_name']}")
            st.write(summary["choices"][0]["message"]["content"])
       