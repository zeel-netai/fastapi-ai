from langchain_google_genai import ChatGoogleGenerativeAI
from services.embedding import semantic_search


def ask_query(query: str) -> str:
    try:
        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.5,
        )

        response = model.invoke(query)

        print("response:", response)

        return response.content
    except Exception as e:
        return f"An error occurred: {str(e)}"


def ask_navigation_query(query: str, vectors, metadata):
    try:
        result = semantic_search(query, vectors, metadata, top_k=5)
        return result

    except Exception as e:
        print("Error in ask_navigation_query:", str(e))
        return f"An error occurred: {str(e)}"
