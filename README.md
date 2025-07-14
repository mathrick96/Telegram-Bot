# LangBot : A Language Learning Telegram Bot


This project is about writing a telegram bot that every day produces a short story in a target language chose by the user. 

## What I want this bot to do 

- Give a welcome message when the user opens the bot on Telegram
- Have settings to choose the language, level and hour for the test to be sent
- Remember the user choices
- Have settings for a full, word for word translation 
- Have a setting to build a vocabulary list and save it as a CSV file (advanced feature)

I will need to:
* interact with the *Telegram API*
* interact with the *OpenAI API* 
* build a small database to save user data 
* deploy this to the cloud
* schedule the API call at the time the user wants
* do some prompt engineering to rotate the topic of the short story as much as possible
