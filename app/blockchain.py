import time
import json
import os
import glob
from hashlib import sha256

DIFFICULTY_START = 2
DIFFICULTY_INCREASE_STEP = 1000
TRANSACTIONS_PER_BLOCK = 3


class Block:
    """
    Block object used to create the chain
    """
    def __init__(self, index, proof_number, previous_hash, data, timestamp=None):
        self.index = index
        self.proof_number = proof_number
        self.previous_hash = previous_hash
        self.data = data
        self.timestamp = timestamp or time.time()

    @property
    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    def to_dict(self):
        return {
            "index": self.index,
            "proof_number": self.proof_number,
            "current_hash": self.compute_hash,
            "previous_hash": self.previous_hash,
            "data": self.data,
            "timestamp": int(self.timestamp)*1000,
        }

    def __repr__(self):
        return f"{self.index} - {self.proof_number} - {self.previous_hash} - {self.timestamp}"

    def __str__(self):
        return f"{self.index} - {self.proof_number} - {self.previous_hash} - {self.timestamp}"

    def __eq__(self, other):
        return str(self) == str(other)


class Blockchain:
    difficulty = DIFFICULTY_START

    def __init__(self):
        # stores all blocks
        self.chain = []
        # stores all data about block to be created
        self.current_data = []

        # try loading from storage
        if self.load_stored_chain():
            return

        self.build_genesis()

    def load_stored_chain(self):
        # drop everything in current_data
        self.current_data = []

        chain = self.get_latest_stored_chain()
        if chain is None:
            return False

        self.chain = chain
        return True

    def store_chain(self):
        latest_chain = self.get_latest_stored_chain() or []

        # check latest save file contains the chain we are saving
        # avoid tampering
        if not all(block in self.chain for block in latest_chain):
            return False

        serialized_chain = [block.to_json() for block in self.chain]

        with open(f"storage/chain_save_files/chain_{int(time.time())}.json", "w+") as f:
            json.dump(serialized_chain, f)

        return True

    def build_genesis(self):
        self.build_block(initial=True)

    def build_block(self, initial=False):

        if initial:
            proof_number = 0
            previous_hash = 0
        else:
            previous_proof_number = self.latest_block.proof_number
            previous_hash = self.latest_block.compute_hash
            proof_number = Blockchain.proof_of_work(previous_proof_number)

        block = Block(
            index=len(self.chain),
            proof_number=proof_number,
            previous_hash=previous_hash,
            data=self.current_data
        )
        # empty the current_data since it was written
        self.current_data = []

        Blockchain.add_block_to_chain(self.chain, block)
        self.store_chain()
        return block

    def new_transaction(self, transaction):
        """
        :param transaction: Dict: {
            sender: ""
            receiver: ""
            amount: ""
        }
        :return: (block_built_flag, the_block)
        """
        sender = transaction.get("sender")
        receiver = transaction.get("receiver")
        amount = transaction.get("amount", 0)
        asset = transaction.get("asset")

        if (
            not sender
            or not receiver
            or sender not in self.all_addresses
            or sender == receiver
            or (not amount and not asset)
        ):
            return False, None

        if amount < 0:
            return False, None

        if sender != "0":
            sender_amount, sender_assets = self.get_wallet(sender)

            if sender_amount < amount:
                return False, None

            if asset and asset not in sender_assets:
                return False, None

        if asset and amount > 0:
            return False, None

        data = {
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "asset": asset,
        }
        self.current_data.append(data)

        if len(self.current_data) == TRANSACTIONS_PER_BLOCK:
            return True, self.build_block()

        return True, None

    @property
    def length(self):
        return len(self.chain)

    @property
    def latest_block(self):
        return self.chain[-1]

    @property
    def all_addresses(self):
        addresses = set("0")

        for block in self.chain:
            for data in block.data:
                addresses.add(data.get("sender"))
                addresses.add(data.get("receiver"))

        return addresses

    @property
    def all_assets(self):
        assets = set()

        for block in self.chain:
            for data in block.data:
                if data.get("asset"):
                    assets.add(data.get("asset"))

        return assets

    @property
    def total_transactions(self):
        count = 0

        for block in self.chain:
            count += len(block.data)

        return count

    @staticmethod
    def add_block_to_chain(chain, block):
        Blockchain.difficulty = DIFFICULTY_START + len(chain) // DIFFICULTY_INCREASE_STEP
        chain.append(block)

    @staticmethod
    def confirm_validity(block, previous_block):
        if (
            previous_block.index + 1 != block.index
            or previous_block.compute_hash != block.previous_hash
            or previous_block.timestamp >= block.timestamp
            or not Blockchain.verify_proof(block.proof_number, previous_block.proof_number)
        ):
            return False

        return True

    @staticmethod
    def proof_of_work(last_proof):
        proof_no = 0
        while not Blockchain.verify_proof(proof_no, last_proof):
            proof_no += 1

        return proof_no

    @staticmethod
    def verify_proof(last_proof, proof):
        # verifying the proof: does hash(last_proof, proof) contain {self.difficulty} leading zeros"
        guess = f'{last_proof**2 - proof**2}'.encode()
        guess_hash = sha256(guess).hexdigest()

        return guess_hash[:Blockchain.difficulty] == "0" * Blockchain.difficulty

    @staticmethod
    def get_latest_stored_chain():
        chain = []
        list_of_saves = list(glob.iglob("storage/chain_save_files/*"))

        if not list_of_saves:
            return None

        latest_save = max(list_of_saves, key=lambda x: int(x[:-5].split("_")[-1]))

        with open(latest_save, "r") as f:
            serialized_chain = json.load(f)
            for block_str in serialized_chain:
                block = Block(**json.loads(block_str))
                if block.previous_hash:
                    if not Blockchain.confirm_validity(block, chain[-1]):
                        return None

                Blockchain.add_block_to_chain(chain, block)

        return chain

    def get_wallet(self, address):
        coin_amount = 0
        assets = set()

        if address not in self.all_addresses:
            return None

        for block in self.chain:
            for data in block.data:
                if address == data["sender"]:
                    coin_amount -= data["amount"]
                    if data.get("asset"):
                        assets.remove(data.get("asset"))

                elif address == data["receiver"]:
                    coin_amount += data["amount"]
                    if data.get("asset"):
                        assets.add(data.get("asset"))

        return coin_amount, assets

    def get_blocks(self, start=0, count=None):
        blocks = []
        if count is None:
            count = len(self.chain)

        if start >= len(self.chain) or count > len(self.chain) - start:
            return None

        c = 1

        for index, block in enumerate(self.chain):

            if index >= start and c <= count:
                blocks.append(block.to_dict())
                c += 1

        return blocks

