import json, random
from dotenv import load_dotenv
import os, openai
from openai import OpenAI
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent 
ROOT_DIR = BASE_DIR.parent
CONFIG_PATH = BASE_DIR / "config.json"

load_dotenv()  # reads your .env into os.environ
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

with open(CONFIG_PATH, 'r', encoding="utf-8") as f:
    _cfg = json.load(f)

def _random_topic():
    return random.choice(_cfg['topics'])





def generate_text(language, level):
    '''
    This function will take language, level and topic (all saved as a list in prefs) from the user input and will query the chatgpt api with that input
    It will return a string with the output of the query and maybe a number of tokens so we can keep track of the total expense
    '''
    topic = _random_topic()

    response = client.responses.create(
    model="gpt-5-mini",
    instructions='You are a language-learning assistant. Your task is to generate a medium-length text in a specified target language, at a given CEFR level, on a given topic.  ' \
    '1. Role: You are an expert at adapting texts to CEFR levels.  ' \
    '2. Instructions: Write a text (about 150–200 words) in the requested language, using vocabulary and structures appropriate to the specified CEFR level.  ' \
    '3. Vocabulary level: Use mostly words and grammar aligned with that level. Sprinkle in 3–5 slightly more advanced words or idioms (e.g. one level above) to stretch the learner.  ' \
    '4. Context: Provide the topic so the text is focused. Keep an informal tone unless specified by the user. ' \
    '5. Output only the text, nothing else: no explanations, no filler words, no list of vocabulary at the end',


    input=f"Generate a text in {language} at level {level} about {topic}"
)
    
    print(f"Here is a text in {level} level {language} about {topic}:")
    return response.output_text

    
    
    
    #print(json.dumps(response.model_dump(), indent=2))

