from flask import Flask, request, jsonify
import asyncio
import aiohttp
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
import sssh

from transaction import Transaction

app = Flask(__name__)

node_addresses = {
    'node1': 'http://127.0.0.1:5001',
    'node2': 'http://127.0.0.1:5002',
    'node3': 'http://127.0.0.1:5003',
}

# Map untuk menyimpan public keys dari setiap node non-leader
# Digunakan pada saat verifikasi digital signature
public_keys = {}

# Fungsi initialize node digunakan untuk membagi secret
async def initialize_node(session, node_url, share):
    async with session.post(f'{node_url}/initialize', json={'share': share}) as response:
        return await response.json()

# Fungsi untuk mengambil public key dari setiap node anggota
async def fetch_public_key(session, node_url, node_id):
    async with session.get(f'{node_url}/public_key') as response:
        resp = await response.json()
        public_key_pem = base64.b64decode(resp['public_key'])
        public_key = serialization.load_pem_public_key(public_key_pem)
        public_keys[node_id] = public_key

# Fungsi untuk meminta digital signature
async def get_signature(session, node_url, transaction):
    async with session.post(f'{node_url}/request_signature', json={'transaction': transaction}) as response:
        return await response.json()

# Fungsi untuk meminta secret share
async def get_share(session, node_url):
    async with session.post(f'{node_url}/request_share') as response:
        return await response.json()

# Route untuk mendistribusikan secret
@app.route('/distribute_shares', methods=['POST'])
async def distribute_shares():
    secret = "my_secret_key"
    shares = shares = sssh.create(3, 2, secret)

    async with aiohttp.ClientSession() as session:
        tasks = [initialize_node(session, node_addresses[f'node{i+1}'], shares[i]) for i in range(3)]
        responses = await asyncio.gather(*tasks)
        return jsonify({'status': 'Shares distributed', 'responses': responses})

# Route untuk menginisialisasi node-node
@app.route('/initialize_nodes', methods=['POST'])
async def initialize_nodes():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_public_key(session, node_addresses[f'node{i+1}'], f'node{i+1}') for i in range(3)]
        await asyncio.gather(*tasks)
    return jsonify({'status': 'Public keys fetched'})

# Route untuk update public key yang sudah digenerate masing-masing node
@app.route('/update_public_key', methods=['POST'])
def update_public_key():
    data = request.json
    node_id = data['node_id']
    public_key_pem = base64.b64decode(data['public_key'])
    public_key = serialization.load_pem_public_key(public_key_pem)
    public_keys[node_id] = public_key
    return jsonify({'status': 'Public key updated'})

# Main route untuk menerima suatu transaksi
@app.route('/submit_transaction', methods=['POST'])
async def submit_transaction():
    data = request.json
    transaction_data = data['transaction']

    async with aiohttp.ClientSession() as session:
        tasks = [get_signature(session, node_url, transaction_data) for node_url in node_addresses.values()]
        responses = await asyncio.gather(*tasks)
        signatures = [resp['signature'] for resp in responses]

        valid_signatures = 0
        for node_id, signature in zip(public_keys.keys(), signatures):
            transaction = Transaction(**transaction_data)
            transaction.signature = signature
            public_key_pem = public_keys[node_id].public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            if transaction.verify_transaction(public_key_pem):
                valid_signatures += 1

        if valid_signatures >= 2:
            share_tasks = [get_share(session, node_url) for node_url in node_addresses.values()]
            share_responses = await asyncio.gather(*share_tasks)
            shares = [base64.b64decode(resp['share']).decode() for resp in share_responses]

            try:
                secret = sssh.combine(shares[:2])
                print(f'Reconstructed secret: {secret}')
                return jsonify({'status': 'Transaction approved', 'secret': secret})
            except Exception as e:
                print(f'Failed to reconstruct secret: {e}')
                return jsonify({'status': 'Transaction rejected', 'error': str(e)})
        else:
            return jsonify({'status': 'Transaction rejected'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
