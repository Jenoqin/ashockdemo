from quantlab.api.dependencies import _load_secret_file


def test_secret_loader_supports_bare_dotenv_and_json_without_mutating_files(tmp_path):
    bare = tmp_path / "bare.txt"
    bare.write_text("bare-token", encoding="utf-8")
    dotenv = tmp_path / "dotenv.txt"
    dotenv.write_text("# local secret\nexport TUSHARE_TOKEN='dotenv-token'\n", encoding="utf-8")
    json_file = tmp_path / "token.json"
    json_file.write_text('{"tushare_token":"json-token"}', encoding="utf-8")

    assert _load_secret_file(str(bare)) == "bare-token"
    assert _load_secret_file(str(dotenv)) == "dotenv-token"
    assert _load_secret_file(str(json_file)) == "json-token"


def test_secret_loader_rejects_unrecognized_multiline_content(tmp_path):
    secret = tmp_path / "invalid.txt"
    secret.write_text("username=user\npassword=hidden\n", encoding="utf-8")
    assert _load_secret_file(str(secret)) is None
