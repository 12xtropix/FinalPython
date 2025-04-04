"""

This is the server file

"""
from flask import Flask, render_template, request, jsonify #Flask allows us to run local server from pycharm, render is for rendering, request gets client data, jsonify turns data in json form
import random #to determine prompts/faker

app = Flask(__name__) #creates the flask server instance

# game stuff - will discuss organization tmrw in class
players = []
prompts = []
faker_prompt = []

# game data
game_data = {
    "rounds": 5,
    "current_round": 1,
    "player_scores": {},
    "player_role": {},  # Mapping player -> role (faker or normal)
}

@app.route('/') #when a player accesses the client/index, this pulls the html file and renders it on their screen
def index():
    return render_template('index.html')  # Serve the HTML page for the game

@app.route('/start', methods=['POST']) #when a post request is made, runs the start game function
def start_game():
    global players
    global game_data

    players = ["Player 1", "Player 2", "Player 3"]  # example players
    game_data["player_scores"] = {player: 0 for player in players}
    game_data["player_role"] = {player: "faker" if i == 0 else "normal" for i, player in enumerate(players)}

    return jsonify({"status": "game started", "game_data": game_data})

@app.route('/play', methods=['POST']) #when player actions are made, calls the useful function - action or vote
def play():
    player_name = request.json['player_name']
    action = request.json['action']  # e.g., answer or vote
    response = ""

    if action == "answer":
        response = handle_answer(player_name)
    elif action == "vote":
        response = handle_vote(player_name)

    return jsonify({"status": response})

def handle_answer(player_name): #finding which prompt to send to the client
    # Logic to handle answering a prompt (send different prompts to normal players and the faker)
    if game_data["player_role"][player_name] == "faker":
        return faker_prompt
    else:
        return random.choice(prompts)

def handle_vote(player_name): # just tells the client that the vote has been recorded right now
    # Logic to handle voting for who the faker is
    return "Vote recorded!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Run the server on the local network
