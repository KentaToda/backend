import os
from langchain_google_vertexai import ChatVertexAI

def test_vertex():
    print("Testing Vertex AI Connection...")
    
    # 環境変数からプロジェクトIDを取得 (必要であれば)
    # project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    try:
        # モデルの初期化
        # 環境変数 GOOGLE_APPLICATION_CREDENTIALS が設定されていることを前提とします
        llm = ChatVertexAI(model="gemini-1.5-flash")
        
        # テストプロンプトの送信
        response = llm.invoke("Hello, Vertex AI!")
        
        print("\n--- Response from Vertex AI ---")
        print(response.content)
        print("-------------------------------\n")
        print("Success! Connection established.")
        
    except Exception as e:
        print("\n!!! Connection Failed !!!")
        print(e)

if __name__ == "__main__":
    test_vertex()
