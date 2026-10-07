import argparse

from .memories import (
    create_memory_bank,
    custom_add,
    list_memories,
    memory_fact,
    memory_resource_name,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage a Vertex AI Memory Bank")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a Memory Bank instance")
    create.add_argument("--display-name", default="travel-agent-memory")

    listing = sub.add_parser("list", help="List memories")
    listing.add_argument("--user-id", help="Filter by user. Omit to list every memory.")
    listing.add_argument("--app-name", default="travel_agent")

    add = sub.add_parser("add", help="Add a custom memory")
    add.add_argument("--fact", required=True, help="Memory text to store")
    add.add_argument("--user-id", required=True)
    add.add_argument("--app-name", default="travel_agent")

    args = parser.parse_args()

    if args.command == "create":
        name = create_memory_bank(args.display_name)
        engine_id = name.rstrip("/").split("/")[-1]
        print(name)
        print(f"Set AGENT_ENGINE_ID to: {engine_id}")
        return

    if args.command == "list":
        memories = list_memories(user_id=args.user_id, app_name=args.app_name)
        if not memories:
            print("No memories yet")
            return
        for index, item in enumerate(memories, start=1):
            print(f"{index}. {memory_fact(item)}")
            resource = memory_resource_name(item)
            if resource:
                print(f"   {resource}")
        return

    operation = custom_add(args.fact, user_id=args.user_id, app_name=args.app_name)
    print(memory_fact(operation))
    resource = memory_resource_name(operation)
    if resource:
        print(resource)


if __name__ == "__main__":
    main()
