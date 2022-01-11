from flask import Flask, request, jsonify
from blockchain import Blockchain

app = Flask(__name__)

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

    addresses = current_blockchain.get_all_addresses - set("0")

    return jsonify({"addresses": list(addresses)})


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
        "new_block": new_block,
    })


@app.route("/create_address", methods=["POST"])
def create_address():
    global current_blockchain
    request_data = request.get_json()
    if not request_data.get("address"):
        return jsonify({
            "success": False,
            "error": "Address not provided",
        })

    data = {
        "sender": "0",
        "receiver": request_data["address"],
        "amount": "0"
    }
    success, new_block = current_blockchain.new_transaction(data)

    if not success:
        return jsonify({
            "success": False,
            "error": "Invalid address",
        })

    return jsonify({
        "success": True,
        "new_block": new_block,
    })


if __name__ == "__main__":
    app.run()
