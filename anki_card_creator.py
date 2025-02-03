import os
import re
from gtts import gTTS  # type: ignore
import genanki
from googletrans import Translator

translator = Translator()

# Function to translate text
def translate_text(text, lang='ru'):
    translation = translator.translate(text, dest=lang)  # Sync
    return translation.text

# Function for text-to-speech conversion using gTTS
def text_to_speech(text, filename="output.mp3"):
    tts = gTTS(text, lang="en")
    tts.save(filename)

# Function to create an Anki card
def create_anki_card(russian_text, english_text, audio_file):
    # Remove unnecessary symbols
    russian_text = russian_text.rstrip('.').replace("\n", " ").replace("\r", "")
    english_text = english_text.rstrip('.').replace("\n", " ").replace("\r", "")
    audio_file = audio_file.replace("\n", " ").replace("\r", "")
    
    # Format the Back field with text and audio link
    back_field = f"{english_text} [sound:{audio_file}]"
    
    # Create a note
    my_note = genanki.Note(
        model=my_model,
        fields=[russian_text, back_field]  # Front and back fields
    )
    
    # Add the note to the global deck
    my_deck.add_note(my_note)

# Function to sanitize file names
def sanitize_filename(text):
    # Remove invalid characters for Windows
    return re.sub(r'[<>:"/\\|?*]', '_', text)

# Function to process sentences and generate Anki cards
def process_sentences():
    sentences = read_sentences_from_file()
    for sentence in sentences:
        translation = translate_text(sentence)
        if translation:
            print(f"Translation: {translation}")
            
            # Generate the filename for the audio
            audio_filename = os.path.join(AUDIO_FOLDER, f"{sanitize_filename(sentence)}.mp3".replace(" ", "_"))
            
            # Convert the English text to speech
            text_to_speech(sentence, filename=audio_filename)
            
            # Save the audio file path for the package
            audio_files.append(audio_filename)
            
            # Create the Anki card with the Russian translation, English text, and audio
            create_anki_card(translation, sentence, os.path.basename(audio_filename))
        else:
            print(f"Failed to translate: {sentence}")
            continue  # Skip current iteration if translation failed

# Function to read sentences from a file
def read_sentences_from_file(filename='C:/ANKI_TESTS/words.txt'):
    with open(filename, 'r', encoding='utf-8') as file:
        sentences = [line.strip() for line in file.readlines()]
    return sentences

# Initialize the global deck
my_deck = genanki.Deck(
    2059400110,  # Deck ID
    'INVERSION'  # Deck name
)

# Create the Anki card model
my_model = genanki.Model(
    1607392319,  # Model ID
    'Basic',
    fields=[
        {'name': 'Front'},  # Russian text
        {'name': 'Back'},   # English text with audio
    ],
    templates=[
        {
            'name': 'Card 1',
            'qfmt': '{{Front}}',  # Front side
            'afmt': '{{Back}}',   # Back side
        }
    ]
)

# Create the folder for mp3 files if it doesn't exist
AUDIO_FOLDER = 'C:/ANKI_TESTS/mp3'
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Initialize the list to store audio files
audio_files = []

# Run the sentence processing
process_sentences()

# Save the deck to a .apkg file including the media files
genanki.Package(my_deck, media_files=audio_files).write_to_file('C:/ANKI_TESTS/output.apkg')