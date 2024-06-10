import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

class Transaction:
    def __init__(self, sender, recipient, amount, timestamp):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp
        self.signature = None
    
    def to_dict(self, include_signature=True):
        data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp,
        }
        if include_signature:
            data['signature'] = self.signature
        return data
    
    def to_json(self, include_signature=True):
        return json.dumps(self.to_dict(include_signature))
    
    def sign_transaction(self, private_key_pem):
        private_key = load_pem_private_key(private_key_pem, password=None)
        transaction_data = self.to_json(include_signature=False).encode()

        self.signature = base64.b64encode(
            private_key.sign(
                transaction_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        ).decode()

    def verify_transaction(self, public_key_pem):
        public_key = load_pem_public_key(public_key_pem)
        transaction_data = self.to_json(include_signature=False).encode()
        
        try:
            public_key.verify(
                base64.b64decode(self.signature.encode()),
                transaction_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Verification failed: {e}")
            return False
