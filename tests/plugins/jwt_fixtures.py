import pytest
from jose import jwk, constants
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import json
from datetime import datetime, timedelta


@pytest.fixture(scope="session")
def private_key():
    return rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )


@pytest.fixture(scope="session")
def public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


@pytest.fixture(scope="session")
def public_jwks(public_key):
    return json.dumps(jwk.RSAKey(algorithm=constants.Algorithms.RS256, key=public_key.decode('utf-8')).to_dict())


@pytest.fixture
def generate_jwt(private_key, public_key):
    def _generate_jwt(payload, headers=None, algorithm="RS256"):
        payload.setdefault('sub', '1')
        payload.setdefault('source', '1')
        payload.setdefault('iat', '1')
        payload.setdefault('iss', '1')

        payload.setdefault('exp', datetime.utcnow() + timedelta(days=1)).utctimetuple()

        return jwt.encode(
            payload, algorithm=algorithm, key=private_key, headers=headers
        )

    return _generate_jwt


@pytest.fixture()
def auth_token(generate_jwt):

    def _auth_token(payload, headers=None, algorithm="RS256"):

        return "Bearer {}".format(generate_jwt(payload=payload, headers=headers, algorithm=algorithm))
    return _auth_token
