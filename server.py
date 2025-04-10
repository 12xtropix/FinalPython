from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Game data
players = []
prompts = []
player_sockets = {}
ready_players = set()

game_data = {
    "rounds": 4,
    "current_round": 1,
    "player_scores": {},
    "player_role": {},  # Mapping player -> role (faker or normal)
}

@app.route('/')
def index():
    return render_template('mainscreen.html')

@app.route('/host')
def host():
    return render_template('hostscreen.html')

@app.route('/player')
def player():
    return render_template('playerscreen.html')

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
    if game_data["player_role"].get(player_name) == "faker":
        return "You're the faker! Try to blend in."
    else:
        return random.choice(prompts)

def handle_vote(player_name):
    return "Vote recorded!"

def generate_prompt_sequence():
    types = ["hands", "pointing", "numbers"]
    alphabet = [chr(i) for i in range(65, 91)]  # A-Z

    all_prompts = {
        "hands": [f"hands_{letter}" for letter in alphabet],
        "pointing": [f"pointing_{letter}" for letter in alphabet],
        "numbers": [f"numbers_{letter}" for letter in alphabet],
        "final": [f"final_{letter}" for letter in alphabet]
    }

    selected_prompts = []

    for _ in range(8):
        category = random.choice(types)
        prompt = random.choice(all_prompts[category])
        selected_prompts.append(prompt)

    final_prompt = random.choice(all_prompts["final"])
    selected_prompts.append(final_prompt)

    return selected_prompts

@socketio.on('join_game')
def handle_join_game(data):
    username = data.get('username')
    if username and len(username) <= 20:
        if username not in players:
            players.append(username)
            game_data["player_scores"][username] = 0

        sid = request.sid
        player_sockets[username] = sid
        join_room(sid)

        emit('player_joined', {'message': f'{username} has joined the game!'}, broadcast=True)
        emit('players_update', {'players': players}, broadcast=True)

@socketio.on('start_game')
def handle_start_game():
    global prompts, ready_players
    ready_players = set()
    prompts = generate_prompt_sequence()

    faker = random.choice(players)
    game_data["player_role"] = {
        player: ("faker" if player == faker else "normal") for player in players
    }

    current_prompt = prompts[game_data["current_round"] - 1]
    prompt_type = current_prompt.split('_')[0]
    prompt_text_for_normal = current_prompt
    prompt_text_for_faker = "You're the faker! Try to blend in."

    for player in players:
        role = game_data["player_role"].get(player)
        sid = player_sockets.get(player)
        if not sid:
            continue

        prompt_text = prompt_text_for_normal if role != "faker" else prompt_text_for_faker

        socketio.emit('serve_prompt', {
            "prompt_type": prompt_type,
            "prompt_text": prompt_text
        }, room=sid)

    # Send prompt to host so it's revealed after countdown or all ready
    socketio.emit('host_prompt', {
        "prompt_type": prompt_type,
        "prompt_text": prompt_text_for_normal
    })

@socketio.on('player_ready')
def handle_player_ready(data):
    username = data.get('username')
    if username and username in players:
        ready_players.add(username)
        emit('ready_update', {
            "ready_count": len(ready_players),
            "total_players": len(players)
        }, broadcast=True)

        if len(ready_players) == len(players):
            # All ready, skip countdown
            socketio.emit('start_countdown', {"seconds": 0})
        elif len(ready_players) == 1:
            # First player ready, start regular countdown
            socketio.emit('start_countdown', {"seconds": 20})

@socketio.on('connect')
def handle_connect():
    emit('players_update', {'players': players})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
