import time
import json
from hashlib import sha256

DIFFICULTY_INCREASE_STEP = 1000000


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

    def __repr__(self):
        return f"{self.index} - {self.proof_number} - {self.previous_hash} - {self.data} - {self.timestamp}"


class Blockchain:
    difficulty = 2

    def __init__(self):
        # stores all blocks
        self.chain = []
        # stores all data about block to be created
        self.current_data = []
        self.nodes = set()
        self.build_genesis()

    def build_genesis(self):
        self.build_block(proof_number=0, previous_hash=0)

    def build_block(self, proof_number, previous_hash):
        block = Block(
            index=len(self.chain),
            proof_number=proof_number,
            previous_hash=previous_hash,
            data=self.current_data
        )
        # empty the current_data since it was written
        self.current_data = []

        self.chain.append(block)
        return block

    @staticmethod
    def confirm_validity(block, previous_block):
        if (
            previous_block.index + 1 != block.index
            or previous_block.compute_hash() != block.previous_hash
            or previous_block.timestamp >= block.timestamp
            or not Blockchain.verify_proof(block.proof_number, previous_block.proof_no)
        ):
            return False

        return True

    def new_data(self, sender, receiver, amount):
        self.current_data.append({
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
        })
        return True

    @property
    def latest_block(self):
        return self.chain[-1]

    @staticmethod
    def proof_of_work(last_proof):
        proof_no = 0
        while not Blockchain.verify_proof(proof_no, last_proof):
            proof_no += 1

        return proof_no

    @staticmethod
    def verify_proof(last_proof, proof):
        # verifying the proof: does hash(last_proof, proof) contain {self.difficulty} leading zeros"
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = sha256(guess).hexdigest()

        return guess_hash[:Blockchain.difficulty] == "0" * Blockchain.difficulty

    # def block_mining(self, details_miner):
    #     self.new_data(
    #         sender="0",  # it implies that this node has created a new block
    #         receiver=details_miner,
    #         amount=1,  # creating a new block (or identifying the proof number) is awarded with 1
    #     )
    #
    #     last_block = self.latest_block
    #     last_proof_no = last_block.proof_no
    #     proof_no = self.proof_of_work(last_proof_no)
    #     last_hash = last_block.calculate_hash
    #
    #     block = self.build_block(proof_no, last_hash)
    #     return vars(block)
    #
    # def create_node(self, address):
    #     self.nodes.add(address)
    #     return True
    #
    # @staticmethod
    # def obtain_block_object(block_data):
    #     # obtains block object from the block data
    #
    #     return Block(
    #         block_data['index'],
    #         block_data['proof_no'],
    #         block_data['prev_hash'],
    #         block_data['data'],
    #         timestamp=block_data['timestamp'])


blockchain = Blockchain()

print("***Mining fccCoin about to start***")
print(blockchain.chain)

last_block = blockchain.latest_block
last_proof_number = last_block.proof_number
proof_number = blockchain.proof_of_work(last_proof_number)

blockchain.new_data(
    sender="0",  #it implies that this node has created a new block
    receiver="Quincy Larson",  #let's send Quincy some coins!
    amount=1,  #creating a new block (or identifying the proof number) is awarded with 1
)

last_hash = last_block.compute_hash
block = blockchain.build_block(proof_number, last_hash)

print("***Mining fccCoin has been successful***")
print(blockchain.chain)
