
from services.gemini_service import gemini_service

prompt = """
Explain the responsibilities of an external auditor
in three sentences.
"""

try:
    result = gemini_service.generate(prompt)

    print("\nSUCCESS!")
    print("Model used:", result["model"])
    print("\nResponse:")
    print(result["answer"])

except Exception as error:
    print("\nGEMINI ERROR:")
    print(error)
