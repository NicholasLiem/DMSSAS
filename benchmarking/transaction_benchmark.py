import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from transaction import Transaction

def benchmark_transaction_operations(num_iterations):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    transaction = Transaction(sender="Alice", recipient="Bob", amount=100, timestamp="2023-06-08T12:00:00Z")

    signing_times = []
    for _ in range(num_iterations):
        start_time = time.time()
        transaction.sign_transaction(private_key_pem)
        end_time = time.time()
        signing_times.append(end_time - start_time)

    verification_times = []
    for _ in range(num_iterations):
        start_time = time.time()
        result = transaction.verify_transaction(public_key_pem)
        end_time = time.time()
        verification_times.append(end_time - start_time)
        assert result, "Verification failed"

    avg_signing_time = sum(signing_times) / num_iterations
    avg_verification_time = sum(verification_times) / num_iterations

    print(f"Average signing time over {num_iterations} iterations: {avg_signing_time:.6f} seconds")
    print(f"Average verification time over {num_iterations} iterations: {avg_verification_time:.6f} seconds")

if __name__ == "__main__":
    benchmark_transaction_operations(100)
