from __future__ import annotations

from generator.cli.commands import COMMAND_HANDLERS
from generator.cli.parser import build_parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return COMMAND_HANDLERS[args.command](args)
