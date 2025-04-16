from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Game data
players = []
prompts = []
player_sockets = {}  # username -> socket ID
ready_players = set()  # Players who are ready
votes = {}  # To store who voted for who
game_data = {
    "current_round": 1,
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
        return "You are the faker, try to blend in!"
    else:
        return random.choice(prompts)


def handle_vote(player_name):
    return "Vote recorded!"


@socketio.on('join_game')
def handle_join_game(data):
    username = data.get('username')
    if username and len(username) <= 20:
        if username not in players:
            players.append(username)

        sid = request.sid
        player_sockets[username] = sid
        join_room(sid)

        emit('player_joined', {'message': f'{username} has joined the game!'}, broadcast=True)
        emit('players_update', {'players': players}, broadcast=True)


@socketio.on('start_game')
def handle_start_game():
    global prompts, ready_players
    prompts = generate_prompt_sequence()
    ready_players = set()

    # Assign roles (1 faker, rest normal)
    faker = random.choice(players)
    game_data["player_role"] = {
        player: ("faker" if player == faker else "normal") for player in players
    }

    current_prompt = prompts[game_data["current_round"] - 1]

    # Send prompt to each player based on role
    for player in players:
        role = game_data["player_role"].get(player)
        sid = player_sockets.get(player)
        if not sid:
            continue

        if role == "faker":
            # Faker gets generic instruction
            socketio.emit('serve_prompt', {"prompt": "Who is the faker? Try to blend in!"}, room=sid)
        else:
            # Normal players get real prompt
            socketio.emit('serve_prompt', {"prompt": current_prompt}, room=sid)

    # Send the real prompt to the host only
    socketio.emit('show_prompt', {"prompt": current_prompt})

    # Start countdown and show it to all
    socketio.emit('start_countdown', {"seconds": 20})


@socketio.on('ready')
def handle_ready(data):
    player_name = data.get('player_name')
    if player_name:
        ready_players.add(player_name)

    # Check if all players are ready, skip countdown if so
    if len(ready_players) == len(players):
        socketio.emit('start_game')  # Trigger start game immediately
        socketio.emit('start_countdown', {"seconds": 0})  # Immediately stop countdown


@socketio.on('vote')
def handle_vote(data):
    player_name = data.get('player_name')
    voted_for = data.get('voted_for')
    if player_name and voted_for:
        votes[player_name] = voted_for

    # Emit the vote updates to the host
    socketio.emit('vote_update', {'votes': votes}, room=player_sockets.get('host'))


@socketio.on('connect')
def handle_connect():
    emit('players_update', {'players': players})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
