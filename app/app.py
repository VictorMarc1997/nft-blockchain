from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain import Blockchain

app = Flask(__name__)
CORS(app)

current_blockchain = Blockchain()


@app.route('/status')
def status():
    response = {
        "status": "online" if current_blockchain is not None else "offline"
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


@app.route("/total_transactions", methods=["GET"])
def total_transactions():
    global current_blockchain

    count = current_blockchain.get_total_transactions()

    return jsonify({"result": count})


@app.route("/make_transaction", methods=["POST"])
def make_transaction():
    global current_blockchain
    data = request.get_json()

    if not data.get("sender") or data.get("sender") == "0":
        return jsonify({
            "success": False,
            "error": "Sender not provided",
        })
    elif not data.get("receiver") or data.get("receiver") == "0":
        return jsonify({
            "success": False,
            "error": "Receiver not provided",
        })
    elif not data.get("amount"):
        return jsonify({
            "success": False,
            "error": "Amount not provided",
        })

    success, new_block = current_blockchain.new_transaction(data)

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
def create_address():
    global current_blockchain
    request_data = request.get_json()
    address = request_data.get("address")

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

    if not success:
        return jsonify({
            "success": False,
            "error": "Invalid address",
        })

    return jsonify({
        "success": True,
        "new_block": str(new_block),
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
def get_wallet():
    global current_blockchain
    request_data = request.get_json()
    address = request_data.get("address")

    if not address:
        return jsonify({
            "success": False,
            "error": "Address not provided",
        })

    if address not in current_blockchain.all_addresses:
        return jsonify({
            "success": False,
            "error": "Address does not exists",
        })

    amount = current_blockchain.get_wallet(address)

    return jsonify({
        "success": True,
        "amount": amount,
    })


if __name__ == "__main__":
    app.run()
