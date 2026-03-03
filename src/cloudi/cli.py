import argparse
import json
from .user_ops import create_student


def main():
    parser = argparse.ArgumentParser(prog="cloudi")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    print("CloudI CLI - User Management")

    s = sub.add_parser("create-student")
    s.add_argument("--email", required=True)
    s.add_argument("--first", required=True)
    s.add_argument("--last", required=True)
    s.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.cmd == "create-student":
        print(f"Creating student {args.email}...")
        result = create_student(
            email=args.email,
            firstname=args.first,
            lastname=args.last,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Created {result['username']} ({result['email']})")
            print(f"Account ID: {result['account_id']}")
            print(f"User ID:    {result['user_id']}")
