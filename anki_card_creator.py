import os
import re
import shutil
from gtts import gTTS  # type: ignore
import genanki
from googletrans import Translator

translator = Translator()
deckName = 'Words pack'

# Function to delete the MP3 folder and the old Anki .apkg file if they exist
def clean_up():
    # Remove the old MP3 folder and its contents
    if os.path.exists(AUDIO_FOLDER):
        shutil.rmtree(AUDIO_FOLDER)
    
    # Remove the previous .apkg file if it exists
    if os.path.exists('C:/ANKI_TESTS/output.apkg'):
        os.remove('C:/ANKI_TESTS/output.apkg')

# Function to translate text
def translate_text(text, lang='ru'):
    # Find words enclosed in **asterisks** (e.g., **expertise)
    bold_words = re.findall(r'\*\*(.*?)\*\*', text)
    
    # Remove the **asterisks** from the text for translation
    text_without_bold = re.sub(r'\*\*(.*?)\*\*', r'\1', text)

    # Translate the text without bold formatting
    translation = translator.translate(text_without_bold, dest=lang).text
    
    # Reapply bold formatting to the translated text
    for word in bold_words:
        translated_word = translator.translate(word, dest=lang).text
        # Add <b> tags to the translated words
        translation = re.sub(rf'\b{translated_word}\b', f'<b>{translated_word}</b>', translation, flags=re.IGNORECASE)
    
    # Also apply the bold to the original English text
    text_bolded = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    return translation, text_bolded


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
    # Replace invalid characters for Windows file system
    sanitized_text = re.sub(r'[<>:"/\\|?*]', '_', text)
    
    # Replace multiple underscores and consecutive dots with a single one
    sanitized_text = re.sub(r'_+', '_', sanitized_text)  # Replace multiple underscores with one
    sanitized_text = re.sub(r'\.+', '.', sanitized_text)  # Replace consecutive dots with a single dot
    
    # Make sure the file doesn't end with a dot (Windows doesn't allow this)
    if sanitized_text.endswith('.'):
        sanitized_text = sanitized_text[:-1]

    return sanitized_text


# Function to process sentences and generate Anki cards
def process_sentences():
    sentences = read_sentences_from_file()
    for sentence in sentences:
        translation, sentence_bolded = translate_text(sentence)
        if translation:
            print(f"Translation: {translation}")
            
            # Generate the filename for the audio
            audio_filename = os.path.join(AUDIO_FOLDER, f"{sanitize_filename(sentence)}.mp3".replace(" ", "_"))
            
            # Convert the English text to speech
            text_to_speech(sentence, filename=audio_filename)
            
            # Save the audio file path for the package
            audio_files.append(audio_filename)
            
            # Create the Anki card with the Russian translation, English text, and audio
            create_anki_card(translation, sentence_bolded, os.path.basename(audio_filename))
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
    deckName  # Deck name
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

# Clean up the previous files before starting
clean_up()

os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Initialize the list to store audio files
audio_files = []

# Run the sentence processing
process_sentences()

# Save the deck to a .apkg file including the media files
genanki.Package(my_deck, media_files=audio_files).write_to_file('C:/ANKI_TESTS/output.apkg')