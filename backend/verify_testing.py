from app.hybrid_retrieval import HybridRetriever
import inspect

print("TEST SEARCH:", hasattr(HybridRetriever, "test_search"))

source = inspect.getsource(HybridRetriever.search)

print(
    "TESTING BRANCH:",
    "elif intent == " + chr(34) + "testing" + chr(34) + ":" in source
)