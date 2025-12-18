from langchain_google_genai import ChatGoogleGenerativeAI


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
