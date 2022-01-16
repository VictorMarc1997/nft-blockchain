import base64
from flask import Flask, request, jsonify
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_cors import CORS
from flask_migrate import Migrate

from blockchain import Blockchain
from models import db, User, NFT

PAGE_SIZE = 1000

app = Flask(__name__)
app.secret_key = "this_is_so_secret_wow"
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:adidas842@localhost:5432/blockchain-app"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db.init_app(app)
migrate = Migrate(app, db)

current_blockchain = Blockchain()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@login_manager.request_loader
def load_user_from_request(req):
    api_key = req.headers.get('Authorization')
    if api_key:
        api_key = api_key.replace('Bearer ', '', 1)
        try:
            api_key = str(base64.b64decode(api_key), "utf-8")
        except TypeError:
            pass
        user = User.query.filter_by(api_key=api_key).first()
        if user:
            return user

    return None


@app.route('/signup', methods=['POST'])
def signup():
    global current_blockchain
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({
            "status": 401,
            "reason": "Email or Password Error"
        })

    # check if user already exists
    user = User.query.filter_by(email=data.get('email')).first()
    if user:
        return jsonify({
            "status": 401,
            "reason": "User already exists"
        })

    user = User(email=email)
    user.set_password(password)
    user.set_api_key()
    user.create_address(current_blockchain)
    db.session.add(user)
    db.session.commit()

    login_user(user)

    return jsonify(user.to_json() | {"status": 200})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({
            "status": 401,
            "reason": "Email or Password Error"
        })

    user = User.query.filter_by(email=email).first()

    if user:
        if user.check_password(password):
            login_user(user)
            return jsonify(user.to_json() | {"status": 200})

    return jsonify({
        "status": 401,
        "reason": "Email or Password Error"
    })


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})


@app.route('/status')
def status():
    response = {
        "bc_status": "online" if current_blockchain is not None else "offline"
    }
    return jsonify(response)


@app.route("/reload_blockchain", methods=["GET", "POST"])
def reload_blockchain():
    global current_blockchain

    success = current_blockchain.load_stored_chain()

    return jsonify({"success": success})


@app.route("/save_blockchain", methods=["GET", "POST"])
def save_blockchain():
    global current_blockchain

    success = current_blockchain.store_chain()

    return jsonify({"success": success})


@app.route("/list_addresses", methods=["GET"])
def list_addresses():
    global current_blockchain

    addresses = current_blockchain.all_addresses - set("0")

    return jsonify({
        "addresses": list(addresses),
        "total": len(list(addresses)),
    })


@app.route("/list_nfts", methods=["GET"])
def list_nfts():
    global current_blockchain

    assets = current_blockchain.all_assets
    nfts = NFT.query.all()

    result = []
    for nft in nfts:
        if nft.token in assets:
            result.append(nft.to_json())

    return jsonify({
        "nfts": result,
        "total": len(result),
    })


@app.route("/search_nft", methods=["POST"])
def search_nft():
    global current_blockchain
    data = request.get_json()
    token = data.get("token")

    nft = NFT.query.filter_by(token=token).first()

    if not nft:
        return jsonify({
            "success": False,
            "reason": "NFT does not exist",
        })

    return jsonify({
        "success": True,
        "nft": nft.to_json(),
    })


@app.route("/total_transactions", methods=["GET"])
def total_transactions():
    global current_blockchain

    return jsonify({"result": current_blockchain.total_transactions})


@app.route("/make_transaction", methods=["POST"])
@login_required
def make_transaction():
    global current_blockchain
    data = request.get_json()
    sender = current_user.address
    receiver = data.get("receiver")
    amount = data.get("amount", 0)
    asset = data.get("asset")

    if current_user.admin:
        sender = data.get("sender", sender)

    if not receiver or receiver == "0":
        return jsonify({
            "success": False,
            "error": "Receiver not provided",
        })
    elif not amount or not isinstance(amount, int):
        return jsonify({
            "success": False,
            "error": "Amount not provided",
        })

    info = {
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "asset": asset,
    }

    success, new_block = current_blockchain.new_transaction(info)

    if not success:
        return jsonify({
            "success": False,
            "error": "Invalid transaction",
        })

    return jsonify({
        "success": True,
        "new_block": str(new_block),
    })


@app.route("/create_address", methods=["POST"])
@login_required
def create_address():
    global current_blockchain
    request_data = request.get_json()
    address = request_data.get("address")

    if current_user.admin:
        if not address:
            return jsonify({
                "success": False,
                "error": "Address not provided",
            })
        if address in current_blockchain.all_addresses:
            return jsonify({
                "success": False,
                "error": "Address already exists",
            })

        data = {
            "sender": "0",
            "receiver": address,
            "amount": 100
        }
        success, new_block = current_blockchain.new_transaction(data)
        if success and not new_block:
            current_blockchain.build_block()

        return jsonify({
            "success": True,
            "new_block": str(new_block),
        })
    else:
        return jsonify({
            "success": False,
            "reason": "Not permitted",
        })


@app.route("/mine_block", methods=["GET", "POST"])
def mine_block():
    global current_blockchain
    new_block = current_blockchain.build_block()

    return jsonify({
        "success": True,
        "new_block": str(new_block),
    })


@app.route("/get_wallet", methods=["POST"])
@login_required
def get_wallet():
    global current_blockchain
    request_data = request.get_json()
    if current_user.admin:
        address = request_data.get("address", current_user.address)
        if address not in current_blockchain.all_addresses:
            return jsonify({
                "success": False,
                "error": "Address does not exists",
            })
        amount, assets = current_blockchain.get_wallet(address)
    else:
        amount, assets = current_blockchain.get_wallet(current_user.address)

    if amount is None:
        return jsonify({
            "success": False,
            "reason": "Address does not exist",
        })

    return jsonify({
        "success": True,
        "amount": amount,
        "assets": list(assets),
    })


@app.route("/get_blocks", methods=["POST"])
def get_blocks():
    global current_blockchain
    request_data = request.get_json() or {}

    page_id = request_data.get("page_id", 0) or 0
    remaining_blocks = current_blockchain.length - page_id

    if remaining_blocks > PAGE_SIZE:
        blocks = current_blockchain.get_blocks(page_id, PAGE_SIZE)
        page_id += PAGE_SIZE
    else:
        blocks = current_blockchain.get_blocks(page_id, remaining_blocks)
        page_id = None

    return jsonify({
        "blocks": blocks,
        "next_page": page_id,
    })


@app.route("/create_asset", methods=["POST"])
@login_required
def create_asset():
    global current_blockchain
    request_data = request.get_json()
    image_str = request_data.get("image")

    if not image_str:
        return jsonify({
            "success": False,
            "reason": "NFT not provided",
        })

    # check if nft already exists
    nft = NFT.query.filter_by(image=image_str).first()
    if nft:
        return jsonify({
            "status": 401,
            "reason": "NFT already exists"
        })

    nft = NFT(image=image_str)
    nft.create_token()
    db.session.add(nft)
    db.session.commit()

    info = {
        "sender": "0",
        "receiver": current_user.address,
        "amount": 0,
        "asset": nft.token,
    }

    success, new_block = current_blockchain.new_transaction(info)
    if success and not new_block:
        current_blockchain.build_block()
    else:
        return jsonify({
            "success": False,
            "reason": "Failed to add to blockchain",
        })

    return jsonify({
        "success": True,
        "token": nft.token
    })


if __name__ == "__main__":
    app.run()
