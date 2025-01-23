import os
from googletrans import Translator
from gtts import gTTS # type: ignore
import genanki

# Инициализация переводчика
translator = Translator()

# Создаём глобальную колоду
my_deck = genanki.Deck(
    2059400110,  # ID колоды
    'English-Russian Deck'  # Название колоды
)

# Создаём модель карточек
my_model = genanki.Model(
    1607392319,  # ID модели
    'Basic Model',
    fields=[
        {'name': 'Front'},  # Русский текст
        {'name': 'Back'},   # Английский текст с озвучкой
    ],
    templates=[
        {
            'name': 'Card 1',
            'qfmt': '{{Front}}',  # Лицевая сторона
            'afmt': '{{Back}}',   # Обратная сторона
        }
    ]
)

# Создаём папку для mp3, если её нет
AUDIO_FOLDER = 'C:/ANKI_TESTS/mp3'
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Инициализация списка для аудиофайлов
audio_files = []

# Функция перевода текста
def translate_text(text, lang='ru'):
    translation = translator.translate(text, dest=lang)  # Синхронный вызов
    return translation.text

# Функция озвучивания текста с использованием gTTS
def text_to_speech(text, filename="output.mp3"):
    tts = gTTS(text, lang="en")
    tts.save(filename)

# Функция добавления карточки в колоду
def create_anki_card(russian_text, english_text, audio_file):
    # Убираем ненужные символы
    russian_text = russian_text.rstrip('.').replace("\n", " ").replace("\r", "")
    english_text = english_text.rstrip('.').replace("\n", " ").replace("\r", "")
    audio_file = audio_file.replace("\n", " ").replace("\r", "")
    
    # Формируем поле Back с текстом и ссылкой на аудио
    back_field = f"{english_text} [sound:{audio_file}]"
    
    # Создаём карточку
    my_note = genanki.Note(
        model=my_model,
        fields=[russian_text, back_field]  # Лицевая и обратная стороны
    )
    
    # Добавляем карточку в глобальную колоду
    my_deck.add_note(my_note)

# Чтение предложений из файла
def read_sentences_from_file(filename='C:/ANKI_TESTS/words.txt'):
    with open(filename, 'r', encoding='utf-8') as file:
        sentences = [line.strip() for line in file.readlines()]
    return sentences

# Обработка предложений
def process_sentences():
    sentences = read_sentences_from_file()
    for sentence in sentences:
        translation = translate_text(sentence)
        print(f"Перевод: {translation}")
        
        # Генерация имени файла для аудио
        audio_filename = os.path.join(AUDIO_FOLDER, f"{sentence}.mp3".replace(" ", "_"))
        
        # Озвучиваем английский текст
        text_to_speech(sentence, filename=audio_filename)
        
        # Сохраняем путь аудиофайла для добавления в пакет
        audio_files.append(audio_filename)
        
        # Создаём карточку с русским переводом, английским текстом и аудио
        create_anki_card(translation, sentence, os.path.basename(audio_filename))

# Запуск обработки предложений
process_sentences()

# Сохраняем колоду в файл .apkg, включая аудиофайлы
genanki.Package(my_deck, media_files=audio_files).write_to_file('C:/ANKI_TESTS/output.apkg')
