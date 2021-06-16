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
import transliterate
from transliterate.exceptions import LanguageDetectionError


@dataclass
class Game:
    name: str
    developer: str
    publisher: str
    minimum: str
    recommended: str


@dataclass
class Hardware:
    name: str
    type: str


games = pd.DataFrame()
processors = pd.DataFrame()  # processors and their benchmarks
videocards = pd.DataFrame()  # GPUs and their benchmarks
assemblies = pd.DataFrame()

FIREBASE_OBJECT = None

# used for moving games with the most popular developers to the top
priored_developers = ['Ubisoft', 'Valve', 'CD PROJEKT RED', 'Bungie', 'Electronic Arts']
priored_publishers = ['Electronic Arts']


def __read_games_dataset__() -> None:
    """
    Reads games dataset.

    :return: None
    """

    global games
    if games.empty:
        games = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/games.xlsx')


def __read_assembly_dataset__() -> None:
    """
    Reads assembly dataset.

    :return: None
    """

    global assemblies
    if assemblies.empty:
        assemblies = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/assemblies.xlsx')


def __read_all_datasets__() -> None:
    """
    Reads all datasets.

    :return: None
    """

    global games, processors, videocards, assemblies
    if games.empty:
        games = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/games.xlsx')
    if processors.empty:
        processors = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/proccessors.xlsx')
    if videocards.empty:
        videocards = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/videocards.xlsx')
    if assemblies.empty:
        assemblies = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/assemblies.xlsx')


def __read_hardware_datasets__() -> None:
    """
    Reads processor and GPU dataset.

    :return: None
    """

    global processors, videocards
    if processors.empty:
        processors = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/proccessors.xlsx')
    if videocards.empty:
        videocards = pd.read_excel(str(pathlib.Path(__file__).parent.absolute()) + '/static/videocards.xlsx')


def get_assembly_by_price(price):
    minimum = 10000000
    min_assembly = int()
    for i in range(len(assemblies)):
        if abs(assemblies.iloc[i]['price'] - price) < minimum:
            minimum = abs(assemblies.iloc[i]['price'] - price)
            min_assembly = i
    return assemblies.iloc[min_assembly]


