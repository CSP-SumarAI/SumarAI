from deep_translator import GoogleTranslator

def translator_text(text, lang):
    translated = GoogleTranslator(source='auto', target=lang).translate(text=text)
    return translated
     