from google import genai
from app.config import GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)


def main():

    text = """
    BIS Standard IS 14543:2024 specifies requirements
    for packaged drinking water other than packaged
    natural mineral water.
    """

    print("Generating embedding...")

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config={
            "output_dimensionality": 768
        }
    )

    embedding = response.embeddings[0].values

    print("Embedding generated successfully!")
    print("Vector dimensions:", len(embedding))
    print("First 10 values:")
    print(embedding[:10])


if __name__ == "__main__":
    main()