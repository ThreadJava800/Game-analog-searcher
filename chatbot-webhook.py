from flask import Flask, request, jsonify
import os
import json
import datetime
import requests
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
    game = memory['games']
    graphics = memory['graphics']['raw']
    assembly = backend.get_assembly(game, graphics)
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
    

if __name__ == '__main__':
	if cf_port is None:
		app.run(host='0.0.0.0', port=5000, debug=True)
	else:
		app.run(host='0.0.0.0', port=int(cf_port), debug=True)