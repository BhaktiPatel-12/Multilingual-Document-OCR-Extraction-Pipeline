import sys
from pathlib import Path

from structured_service import AstraStructuredService


def main():

    print()
    print("=" * 60)
    print("       ASTRA STRUCTURED OUTPUT ENGINE")
    print("=" * 60)

    # ============================================================
    # INPUT
    # ============================================================

    if len(sys.argv) < 2:

        print()
        print(
            "Usage:"
        )

        print(
            "python structured_runner.py "
            "path\\to\\results.json"
        )

        print()

        return

    input_path = Path(
        sys.argv[1]
    ).resolve()

    print()
    print(
        f"Input JSON:"
    )
    print(
        input_path
    )

    # ============================================================
    # SERVICE
    # ============================================================

    service = AstraStructuredService()

    # ============================================================
    # PROCESS
    # ============================================================

    try:

        result, output_path = (
            service.process_file(
                input_path
            )
        )

    except Exception as exc:

        print()
        print(
            "ERROR:"
        )

        print(
            str(exc)
        )

        raise

    # ============================================================
    # SUMMARY
    # ============================================================

    print()
    print("-" * 60)

    print(
        "DOCUMENT TYPE:"
    )

    print(
        result["document"]["type"]
    )

    print()

    print(
        "STRUCTURED FIELDS:"
    )

    for field_name, field in result[
        "fields"
    ].items():

        print(
            f"  {field_name}: "
            f"{field['value']}"
        )

    print()

    print(
        f"Tables detected: "
        f"{len(result['tables'])}"
    )

    print()

    print(
        "Output:"
    )

    print(
        output_path
    )

    print()
    print("=" * 60)
    print(
        "       STRUCTURING COMPLETE"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()