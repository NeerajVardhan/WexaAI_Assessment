from app.core.security import create_access_token, decode_token, hash_secret


def test_access_token_round_trip() -> None:
    token = create_access_token("user-1", "org-1", "owner")

    payload = decode_token(token)

    assert payload["sub"] == "user-1"
    assert payload["org"] == "org-1"
    assert payload["role"] == "owner"


def test_secret_hash_is_stable_and_not_plaintext() -> None:
    raw = "wx_live_secret"

    assert hash_secret(raw) == hash_secret(raw)
    assert hash_secret(raw) != raw