def get_assembly(game_name, given_graphics, price, purpose):
    """
    Searches the most suitable dataset according to a wanted game and graphics.

    :param game_name: Game name
    :param given_graphics: Requested graphics
    :param price: Wanted price
    :param purpose: For what do you need that assembly
    :return: pandas.core.frame.DataFrame
    """

    __read_all_datasets__()

    if str(purpose).find('видеомонтаж') != -1 or str(game_name).find('видеомонтаж') != -1:
        if int(price) > 67900:
            return get_assembly_by_price(int(price))
        else:
            return assemblies.iloc[1]  # EPIX PURE
    elif str(purpose).find('браузинг') != -1 or str(purpose).find('работ') != -1 or str(game_name).find(
            'браузинг') != -1 or str(game_name).find('работ') != -1:
        if int(price) > 25990:
            return get_assembly_by_price(int(price))
        else:
            return assemblies.iloc[2]
    else:
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
        ideal_assembly_rating = float(
            videocards.iloc[list(videocards['Name']).index(ideal_videocard)]['Rating']) + float(
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

        if price - int(assemblies.iloc[ans_assembly_index]['price']) > 20000:
            return get_assembly_by_price(price)
        return assemblies.iloc[ans_assembly_index]


def search_similar_names(names: np.array, given_name: str) -> dict:
    """
    Returns a dict with names and a percentage of similarity to a :param given_name.

    :param names: Array of possible names
    :type names: np.array

    :param given_name: A given name
    :type given_name: str
    :return: dict
    """

    indexes = dict()  # a dict containing game name and its coincidence to a given one
    for i in range(len(names)):
        indexes[i] = -1.0
    for i in range(len(names)):
        try:
            try:
                # if game was given right like in steam
                if names[i].lower().find(given_name.lower()) != -1:
                    indexes[i] = 1.0
                    continue
            except AttributeError:
                pass

            # getting percentage of coincidence
            tmp = SequenceMatcher(lambda x: x == " ", given_name, names[i]).ratio()
            indexes[i] = tmp
        except TypeError:
            pass

    # sorting dictionary by coincidence value
    return dict(sorted(indexes.items(), key=lambda item: item[1]))


def game_analog_searcher(income_game) -> list:
    """
    Return names of the most similar game to a given one (see :param income_game).

    :param income_game: Given game name (free formulation)
    :return: list
    """

    __read_games_dataset__()

    # translating game`s name if it was given in Russian
    # translating cyrillics to latin works worse, trust me)
    translator = Translator(from_lang='ru', to_lang='en')
    game = translator.translate(str(income_game))

    names = np.array(games['name'])  # an array containing only game names
    indexes = search_similar_names(names, game)

    # slicing 50 first games with max coincidence to a given game
    feedback_list = list(indexes.keys())[-50::]
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


def get_hardware_data_by_name(hardware_list: pd.DataFrame, name: str) -> dict:
    """
    Returns type of hardware and possible name of it.

    :param hardware_list: Dataframe with all hardware
    :type hardware_list: pd.DataFrame

    :param name: Given hardware (free formulation)
    :type name: str
    :return: dict
    """

    hardware = dict()
    for i in range(len(hardware_list)):
        if hardware_list.iloc[i]['name'] == name:
            hardware = dict(hardware_list.iloc[i])
            break
    return hardware


def get_hardware_type(hardware: str) -> dict:
    """
    Returns type of hardware and possible name of it.

    :param hardware: Given hardware (free formulation)
    :type hardware: str
    :return: dict
    """

    __read_hardware_datasets__()
    # Creating a dataframe of all hardware we have
    vid_result = {}
    proc_result = {}
    for i in range(len(videocards)):
        vid_result['name'] = videocards['Name']
        vid_result['rating'] = videocards['Rating']
        vid_result['type'] = 'Videocard'
    for i in range(len(processors)):
        proc_result['name'] = processors['name']
        proc_result['rating'] = processors['rating']
        proc_result['type'] = 'Processor'
    all_hardware = pd.concat([pd.DataFrame.from_dict(proc_result), pd.DataFrame.from_dict(vid_result)],
                             ignore_index=True, sort=False)

    # translator = Translator(from_lang='ru', to_lang='en')
    # given_hardware = translator.translate(str(hardware))
    try:
        given_hardware = transliterate.translit(str(hardware), 'ru', reversed=True)
    except LanguageDetectionError:
        given_hardware = hardware
    names = np.concatenate((np.array(videocards['Name']), np.array(processors['name'])),
                           axis=None)  # an array containing only hardware names
    indexes = search_similar_names(names, given_hardware)
    possible_hardware = get_hardware_data_by_name(all_hardware, names[list(indexes.keys())[-1]])

    # Алгоритм можно доработать, но и с этим жить можно. Наработки ниже
    """
    # slicing 50 first games with max coincidence to a given game
    feedback_list = list(indexes.keys())
    suggested_hardware = list()
    for i in feedback_list:
        tmp = Hardware(str(all_hardware.iloc[i]['name']), str(all_hardware.iloc[i]['type']))
        if tmp not in suggested_hardware:
            suggested_hardware.append(tmp)

    # if game with priored developer was found then move it to the top
    numbers = [int(s) for s in given_hardware.split() if s.isdigit()]
    print(numbers)
    for i in range(len(suggested_hardware)):
        for number in numbers:
            if all_hardware.iloc[i]['name'].find(str(number)):
                suggested_hardware[i], suggested_hardware[-1] = suggested_hardware[-1], suggested_hardware[i]
                break

    hardware_names = list()
    for val in suggested_hardware:
        hardware_names.append(val.name)
    """

    return {
        'hardware_type': possible_hardware['type'],
        'hardware_name': possible_hardware['name'],
    }


def init_firebase() -> None:
    """
    Initializes firebase if it is not already initialized.

    :return: None
    """

    global FIREBASE_OBJECT
    if FIREBASE_OBJECT is None:
        cred_object = firebase_admin.credentials.Certificate(
            os.path.join(str(pathlib.Path(__file__).parent.absolute()) + '/static/firebase_credentials.json'))
        FIREBASE_OBJECT = firebase_admin.initialize_app(cred_object, {
            'databaseURL': 'https://computershop-3bc7d-default-rtdb.europe-west1.firebasedatabase.app/'
        })


def get_last_order_id() -> int:
    """
    Return last order id.

    :return: int
    """

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
    """
    Returns last pretense in database id.

    :return: int
    """

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
    """
    Returns a dict with info of order.

    :param order_id: ID of an order
    :type order_id: int
    :return: dict
    """

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
    """
    Returns a dict with info of pretense.

    :param pretense_id: ID of a pretense
    :type pretense_id: int
    :return: dict
    """

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
    """
    Returns a dict with info of assembly.

    :param assembly_name: Name of assembly
    :type assembly_name: str
    :return: dict
    """

    __read_assembly_dataset__()
    for i in range(len(assemblies)):
        if assemblies.iloc[i]['name'] == assembly_name:
            return dict(assemblies.iloc[i])
    return {}


def make_order(assembly: str, name: str, address: str, email: str) -> dict:
    """
    Creates an order in database and returns a dict with order ID.

    :param assembly: Name of assembly
    :type assembly: str

    :param name: Name of a client
    :type name: str

    :param address: Home address of a client
    :type address: str

    :param email: Email address of a client
    :type email: str
    :return: dict
    """

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
    """
    Returns info about order by its ID.

    :param order_id: An ID of order
    :type order_id: str
    :return: dict
    """

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
    """
    Creates a pretense in database and returns a dict with pretense ID.

    :param name: Name of a client
    :type name: str

    :param email: Email address of a client
    :type email: str

    :param pretense_text: Text of pretense
    :type pretense_text: str
    :return: dict
    """

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
    """
    Returns info about pretense by its ID.

    :param pretense_id: ID of pretense
    :type pretense_id: str
    :return: dict
    """

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
