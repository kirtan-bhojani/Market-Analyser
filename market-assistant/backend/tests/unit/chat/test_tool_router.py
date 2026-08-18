from app.chat.tools.router import TOOL_IMPLS, dispatch_tool_call
from app.schemas.chat import ToolCall


async def test_dispatch_calls_registered_tool(monkeypatch):
    async def fake_get_price(args, ctx):
        return {"symbol": args["symbol"], "price": 65000.0}

    monkeypatch.setitem(TOOL_IMPLS, "get_price", fake_get_price)

    call = ToolCall(name="get_price", arguments={"symbol": "BTC/USDT"})
    result = await dispatch_tool_call(call, ctx={})
    assert result.ok is True
    assert result.data["price"] == 65000.0


async def test_dispatch_unknown_tool_returns_safe_error_not_exception():
    call = ToolCall(name="does_not_exist", arguments={})
    result = await dispatch_tool_call(call, ctx={})
    assert result.ok is False
    assert "unknown tool" in result.error.lower()


async def test_dispatch_tool_exception_returns_safe_error(monkeypatch):
    async def broken(args, ctx):
        raise RuntimeError("boom")

    monkeypatch.setitem(TOOL_IMPLS, "get_price", broken)
    call = ToolCall(name="get_price", arguments={"symbol": "BTC/USDT"})
    result = await dispatch_tool_call(call, ctx={})
    assert result.ok is False
    assert "boom" not in result.error
    assert "temporarily unavailable" in result.error.lower()
