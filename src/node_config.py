import rsa
import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

class NodeConfig:
    def __init__(self, node_id, endpoint_url, private_key=None, public_key=None, secret_share=None):
        self.node_id = node_id
        self.endpoint_url = endpoint_url
        self.private_key = private_key
        self.public_key = public_key
        self.secret_share = secret_share

    def generate_keys(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "endpoint_url": self.endpoint_url,
            "public_key": base64.b64encode(self.get_public_key_pem()).decode('utf-8'),
            "secret_share": self.secret_share
        }

    @staticmethod
    def from_dict(data):
        public_key = serialization.load_pem_public_key(base64.b64decode(data["public_key"]))
        return NodeConfig(
            node_id=data["node_id"],
            endpoint_url=data["endpoint_url"],
            private_key=None,
            public_key=public_key,
            secret_share=data["secret_share"]
        )
