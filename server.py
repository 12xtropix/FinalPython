from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit  # Importing SocketIO
import random
#test
app = Flask(__name__)
socketio = SocketIO(app)  # Initializing SocketIO

# Game data
players = []
prompts = []
faker_prompt = []

game_data = {
    "rounds": 5,
    "current_round": 1,
    "player_scores": {},
    "player_role": {},  # Mapping player -> role (faker or normal)
    "counter": 0  # New variable for the counter
}

@app.route('/')
def index():
    return render_template('mainscreen.html')

@app.route('/start', methods=['POST'])
def start_game():
    global players
    global game_data

    players = ["Player 1", "Player 2", "Player 3"]  # Example players
    game_data["player_scores"] = {player: 0 for player in players}
    game_data["player_role"] = {player: "faker" if i == 0 else "normal" for i, player in enumerate(players)}

    return jsonify({"status": "game started", "game_data": game_data})

@app.route('/play', methods=['POST'])
def play():
    player_name = request.json['player_name']
    action = request.json['action']
    response = ""

    if action == "answer":
        response = handle_answer(player_name)
    elif action == "vote":
        response = handle_vote(player_name)

    return jsonify({"status": response})

def handle_answer(player_name):
    if game_data["player_role"][player_name] == "faker":
        return faker_prompt
    else:
        return random.choice(prompts)

def handle_vote(player_name):
    return "Vote recorded!"

# SocketIO event for counter increment
@socketio.on('increment_counter')
def increment_counter():
    game_data['counter'] += 1
    emit('counter_update', {'counter': game_data['counter']}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)  # Run with SocketIO
