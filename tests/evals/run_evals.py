"""Run the RAG evaluation harness."""

from tests.evals import isolation


def main() -> None:
    """Guard the environment, then run the evaluation."""
    isolation.guard()
    print("bound to:", isolation.database.DATABASE_URL)


if __name__ == "__main__":
    main()
