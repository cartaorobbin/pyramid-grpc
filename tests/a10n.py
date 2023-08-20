from dataclasses import dataclass
import secrets
from pyramid.authorization import ACLHelper, Everyone, Authenticated
from pyramid_jwt import JWTAuthenticationPolicy



@dataclass
class Identity:
    sub: str
    source: str
    scope: list
    iat: int
    exp: int
    iss: str


class JWtAuthenticationHelper:
    def __init__(self, settings):
        self.jwt = JWTAuthenticationPolicy(
            private_key=settings["jwt.private_key"],
            public_key=settings["jwt.public_key"],
            auth_type="Bearer",
            default_claims=["scope", "sub", "uid", "source"],
            algorithm="RS256",
        )

    def get_claims(self, request):
        return self.jwt.get_claims(request)


class SecurityPolicy:
    def __init__(self, settings):
        self.helper = JWtAuthenticationHelper(settings)

    def identity(self, request):
        """Return app-specific user object."""
        if self.helper.get_claims(request):
            return Identity(**self.helper.get_claims(request))

    def authenticated_userid(self, request):
        """Return user id."""
        identity = self.identity(request=request)
        if identity is not None:
            return identity.sub

    def permits(self, request, context, permission):
        principals = [Everyone]
        identity = self.identity(request=request)
        if identity is not None:
            principals.append(Authenticated)
            principals.append("user:" + identity.sub)
            principals.append("source:" + identity.source)
            for scope in identity.scope:
                principals.append(scope)
        return ACLHelper().permits(context, principals, permission)
