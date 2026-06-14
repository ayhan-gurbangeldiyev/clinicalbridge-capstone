import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from schemas import RPMAlert
from orchestrator.orchestrator import ClinicalBridgeOrchestrator

load_dotenv()


def main():
    if len(sys.argv) < 3:
        print("Usage: python main.py --scenario <name> | --alert <json_file> [--version v1]")
        sys.exit(1)

    mode = sys.argv[1]
    target = sys.argv[2]

    if mode == "--scenario":
        alert_path = Path(f"data/scenarios/{target}/input_alert.json")
    elif mode == "--alert":
        alert_path = Path(target)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

    if not alert_path.exists():
        print(f"Alert file not found: {alert_path}")
        sys.exit(1)

    version = "v4"
    for i, arg in enumerate(sys.argv):
        if arg == "--version" and i + 1 < len(sys.argv):
            version = sys.argv[i + 1]

    scenario = target if mode == "--scenario" else None
    alert = RPMAlert(**json.loads(alert_path.read_text()))
    orchestrator = ClinicalBridgeOrchestrator(prompt_version=version)
    brief = asyncio.run(orchestrator.run(alert, scenario=scenario))
    print(json.dumps(brief.model_dump(), indent=2, default=str))

    from utils.tracing import flush_langfuse
    flush_langfuse()  # ensure the trace reaches LangFuse before exit


if __name__ == "__main__":
    main()
