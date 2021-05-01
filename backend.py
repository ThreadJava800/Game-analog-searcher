import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from translate import Translator
import ast
import pathlib



class Game:
  def __init__(self, name: str, developer: str, publisher: str, minimum: str, recommended: str):
    self.name = name
    self.developer = developer
    self.publisher = publisher
    self.minimum = minimum
    self.recommended = recommended

  def __str__(self):
    return 'Game name: ' + self.name + '\n' + 'Developer: ' + self.developer + '\n\n'


games = pd.DataFrame()
processors = pd.DataFrame()
videocards = pd.DataFrame()
assemblies = pd.DataFrame()
priored_developers = ['Ubisoft', 'Valve', 'CD PROJEKT RED', 'Bungie']
priored_publishers = ['Electronic Arts']


def __read_games_dataset__():
    global games
    if games.empty:
        games = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/games.xlsx')


def __read_all_datasets__():
    global games, processors, videocards, assemblies
    if games.empty:
        games = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/games.xlsx')
    if processors.empty:
        processors = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/proccessors.xlsx')
    if videocards.empty:
        videocards = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/videocards.xlsx')
    if assemblies.empty:
        assemblies = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/assemblies.xlsx')



def find_game(game_name):
    for i in range(len(games)):
        if games.iloc[i]['name'] == game_name:
            return games.iloc[i]


def get_assembly(game_name, given_graphics):
    __read_all_datasets__()

    graphics = None
    if given_graphics.find('высок') != -1:
        graphics = 'win_recommended'
    elif given_graphics.find('низк') != -1:
        graphics = 'win_minimum'
    else:
        raise ValueError()

    game = games.iloc[list(games['name']).index(game_name)]
    processor_names, videocard_names = list(processors['name']), list(videocards['Name'])
    max_coincidence = -1.0
    max_index = -1
    for i in range(len(processor_names)):
        if ast.literal_eval(game[graphics])['processor'].lower().find(processor_names[i].lower()) != -1: 
            max_coincidence = 1.0
            max_index = i
            break
        tmp = SequenceMatcher(lambda x: x==" ", ast.literal_eval(game[graphics])['processor'].lower(), processor_names[i].lower()).ratio()
        if max_coincidence < tmp:
            max_index = i
            max_coincidence = tmp
    ideal_processor = processor_names[max_index]

    max_coincidence = -1.0
    max_index = -1
    for i in range(len(videocard_names)):
        if ast.literal_eval(game[graphics])['graphics'].lower().find(videocard_names[i].lower()) != -1: 
            max_coincidence = 1.0
            max_index = i
            break
        tmp = SequenceMatcher(lambda x: x==" ", ast.literal_eval(game[graphics])['graphics'].lower(), videocard_names[i].lower()).ratio()
        if max_coincidence < tmp:
            max_index = i
            max_coincidence = tmp
    ideal_videocard = videocard_names[max_index]
    ideal_assembly_rating = float(videocards.iloc[list(videocards['Name']).index(ideal_videocard)]['Rating']) + float(processors.iloc[list(processors['name']).index(ideal_processor)]['rating'])

    min_difference = max(list(assemblies['rating']))
    ans_assembly_index = -1
    for i in range(len(assemblies)):
        if 0 <= (assemblies.iloc[i]['rating'] - ideal_assembly_rating) < min_difference \
                and videocards.iloc[list(videocards['Name']).index(assemblies.iloc[i]['graphics'])]['Rating'] > videocards.iloc[list(videocards['Name']).index(ideal_videocard)]['Rating'] \
                and processors.iloc[list(processors['name']).index(assemblies.iloc[i]['processor'])]['rating'] > processors.iloc[list(processors['name']).index(ideal_processor)]['rating']:
            min_difference = assemblies.iloc[i]['rating'] - ideal_assembly_rating
            ans_assembly_index = i

    return assemblies.iloc[ans_assembly_index]

    

def game_analog_searcher(income_game):
    """
    Returns games with similar name and their requirements
    """
    __read_games_dataset__()

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
        tmp = Game(str(games.iloc[i]['name']), str(games.iloc[i]['developer']), str(games.iloc[i]['publisher']), str(games.iloc[i]['win_minimum']), str(games.iloc[i]['win_recommended']))
        if tmp not in suggested_games:
            suggested_games.append(tmp)
    for i in range(len(suggested_games)):
        if suggested_games[i].developer in priored_developers or suggested_games[i].publisher in priored_publishers:
            suggested_games[i], suggested_games[-1] = suggested_games[-1], suggested_games[i]
    game_names = list()
    for val in suggested_games:
        game_names.append(val.name)

    return game_names[-8::]
