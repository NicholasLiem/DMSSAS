import subprocess
import time
import requests
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from transaction import Transaction

leader_url = 'http://127.0.0.1:5000'
node_urls = {
    'node1': 'http://127.0.0.1:5001',
    'node2': 'http://127.0.0.1:5002',
    'node3': 'http://127.0.0.1:5003',
}

def start_server(command):
    return subprocess.Popen(command, shell=True)

leader_process = start_server('python3 src/leader.py')
node_processes = [
    start_server(f'PORT=5001 NODE_ID=node1 python3 src/node.py'),
    start_server(f'PORT=5002 NODE_ID=node2 python3 src/node.py'),
    start_server(f'PORT=5003 NODE_ID=node3 python3 src/node.py')
]

time.sleep(5)

# Step 1: Initialize nodes
start_time = time.time()
response = requests.post(f'{leader_url}/initialize_nodes')
init_nodes_time = time.time() - start_time
print(f'Node Initialization Time: {init_nodes_time:.2f} seconds')
print(response.json())

# Step 2: Distribute shares
start_time = time.time()
response = requests.post(f'{leader_url}/distribute_shares')
distribute_shares_time = time.time() - start_time
print(f'Shares Distribution Time: {distribute_shares_time:.2f} seconds')
print(response.json())

# Step 3: Submit transaction
transaction = Transaction(sender='Alice', recipient='Bob', amount=100, timestamp='1234')
transaction_data = {
    "transaction": transaction.to_dict(False)
}

start_time = time.time()
response = requests.post(f'{leader_url}/submit_transaction', json=transaction_data)
submit_transaction_time = time.time() - start_time
print(f'Transaction Submission Time: {submit_transaction_time:.2f} seconds')
print(response.json())

# Terminate the processes
leader_process.terminate()
for process in node_processes:
    process.terminate()
