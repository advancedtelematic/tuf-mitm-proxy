import json

from mitmproxy.http import HTTPFlow
from typing import Any, Dict, Optional

from .signature import Signatures
from .targets import Targets
from ..errors import UnknownRole
from ..utils import Encoded, Readable, canonical, contains


class Role(str):
    """A valid TUF metadata role."""
    VALID = ["root", "snapshot", "targets", "timestamp"]

    def __new__(cls, role: str) -> str:
        if role.lower() not in cls.VALID:
            raise UnknownRole(role)
        return role


class Metadata(object):
    """Parsed TUF metadata."""
    signatures: Signatures
    role: Role
    expires: str
    version: int
    targets: Optional[Targets] = None
    extra: Dict[str, Any]

    def __init__(self, meta: Dict[str, Any]) -> None:
        contains(meta, "signatures", "signed")
        self.signatures = Signatures.from_dicts(meta.pop("signatures"))

        signed = meta.pop("signed")
        contains(signed, "_type", "expires", "version")
        self.expires = signed.pop("expires")
        self.version = signed.pop("version")

        self.role = Role(signed.pop("_type"))
        if self.role.lower() == "targets":
            contains(signed, "targets")
            self.targets = Targets.from_dict(signed.pop("targets"))

        self.extra = signed

    @classmethod
    def from_flow(cls, flow: HTTPFlow) -> 'Metadata':
        """Convert the HTTPFlow into a new instance."""
        return cls.from_readable(flow.response.content)

    @classmethod
    def from_readable(cls, data: Readable) -> 'Metadata':
        """Parse the readable JSON data into a new instance."""
        return cls(json.loads(data))

    def to_json(self) -> str:
        """Return the TUF metadata object as JSON."""
        return str(canonical(self._encode()))

    def canonical_signed(self) -> str:
        """Return the TUF metadata signed section as JSON."""
        return str(canonical(self._encode_signed()))

    def _encode(self) -> Encoded:
        """Encode the signatures and the signed section.."""
        return {
            "signatures": self.signatures._encode(),
            "signed": self._encode_signed()
        }

    def _encode_signed(self) -> Encoded:
        """Encode the signed section."""
        out: Dict[str, Any] = {
            "_type": self.role,
            "expires": self.expires,
            "version": self.version,
        }
        if self.targets:
            out["targets"] = self.targets._encode()
        out.update(self.extra)
        return out
