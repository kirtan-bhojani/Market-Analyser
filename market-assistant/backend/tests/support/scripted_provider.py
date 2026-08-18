"""A scripted LLMProvider for tests: replays canned per-round chunk lists."""

from __future__ import annotations


class ScriptedProvider:
    def __init__(self, rounds):
        self.rounds = rounds
        self.call_count = 0

    async def stream(self, messages, tools):
        idx = min(self.call_count, len(self.rounds) - 1)
        self.call_count += 1
        for chunk in self.rounds[idx]:
            yield chunk
