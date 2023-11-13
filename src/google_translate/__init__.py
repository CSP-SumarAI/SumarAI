from google_trans_new import google_translator
import streamlit as st
from util import timeit

@timeit

def translator_text(text, lang):
    translator = google_translator()
    translate = translator.translate(text, lang_tgt=lang)
    print(text)
    print(lang)
    print(translate)
    return translate