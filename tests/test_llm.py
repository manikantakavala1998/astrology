from vedic_astro.rag.llm import chat

# Uses llama3.2 explicitly (already downloaded) rather than the module's
# qwen2.5:7b default, since these tests must run whatever chat model happens
# to be available locally - the wrapper function itself is model-agnostic.
_TEST_MODEL = "llama3.2"


def test_chat_returns_a_nonempty_response() -> None:
    answer = chat(
        system_prompt="You are a helpful assistant. Answer in one short sentence.",
        user_message="What is 2+2?",
        model=_TEST_MODEL,
    )
    assert len(answer.strip()) > 0


def test_chat_follows_system_prompt_instruction() -> None:
    answer = chat(
        system_prompt="Respond with exactly the single word: PONG",
        user_message="ping",
        model=_TEST_MODEL,
    )
    assert "pong" in answer.lower()


def test_chat_uses_provided_context_in_answer() -> None:
    answer = chat(
        system_prompt=(
            "Answer the user's question using ONLY the following fact: "
            "The current Vimshottari mahadasha is Saturn."
        ),
        user_message="What is the current mahadasha?",
        model=_TEST_MODEL,
    )
    assert "saturn" in answer.lower()
