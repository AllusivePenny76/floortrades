from .. import config
from .kadoa import KadoaProvider

_PROVIDERS = {
    "kadoa": KadoaProvider,
}


def get_provider():
    cls = _PROVIDERS.get(config.PROVIDER)
    if cls is None:
        raise ValueError(
            f"Unknown provider '{config.PROVIDER}'. "
            f"Available: {', '.join(_PROVIDERS)}"
        )
    return cls()
