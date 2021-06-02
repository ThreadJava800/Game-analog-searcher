import os.path

import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from translate import Translator
import ast
import pathlib
from dataclasses import dataclass
import firebase_admin
from firebase_admin import db


@dataclass
class Game:
    name: str
    developer: str
    publisher: str
    minimum: str
    recommended: str


games = pd.DataFrame()
processors = pd.DataFrame()  # processors and their benchmarks
videocards = pd.DataFrame()  # GPUs and their benchmarks
assemblies = pd.DataFrame()

FIREBASE_OBJECT = None

# used for moving games with the most popular developers to the top
priored_developers = ['Ubisoft', 'Valve', 'CD PROJEKT RED', 'Bungie', 'Electronic Arts']
priored_publishers = ['Electronic Arts']


def __read_games_dataset__() -> None:
    global games
    if games.empty:
        games = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/games.xlsx')


def __read_assembly_dataset__() -> None:
    global assemblies
    if assemblies.empty:
        assemblies = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/assemblies.xlsx')


def __read_all_datasets__() -> None:
    global games, processors, videocards, assemblies
    if games.empty:
        games = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/games.xlsx')
    if processors.empty:
        processors = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/proccessors.xlsx')
    if videocards.empty:
        videocards = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/videocards.xlsx')
    if assemblies.empty:
        assemblies = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/assemblies.xlsx')


def get_assembly(game_name, given_graphics):
    __read_all_datasets__()

    # getting needed graphics
    graphics = None
    if given_graphics.find('высок') != -1:
        graphics = 'win_recommended'
    elif given_graphics.find('низк') != -1:
        graphics = 'win_minimum'
    else:
        # TODO: add other cases
        raise ValueError()

    # TODO: make a check on games with similar names
    game = games.iloc[list(games['name']).index(game_name)]
    processor_names, videocard_names = list(processors['name']), list(videocards['Name'])
    max_coincidence = -1.0
    max_index = -1
    for i in range(len(processor_names)):
        # if we found processor name in game requirements string
        if ast.literal_eval(game[graphics])['processor'].lower().find(processor_names[i].lower()) != -1:
            max_coincidence = 1.0
            max_index = i
            break

        # getting percentage of coincidence
        tmp = SequenceMatcher(lambda x: x == " ", ast.literal_eval(game[graphics])['processor'].lower(),
                              processor_names[i].lower()).ratio()
        if max_coincidence < tmp:
            max_index = i
            max_coincidence = tmp
    ideal_processor = processor_names[max_index]

    max_coincidence = -1.0
    max_index = -1
    for i in range(len(videocard_names)):
        # if we found videocard name in game requirements string
        if ast.literal_eval(game[graphics])['graphics'].lower().find(videocard_names[i].lower()) != -1:
            max_coincidence = 1.0
            max_index = i
            break

        # getting percentage of coincidence
        tmp = SequenceMatcher(lambda x: x == " ", ast.literal_eval(game[graphics])['graphics'].lower(),
                              videocard_names[i].lower()).ratio()
        if max_coincidence < tmp:
            max_index = i
            max_coincidence = tmp
    ideal_videocard = videocard_names[max_index]

    # getting benchmark of assembly asked in the requirements
    ideal_assembly_rating = float(videocards.iloc[list(videocards['Name']).index(ideal_videocard)]['Rating']) + float(
        processors.iloc[list(processors['name']).index(ideal_processor)]['rating'])

    # getting assembly (available at the shop) closest ideal one
    min_difference = max(list(assemblies['rating']))
    ans_assembly_index = -1
    for i in range(len(assemblies)):
        if 0 <= (assemblies.iloc[i]['rating'] - ideal_assembly_rating) < min_difference \
                and videocards.iloc[list(videocards['Name']).index(assemblies.iloc[i]['graphics'])]['Rating'] > \
                videocards.iloc[list(videocards['Name']).index(ideal_videocard)]['Rating'] \
                and processors.iloc[list(processors['name']).index(assemblies.iloc[i]['processor'])]['rating'] > \
                processors.iloc[list(processors['name']).index(ideal_processor)]['rating']:
            min_difference = assemblies.iloc[i]['rating'] - ideal_assembly_rating
            ans_assembly_index = i

    return assemblies.iloc[ans_assembly_index]


def game_analog_searcher(income_game) -> list:
    """
    Returns games with similar name and their requirements
    """

    __read_games_dataset__()

    # translating game`s name if it was given in Russian
    # translating cyrillics to latin works worse, trust me)
    translator = Translator(from_lang='ru', to_lang='en')
    game = translator.translate(str(income_game))

    names = np.array(games['name'])  # an array containing only game names
    indexes = dict()  # a dict containing game name and its coincidence to a given one
    for i in range(len(names)):
        indexes[i] = -1.0
    for i in range(len(names)):
        try:
            try:
                # if game was given right like in steam
                if names[i].lower().find(game.lower()) != -1:
                    indexes[i] = 1.0
                    continue
            except AttributeError:
                pass

            # getting percentage of coincidence
            tmp = SequenceMatcher(lambda x: x == " ", game, names[i]).ratio()
            indexes[i] = tmp
        except TypeError:
            pass

    # sorting dictionary by coincidence value
    indexes = dict(sorted(indexes.items(), key=lambda item: item[1]))

    # slicing 50 first games with max coincidence to a given game
    feedback_list = list(indexes.keys())[-50::]
    tempa = list(indexes.items())[-50::]
    suggested_games = list()
    for i in feedback_list:
        tmp = Game(str(games.iloc[i]['name']), str(games.iloc[i]['developer']), str(games.iloc[i]['publisher']),
                   str(games.iloc[i]['win_minimum']), str(games.iloc[i]['win_recommended']))
        if tmp not in suggested_games:
            suggested_games.append(tmp)

    # if game with priored developer was found then move it to the top
    for i in range(len(suggested_games)):
        if suggested_games[i].developer in priored_developers or suggested_games[i].publisher in priored_publishers:
            suggested_games[i], suggested_games[-1] = suggested_games[-1], suggested_games[i]

    game_names = list()
    for val in suggested_games:
        game_names.append(val.name)

    # do not return a slice with more than 10 values!!!
    return game_names[-8::]


