from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random
import json
import os

app = Flask(__name__)
socketio = SocketIO(app)

players = []
prompts = []
player_sockets = {}
ready_players = set()
votes = {}

game_data = {
    "current_round": 0,
    "player_role": {},
    "current_prompt": "",
    "current_category": "",
    "round_ready": set(),
    "current_faker": None,
    "last_faker_category": None,
    "scores": {}
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
    with open(os.path.join(os.path.dirname(__file__), 'prompts.json'), encoding='utf-8') as f:
        all_prompts = json.load(f)

    sequence = []
    for category in ["hands"] * 3 + ["pointing"] * 3 + ["numbers"] * 3:
        if all_prompts[category]:
            prompt = random.choice(all_prompts[category])
            sequence.append((prompt, category))
            all_prompts[category].remove(prompt)
        else:
            sequence.append(("No prompt available", category))
    return sequence

def start_next_round():
    round_index = game_data["current_round"]

    if round_index >= len(prompts):
        declare_final_winners()
        return

    current_prompt, current_category = prompts[round_index]
    game_data["current_prompt"] = current_prompt
    game_data["current_category"] = current_category
    game_data["round_ready"] = set()
    game_data["current_round"] += 1
    global votes
    votes.clear()

    if game_data["last_faker_category"] != current_category:
        game_data["current_faker"] = random.choice(players)
        game_data["last_faker_category"] = current_category

    game_data["player_role"] = {
        player: ("faker" if player == game_data["current_faker"] else "normal")
        for player in players
    }

    for player in players:
        sid = player_sockets.get(player)
        role = game_data["player_role"].get(player)
        if not sid:
            continue

        if role == "faker":
            socketio.emit('serve_prompt', {
                "prompt": "You are the faker! Try to blend in!",
                "category": current_category
            }, room=sid)
        else:
            socketio.emit('serve_prompt', {
                "prompt": current_prompt,
                "category": current_category
            }, room=sid)

@socketio.on('join_game')
def handle_join_game(data):
    username = data.get('username')
    if username and len(username) <= 20:
        if username not in players:
            players.append(username)
            game_data["scores"][username] = 0
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
    game_data["last_faker_category"] = None
    socketio.emit("game_started")
    start_next_round()

@socketio.on('ready')
def handle_ready(data):
    player_name = data.get('player_name')
    if player_name:
        game_data["round_ready"].add(player_name)

    if len(game_data["round_ready"]) == len(players):
        for name, sid in player_sockets.items():
            if name.lower() == "host":
                socketio.emit('pre_prompt_countdown', room=sid)
                break
        else:
            socketio.emit('pre_prompt_countdown')

@socketio.on('trigger_prompt_reveal')
def handle_trigger_prompt_reveal():
    current_prompt = game_data["current_prompt"]
    current_category = game_data["current_category"]

    socketio.emit('show_prompt', {
        "prompt": current_prompt,
        "category": current_category
    })

    socketio.emit('start_countdown', {"seconds": 30})

@socketio.on('vote')
def handle_vote(data):
    player_name = data.get('player_name')
    voted_for = data.get('voted_for')
    if player_name and voted_for:
        votes[player_name] = voted_for

    if len(votes) == len(players):
        faker = game_data["current_faker"]
        normal_voters = [p for p in players if p != faker]
        voted_for_faker = all(votes.get(p) == faker for p in normal_voters)

        socketio.emit('stop_countdown')
        socketio.emit('hide_countdown')

        if voted_for_faker:
            for player in normal_voters:
                game_data["scores"][player] += 100
            message = f"The faker **{faker}** has been caught!"
            socketio.emit('round_results', {"votes": votes, "message": message})
            skip_to_next_game_category()
        else:
            for player in normal_voters:
                if votes.get(player) == faker:
                    game_data["scores"][player] += 100
            if faker in game_data["scores"]:
                game_data["scores"][faker] += 125
            message = "Voting complete."
            socketio.emit('round_results', {"votes": votes, "message": message})

        socketio.emit('leaderboard_update', {"scores": game_data["scores"]})

def skip_to_next_game_category():
    current_index = game_data["current_round"]
    current_category = game_data["current_category"]

    for i in range(current_index, len(prompts)):
        _, category = prompts[i]
        if category != current_category:
            game_data["current_round"] = i
            break
    else:
        declare_final_winners()
        return

    game_data["round_ready"] = set()
    start_next_round()

def declare_final_winners():
    if not game_data["scores"]:
        socketio.emit('game_over', {"message": "Game over! Thanks for playing!"})
        return

    best_sleuth = max(game_data["scores"], key=lambda p: game_data["scores"][p])
    scores_sorted = sorted(game_data["scores"].items(), key=lambda x: x[1], reverse=True)

    leaderboard_text = "🏆 Final Leaderboard 🏆\n\n"
    for name, score in scores_sorted:
        leaderboard_text += f"{name}: {score} points\n"

    message = f"Best Sleuth: {best_sleuth}!\n\n{leaderboard_text}"
    socketio.emit('game_over', {"message": message})

@socketio.on('connect')
def handle_connect():
    emit('players_update', {'players': players})

@socketio.on('next_round')
def handle_next_round():
    start_next_round()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
#a