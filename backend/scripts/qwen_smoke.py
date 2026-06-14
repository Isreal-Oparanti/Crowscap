from app.ai.qwen_client import QwenClient, QwenClientError


def main() -> None:
    client = QwenClient()
    try:
        response = client.chat_once(
            "Reply with one short sentence confirming Crowscap can reach Qwen Cloud."
        )
    except QwenClientError as exc:
        raise SystemExit(f"Qwen smoke test failed: {exc}") from exc

    print(response)


if __name__ == "__main__":
    main()

