import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from translate import Translator


class Game:
  def __init__(self, name: str, developer: str, minimum: str, recommended: str):
    self.name = name
    self.developer = developer
    self.minimum = minimum
    self.recommended = recommended

  def __str__(self):
    return 'Game name: ' + self.name + '\n' + 'Developer: ' + self.developer + '\n\n'


games = pd.DataFrame()
priored_developers = ['Ubisoft', 'Valve', 'CD PROJEKT RED']

def __read_dataset__():
    """
    Reads dataset on first start
    """
    global games
    if games.empty:
        games = pd.read_excel('D:/Projects/WEB/sap_chatbot/chatbot-webhook/static/games.xlsx')

def find_game(income_game):
    """
    Returns games with similar name and their requirements
    """
    __read_dataset__()

    # translating game`s name if it was given in Russian
    translator = Translator(from_lang='ru', to_lang='en')
    game = translator.translate(str(income_game))

    names = np.array(games['name']) # an array containing only game names
    indexes = dict()
    for i in range(len(names)):
        indexes[i] = -1.0
    for i in range(len(names)):
        try:
            try:
                if names[i].lower().find(game.lower()) != -1: 
                    indexes[i] = 1.0
                    continue
            except AttributeError:
                pass
            tmp = SequenceMatcher(lambda x: x==" ", game, names[i]).ratio()
            indexes[i] = tmp
        except TypeError:
            pass
    indexes = dict(sorted(indexes.items(), key=lambda item: item[1]))

    feedback_list = list(indexes.keys())[-50::]
    suggested_games = list()
    for i in feedback_list:
        tmp = Game(str(games.iloc[i]['name']), str(games.iloc[i]['developer']), str(games.iloc[i]['win_minimum']), str(games.iloc[i]['win_recommended']))
        if tmp not in suggested_games:
            suggested_games.append(tmp)
    for i in range(len(suggested_games)):
        if suggested_games[i].developer in priored_developers:
            suggested_games[i], suggested_games[-1] = suggested_games[-1], suggested_games[i]

    return suggested_games
