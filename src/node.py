from flask import Flask, request, jsonify
import base64
import requests
import threading
import time
import os
from cryptography.hazmat.primitives import serialization
from node_config import NodeConfig
from transaction import Transaction

app = Flask(__name__)

port = int(os.environ.get('PORT', 5001))

node_id = os.environ.get('NODE_ID', 'node1')
endpoint_url = f"http://127.0.0.1:{port}"

node_config = NodeConfig(
    node_id=node_id,
    endpoint_url=endpoint_url
)
node_config.generate_keys()
share = None

LEADER_URL = 'http://127.0.0.1:5000/update_public_key'

@app.route('/initialize', methods=['POST'])
def initialize():
    global share
    data = request.json
    share = base64.b64decode(data['share'])
    node_config.secret_share = share
    return jsonify({'status': 'initialized'})

@app.route('/public_key', methods=['GET'])
def public_key_endpoint():
    try:
        return jsonify({'public_key': base64.b64encode(node_config.get_public_key_pem()).decode()})
    except Exception as e:
        print(f'Error retrieving public key: {e}')
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/request_signature', methods=['POST'])
def request_signature():
    data = request.json
    transaction_data = data['transaction']
    
    transaction = Transaction(**transaction_data)
    
    try:
        private_key_pem = node_config.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        transaction.sign_transaction(private_key_pem)
        return jsonify({'signature': transaction.signature})
    except Exception as e:
        print(f'Error signing transaction: {e}')
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/request_share', methods=['POST'])
def request_share():
    global share
    try:
        return jsonify({'share': base64.b64encode(share).decode()})
    except Exception as e:
        print(f'Error retrieving share: {e}')
        return jsonify({'status': 'error', 'message': str(e)})

def rotate_keys():
    while True:
        time.sleep(86400)

        node_config.generate_keys()

        public_key_pem = node_config.get_public_key_pem()
        response = requests.post(LEADER_URL, json={'node_id': node_config.node_id, 'public_key': base64.b64encode(public_key_pem).decode()})
        print(response.json())

key_rotation_thread = threading.Thread(target=rotate_keys)
key_rotation_thread.start()

if __name__ == '__main__':
    app.run(port=port)
