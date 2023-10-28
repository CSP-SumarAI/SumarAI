import streamlit as st

if "prompt" not in st.session_state:
    st.session_state.prompt = None
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
    st.session_state.options = ["Podcast 1", "Podcast 2", "Podcast 3"]

if st.session_state.options:
    with st.chat_message("assistant"):
        st.write("Here are your options: ")
        for k,option in enumerate(st.session_state.options):
            disabled = st.session_state.selected_option != None and k != st.session_state.selected_option
            if st.button(option, disabled=disabled):
                if st.session_state.selected_option == None:
                    st.session_state.selected_option = k 

if st.session_state.selected_option != None:
    chat("assistant", "Selected " + st.session_state.options[st.session_state.selected_option])
