import json, random

with open('topics.json', 'r', encoding="utf-8") as f:
    _TOPICS = json.load(f)

def _random_topic():
    return random.choice(_TOPICS)


def generate_text(language, level):
    '''
    This function will take language, level and topic (all saved as a list in prefs) from the user input and will query the chatgpt api with that input
    It will return a string with the output of the query and maybe a number of tokens so we can keep track of the total expense
    '''
    topic = _random_topic()
    return f"[stub] generate a text in {language} at level {level} about {topic}"

print(generate_text('thai', 'A2'))
