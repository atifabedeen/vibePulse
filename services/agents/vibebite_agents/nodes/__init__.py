"""LangGraph node implementations for the recommend_v1 graph.

Each node is an `async` coroutine taking the current `GraphState` and
returning a partial state update (the LangGraph idiom). The demo runner
in C2-C wires them into a graph.
"""