def init_firebase() -> None:
    global FIREBASE_OBJECT
    if FIREBASE_OBJECT is None:
        cred_object = firebase_admin.credentials.Certificate(
            os.path.join(str(pathlib.Path(__file__).parent.absolute()) + '/static/firebase_credentials.json'))
        FIREBASE_OBJECT = firebase_admin.initialize_app(cred_object, {
            'databaseURL': 'https://computershop-3bc7d-default-rtdb.europe-west1.firebasedatabase.app/'
        })


def get_last_order_id() -> int:
    max_order_id = 0
    snapshot = db.reference('').get()
    if snapshot is None:
        return 0
    for order_type in snapshot:
        if order_type == "active_orders" or order_type == "done_orders":
            for order in snapshot[order_type]:
                max_order_id = max(max_order_id, int(snapshot[order_type][order]['id']))
    return max_order_id


def get_last_pretense_id() -> int:
    max_pretense_id = 0
    snapshot = db.reference('').get()
    if snapshot is None:
        return 0
    for order_type in snapshot:
        if order_type == "active_pretenses" or order_type == "done_pretenses":
            for order in snapshot[order_type]:
                max_pretense_id = max(max_pretense_id, int(snapshot[order_type][order]['id']))
    return max_pretense_id


def get_order_by_id(order_id: int) -> dict:
    snapshot = db.reference('').get()
    if snapshot is None:
        return {}
    for order_type in snapshot:
        if order_type == "active_orders" or order_type == "done_orders":
            for order in snapshot[order_type]:
                possible_order = snapshot[order_type][order]
                if possible_order['id'] == order_id:
                    possible_order['order_type'] = order_type
                    return possible_order
    return {}


def get_pretense_by_id(pretense_id: int) -> dict:
    snapshot = db.reference('').get()
    if snapshot is None:
        return {}
    for pretense_type in snapshot:
        if pretense_type == "active_pretenses" or pretense_type == "done_pretenses":
            for pretense in snapshot[pretense_type]:
                possible_pretense = snapshot[pretense_type][pretense]
                if possible_pretense['id'] == pretense_id:
                    possible_pretense['pretense_type'] = pretense_type
                    return possible_pretense
    return {}


def get_assembly_by_name(assembly_name: str) -> dict:
    __read_assembly_dataset__()
    for i in range(len(assemblies)):
        if assemblies.iloc[i]['name'] == assembly_name:
            return dict(assemblies.iloc[i])
    return {}


def make_order(assembly: str, name: str, address: str, email: str) -> dict:
    init_firebase()
    reference = db.reference('active_orders')
    order = dict()
    order['id'] = get_last_order_id() + 1
    order['name'] = name
    order['address'] = address
    order['email'] = email
    order['assembly'] = assembly
    reference.push(order)
    return {'ID заказа': f'FFF-{order["id"]}'}


def get_order_status(order_id: str) -> dict:
    init_firebase()
    search_id = int(order_id[4::])
    order = get_order_by_id(search_id)
    user_info = dict()
    if order == {}:
        user_info['status'] = "Заказ не найден!"
        user_info['assembly'] = ""
    else:
        user_info['assembly'] = order['assembly']
        if order['order_type'] == "active_orders":
            user_info['status'] = "Выполняется"
        if order['order_type'] == "done_orders":
            user_info['status'] = "Выполнен"
    return user_info


def create_pretense(name: str, email: str, pretense_text: str) -> dict:
    init_firebase()
    reference = db.reference('active_pretenses')
    pretense = dict()
    pretense['id'] = get_last_pretense_id() + 1
    pretense['name'] = name
    pretense['email'] = email
    pretense['pretense'] = pretense_text
    reference.push(pretense)
    return {'ID претензии': f'ZZZ-{pretense["id"]}'}


def get_pretense_status(pretense_id: str) -> dict:
    init_firebase()
    search_id = int(pretense_id[4::])
    pretense = get_pretense_by_id(search_id)
    user_pretense = dict()
    if pretense == {}:
        user_pretense['status'] = "Жалоба не найдена!"
        user_pretense['pretense'] = ""
    else:
        user_pretense['pretense'] = pretense['pretense']
        if pretense['pretense_type'] == "active_pretenses":
            user_pretense['status'] = "Жалоба рассматривается. Ответ придёт вам на почту."
        if pretense['pretense_type'] == "done_pretenses":
            user_pretense['status'] = "Жалоба рассмотрена. Проверьте почту."
    return user_pretense
