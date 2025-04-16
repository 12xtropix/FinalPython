from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random

app = Flask(__name__)
socketio = SocketIO(app)

# Game data
players = []
prompts = []
player_sockets = {}  # username -> socket ID
ready_players = set()
votes = {}

game_data = {
    "current_round": 0,
    "player_role": {},  # Mapping player -> role (faker or normal)
    "current_prompt": ""
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
    alphabet = [chr(i) for i in range(65, 91)]  # A-Z
    all_prompts = {
        "hands": [f"hands_{letter}" for letter in alphabet],
        "pointing": [f"pointing_{letter}" for letter in alphabet],
        "numbers": [f"numbers_{letter}" for letter in alphabet]
    }

    sequence = []
    for category in ["hands"] * 3 + ["pointing"] * 3 + ["numbers"] * 3:
        sequence.append(random.choice(all_prompts[category]))

    return sequence


def start_next_round():
    round_index = game_data["current_round"]

    if round_index >= len(prompts):
        socketio.emit('game_over', {"message": "Game over! Thanks for playing!"})
        return

    current_prompt = prompts[round_index]
    game_data["current_prompt"] = current_prompt
    game_data["current_round"] += 1
    global votes
    votes.clear()

    for player in players:
        sid = player_sockets.get(player)
        role = game_data["player_role"].get(player)
        if not sid:
            continue

        if role == "faker":
            socketio.emit('serve_prompt', {"prompt": "Who is the faker? Try to blend in!"}, room=sid)
        else:
            socketio.emit('serve_prompt', {"prompt": current_prompt}, room=sid)

    socketio.emit('show_prompt', {"prompt": current_prompt})
    socketio.emit('start_countdown', {"seconds": 20})


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
    game_data["current_round"] = 0

    faker = random.choice(players)
    game_data["player_role"] = {
        player: ("faker" if player == faker else "normal") for player in players
    }

    start_next_round()


@socketio.on('ready')
def handle_ready(data):
    player_name = data.get('player_name')
    if player_name:
        ready_players.add(player_name)

    if len(ready_players) == len(players):
        start_next_round()


@socketio.on('vote')
def handle_vote(data):
    player_name = data.get('player_name')
    voted_for = data.get('voted_for')
    if player_name and voted_for:
        votes[player_name] = voted_for

    socketio.emit('vote_update', {'votes': votes}, room=player_sockets.get('host'))

    if len(votes) == len(players):
        socketio.emit('round_results', {"votes": votes})
        socketio.sleep(5)
        start_next_round()


@socketio.on('connect')
def handle_connect():
    emit('players_update', {'players': players})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=4000, allow_unsafe_werkzeug=True)