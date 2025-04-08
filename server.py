from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app)

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
    global players, game_data
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

@app.route('/host')
def host():
    return render_template('hostscreen.html')

@app.route('/player')
def player():
    return render_template('playerscreen.html')

def handle_answer(player_name):
    if game_data["player_role"].get(player_name) == "faker":
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

@socketio.on('start_game')
def handle_start_game():
    emit('game_started', broadcast=True)

# SocketIO event for when a player joins
@socketio.on('join_game')
def handle_join_game(data):
    username = data.get('username') #make a max char limit of 12
    if username:
        # Add new username to your game data if not already present.
        if username not in players:
            players.append(username)
            game_data["player_scores"][username] = 0  # Initialize score for the new player
        # Broadcast the join message to all connected clients.
        emit('player_joined', {'message': f'{username} has joined the game!'}, broadcast=True)
        # Also broadcast the updated players list.
        emit('players_update', {'players': players}, broadcast=True)

# New event: send current state when a client connects
@socketio.on('connect')
def handle_connect():
    # Send the current counter value to the newly connected client.
    emit('counter_update', {'counter': game_data['counter']})
    # Send the current players list to the newly connected client.
    emit('players_update', {'players': players})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
