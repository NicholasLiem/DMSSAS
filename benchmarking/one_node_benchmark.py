import subprocess
import time
import requests
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from transaction import Transaction

# Define the URLs for the leader and nodes
leader_url = 'http://127.0.0.1:5000'
node_urls = {
    'node1': 'http://127.0.0.1:5001',
    'node2': 'http://127.0.0.1:5002',
    'node3': 'http://127.0.0.1:5003',
}

# Function to start a server
def start_server(command):
    return subprocess.Popen(command, shell=True)

# Start the leader and node servers
leader_process = start_server('python3 src/leader.py')
node_processes = [
    start_server(f'PORT=5001 NODE_ID=node1 python3 src/node.py'),
]

time.sleep(5)

def benchmark_init_and_distribute():
    start_time = time.time()
    response = requests.post(f'{leader_url}/distribute_shares')
    init_distribute_time = time.time() - start_time
    print(f'Initialization and Distribution Time: {init_distribute_time:.2f} seconds')
    print(response.json())

def benchmark_submit_transaction(transaction_data):
    start_time = time.time()
    response = requests.post(f'{leader_url}/submit_transaction', json=transaction_data)
    submit_transaction_time = time.time() - start_time
    print(f'Transaction Submission Time: {submit_transaction_time:.2f} seconds')
    print(response.json())

benchmark_init_and_distribute()

transaction = Transaction(sender='Alice', recipient='Bob', amount=100, timestamp='1234')
transaction_data = {
    "transaction": transaction.to_dict(False)
}
benchmark_submit_transaction(transaction_data)

# Cleanup: Terminate the server processes
leader_process.terminate()
for process in node_processes:
    process.terminate()
