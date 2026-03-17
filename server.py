from flask import Flask, jsonify, request
from flask_cors import CORS
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
import threading
import time
import random

app = Flask(__name__)
CORS(app)

DEVICES = [
    {
        "app_version": "269.0.0.18.75",
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "OnePlus",
        "device": "OnePlus5",
        "model": "ONEPLUS A5000",
        "cpu": "qcom",
    },
    {
        "app_version": "269.0.0.18.75",
        "android_version": 28,
        "android_release": "9.0.0",
        "dpi": "560dpi",
        "resolution": "1440x2960",
        "manufacturer": "samsung",
        "device": "star2qltecs",
        "model": "SM-G965F",
        "cpu": "samsungexynos9810",
    }
]

users = {}

class MiningSession:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.cl = Client()
        self.cl.set_device(random.choice(DEVICES))
        self.is_mining = False
        self.followed_count = 0
        self.coins = 0
        self.is_logged_in = False
        self.targets = []

    def login(self):
        try:
            try:
                self.cl.load_settings(f"{self.username}_session.json")
                self.cl.login(self.username, self.password)
            except:
                self.cl.login(self.username, self.password)
                self.cl.dump_settings(f"{self.username}_session.json")
            self.is_logged_in = True
            return True
        except Exception as e:
            print(f"Login Error: {e}")
            return False

    def safe_follow(self, target):
        if not self.is_mining:
            return "stopped"
        try:
            user_info = self.cl.user_info_by_username(target)
            
            # Private account check
            if user_info.is_private:
                return "skip"
            
            # Already following check
            friendship = self.cl.user_friendship_v1(user_info.pk)
            if friendship.following:
                return "already"
            
            # Follow karo
            self.cl.user_follow(user_info.pk)
            return "followed"
            
        except LoginRequired:
            self.login()
            return self.safe_follow(target)
        except Exception as e:
            print(f"Error: {e}")
            return "error"

    def mining_loop(self):
        print(f"Mining started for {self.username}")
        while self.is_mining:
            for target in self.targets:
                if not self.is_mining:
                    return
                    
                result = self.safe_follow(target)

                # Sirf follow hone pe +4 coins
                if result == "followed":
                    self.followed_count += 1
                    self.coins += 4
                    print(f"{self.username} followed {target} | +4 coins | Total: {self.coins} coins")
                    time.sleep(random.uniform(4, 8))

                    # 100 follows = 1 hour break
                    if self.followed_count % 100 == 0:
                        print(f"100 follows done! 1 hour break...")
                        for i in range(3600, 0, -60):
                            if not self.is_mining:
                                return
                            time.sleep(60)

                elif result == "already":
                    print(f"Already followed {target} - 0 coins")

                elif result == "skip":
                    print(f"Private account {target} - 0 coins")

                elif result == "error":
                    print(f"Error on {target} - 0 coins")

                elif result == "stopped":
                    return

            time.sleep(2)


# ═══════════════════
# API ROUTES
# ═══════════════════

@app.route('/')
def home():
    return jsonify({
        'status': 'success',
        'message': 'FollowHub Server Running!'
    })


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({
            'status': 'error',
            'message': 'Username aur password daalo!'
        })

    # Agar already logged in hai
    if username in users:
        return jsonify({
            'status': 'success',
            'message': 'Already logged in!',
            'username': username
        })

    session = MiningSession(username, password)
    success = session.login()

    if success:
        users[username] = session
        return jsonify({
            'status': 'success',
            'message': 'Login successful!',
            'username': username
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Login failed! Check credentials.'
        })


@app.route('/api/start_mining', methods=['POST'])
def start_mining():
    data = request.json
    username = data.get('username')
    targets = data.get('targets', [])

    if username not in users:
        return jsonify({
            'status': 'error',
            'message': 'User not logged in!'
        })

    session = users[username]
    
    if session.is_mining:
        return jsonify({
            'status': 'success',
            'message': 'Mining already running!'
        })

    session.targets = targets
    session.is_mining = True

    t = threading.Thread(target=session.mining_loop)
    t.daemon = True
    t.start()

    return jsonify({
        'status': 'success',
        'message': 'Mining started!'
    })


@app.route('/api/stop_mining', methods=['POST'])
def stop_mining():
    data = request.json
    username = data.get('username')

    if username not in users:
        return jsonify({
            'status': 'error',
            'message': 'User not logged in!'
        })

    users[username].is_mining = False
    return jsonify({
        'status': 'success',
        'message': 'Mining stopped!'
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    username = request.args.get('username')

    if username not in users:
        return jsonify({
            'status': 'error',
            'message': 'User not found!'
        })

    session = users[username]
    return jsonify({
        'status': 'success',
        'username': username,
        'coins': session.coins,
        'followed_count': session.followed_count,
        'is_mining': session.is_mining
    })


@app.route('/api/place_order', methods=['POST'])
def place_order():
    data = request.json
    username = data.get('username')
    target = data.get('target')
    quantity = data.get('quantity', 10)
    use_gems = data.get('use_gems', False)

    if username not in users:
        return jsonify({
            'status': 'error',
            'message': 'User not logged in!'
        })

    session = users[username]
    coins_needed = quantity * 8

    if not use_gems:
        if session.coins < coins_needed:
            return jsonify({
                'status': 'error',
                'message': f'{coins_needed} coins chahiye! Tumhare paas sirf {session.coins} hain.'
            })
        session.coins -= coins_needed

    return jsonify({
        'status': 'success',
        'message': f'{quantity} followers order placed!',
        'remaining_coins': session.coins
    })


@app.route('/api/follow_check', methods=['POST'])
def follow_check():
    data = request.json
    username = data.get('username')
    target = data.get('target')

    if username not in users:
        return jsonify({'status': 'error'})

    session = users[username]
    try:
        user_info = session.cl.user_info_by_username(target)
        return jsonify({
            'status': 'success',
            'is_private': user_info.is_private,
            'user_id': str(user_info.pk),
            'full_name': user_info.full_name
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )