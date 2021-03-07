import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from translate import Translator

games = pd.DataFrame()

def __read_dataset__():
    global games
    if games.empty:
        games = pd.read_excel('C:/sap_chatbot/chatbot-webhook/static/games.xlsx')

def find_game(income_game):
    __read_dataset__()

    # translating game`s name if it was given in Russian
    translator = Translator(from_lang='ru', to_lang='en')
    game = translator.translate(str(income_game))

    names = np.array(games['name']) # an array containing only game names
    max_coincidence = -1.0
    max_index = -1 # a number of games in dataset
    for i in range(len(names)):
        try:
            # if income game name is met in orginal game name
            # example: 'witcher' vs 'The Witcher® 3: Wild Hunt'
            try:
                if names[i].lower().find(game.lower()) != -1: 
                    max_index = i
                    break
            except AttributeError:
                pass

            # probability of word coincidence
            tmp = SequenceMatcher(lambda x: x==" ", game, names[i]).ratio()
            if tmp > max_coincidence:
                max_coincidence = tmp
                max_index = i
        except TypeError:
            pass

    return games.iloc[max_index]
