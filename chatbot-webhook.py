from flask import Flask, request, jsonify
import os
import json
import backend

app = Flask(__name__)
cf_port = os.getenv("PORT")


# Default
@app.route('/')
def default():
    return '<h1>An error ocurred.</h1>'


@app.route('/api', methods=['POST'])
def bot():
    income_request = json.loads(request.get_data())
    memory = income_request['conversation']['memory']
    game = memory['games']
    games = backend.game_analog_searcher(game)
    buttons = list()
    for val in games:
        buttons.append({
            "value": str(val),
            "title": str(val)
        })
    return jsonify(
        status=200,
        replies=[
            {
                'type': 'quickReplies',
                'content': {
                    "title": "Пожалуйста, выберите нужную игру из списка",
                    "buttons": buttons
                }
            }
        ],
        conversation={
            'memory': memory
        }
    )


@app.route('/assembly', methods=['POST'])
def get_assembly():
    income_request = json.loads(request.get_data())
    memory = income_request['conversation']['memory']
    game = memory['games']['raw']
    graphics = memory['graphics']['raw']
    assembly = backend.get_assembly(game, graphics)
    memory['assembly'] = assembly['name']
    return jsonify(
        status=200,
        replies=[
            {
                'type': 'text',
                'content': {
                    'Name': assembly['name'],
                    'Processor': assembly['processor'],
                    'Memory': assembly['memory'],
                    'Price': assembly['price'],
                    'Graphics': assembly['graphics']
                }
            }
        ],
        conversation={
            'memory': memory
        }
    )


@app.route('/create_order', methods=['POST'])
def create_order():
    income_request = json.loads(request.get_data())
    memory = income_request['conversation']['memory']
    answer = backend.make_order(str(memory['assembly']), str(memory['name']['raw']), str(memory['address']['raw']),
                                str(memory['email']['raw']))
    return jsonify(
        status=200,
        replies=[
            {
                'type': 'text',
                'content': answer,
            }
        ],
        conversation={
            'memory': memory
        }
    )


@app.route('/get_order', methods=['POST'])
def get_order():
    income_request = json.loads(request.get_data())
    memory = income_request['conversation']['memory']
    answer = backend.get_order_status(str(memory['order_id']['raw']))
    return jsonify(
        status=200,
        replies=[
            {
                'type': 'text',
                'content': answer,
            }
        ],
        conversation={
            'memory': memory
        }
    )


@app.route('/create_pretense', methods=['POST'])
def create_pretense():
    income_request = json.loads(request.get_data())
    memory = income_request['conversation']['memory']
    answer = backend.create_pretense(str(memory['name']['raw']), str(memory['email']['raw']),
                                     str(memory['pretense']['raw']))
    return jsonify(
        status=200,
        replies=[
            {
                'type': 'text',
                'content': answer,
            }
        ],
        conversation={
            'memory': memory
        }
    )


@app.route('/get_pretense', methods=['POST'])
def get_pretense():
    income_request = json.loads(request.get_data())
    memory = income_request['conversation']['memory']
    answer = backend.get_pretense_status(str(memory['pretense_id']['raw']))
    return jsonify(
        status=200,
        replies=[
            {
                'type': 'text',
                'content': answer,
            }
        ],
        conversation={
            'memory': memory
        }
    )


if __name__ == '__main__':
    if cf_port is None:
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=int(cf_port), debug=True)
