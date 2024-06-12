from flask import Flask, request, jsonify
import asyncio
import aiohttp
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
import pyshamir

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
    try:
        async with session.post(f'{node_url}/initialize', json={'share': share}) as response:
            return await response.json()
    except aiohttp.ClientError as e:
        print(f'Error initializing node at {node_url}: {e}')
        return {'status': 'error', 'message': str(e)}

# Fungsi untuk mengambil public key dari setiap node anggota
async def fetch_public_key(session, node_url, node_id):
    try:
        async with session.get(f'{node_url}/public_key') as response:
            resp = await response.json()
            public_key_pem = base64.b64decode(resp['public_key'])
            public_key = serialization.load_pem_public_key(public_key_pem)
            public_keys[node_id] = public_key
    except aiohttp.ClientError as e:
        print(f'Error fetching public key from {node_url}: {e}')

# Fungsi untuk meminta digital signature
async def get_signature(session, node_url, transaction):
    try:
        async with session.post(f'{node_url}/request_signature', json={'transaction': transaction}) as response:
            return await response.json()
    except aiohttp.ClientError as e:
        print(f'Error getting signature from {node_url}: {e}')
        return {'status': 'error', 'message': str(e)}

# Fungsi untuk meminta secret share
async def get_share(session, node_url):
    try:
        async with session.post(f'{node_url}/request_share') as response:
            return await response.json()
    except aiohttp.ClientError as e:
        print(f'Error getting share from {node_url}: {e}')
        return {'status': 'error', 'message': str(e)}

# Route untuk mendistribusikan secret
@app.route('/distribute_shares', methods=['POST'])
def distribute_shares():
    secret = b"my_secret_key"
    shares = pyshamir.split(secret, 3, 2)

    async def distribute():
        async with aiohttp.ClientSession() as session:
            tasks = [initialize_node(session, node_addresses[f'node{i+1}'], base64.b64encode(shares[i]).decode()) for i in range(3)]
            responses = await asyncio.gather(*tasks)
            return jsonify({'status': 'Shares distributed', 'responses': responses})

    return asyncio.run(distribute())

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
        try:
            tasks = [get_signature(session, node_url, transaction_data) for node_url in node_addresses.values()]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            signatures = []
            for resp in responses:
                if isinstance(resp, Exception):
                    print(f"Exception from node: {resp}")
                elif 'signature' in resp:
                    signatures.append(resp['signature'])
                else:
                    print(f"Invalid response from node: {resp}")

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
                share_responses = await asyncio.gather(*share_tasks, return_exceptions=True)

                shares = []
                for resp in share_responses:
                    if isinstance(resp, Exception):
                        print(f"Exception from node: {resp}")
                    elif 'share' in resp:
                        shares.append(base64.b64decode(resp['share']))
                    else:
                        print(f"Invalid response from node: {resp}")

                try:
                    secret = pyshamir.combine(shares[:2])
                    print(f'Reconstructed secret: {secret}')
                    return jsonify({'status': 'Transaction approved', 'secret': secret.decode()})
                except Exception as e:
                    print(f'Failed to reconstruct secret: {e}')
                    return jsonify({'status': 'Transaction rejected', 'error': str(e)})
            else:
                return jsonify({'status': 'Transaction rejected', 'error': f'Insufficient valid signatures, total: {valid_signatures}'})
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            return jsonify({'status': 'Transaction rejected', 'error': 'Unexpected error'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
